#!/usr/bin/env python3
"""playbook-forge : outil en ligne de commande (bibliothèque standard uniquement)."""
import argparse
import difflib
import json
import os
import re
import shutil
import sys
import tempfile
import webbrowser
import zipfile
from collections import Counter
from datetime import date
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "skills" / "playbook" / "assets"
PORTABLE = {"name", "description", "metadata", "license", "compatibility", "allowed-tools"}
SECTIONS = [
    ("Objectif", "Purpose"), ("Quand l'utiliser", "When to use this"), ("Entrées", "Inputs"),
    ("Étapes", "Steps"), ("Décisions", "Decisions"), ("Boîte à outils", "Toolbox"),
    ("Définition de terminé", "Definition of done"), ("Cas particuliers", "Edge cases"),
    ("Après chaque exécution", "After each run"),
]
DATE = r"\d{4}-\d{2}-\d{2}"
IDX = re.compile(rf"- (.+?) \| (.*) \| ({DATE})$")
NOTE = re.compile(rf"- ({DATE}) \| (instructions|outils|checks) \| (.+) \| (.+)$")
SECRET = re.compile(
    r"sk-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{8,}|PRIVATE KEY|(?i:password\s*=|api_key\s*=)")
SUBJECTIVE = re.compile(r"(?i)\b(clairs?|claires?|professionnel(?:le)?s?|qualité|soigné(?:e)?s?)\b")


class Usage(Exception):
    """Erreur d'usage, code retour 2."""


class Fail(Exception):
    """Échec métier, code retour 1."""


# ---------- utilitaires ----------

def today():
    return date.today().isoformat()


def days_since(s):
    try:
        return (date.today() - date.fromisoformat(s)).days
    except (ValueError, TypeError):
        return None


def config_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def project_root():
    p = Path.cwd().resolve()
    return next((d for d in [p, *p.parents] if (d / ".git").exists()), p)


def read(p):
    return Path(p).read_text(encoding="utf-8", errors="replace")  # l'encodage de SKILL.md est vérifié par enc_ok


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def clean(s):
    return re.sub(r"\s+", " ", s.replace("|", "/")).strip()


def valid_name(n):
    return bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", n)) and len(n) <= 64 and n != "synced"


def cfg_file():
    return config_dir() / "playbook-forge" / "config.json"


def enc_ok(p):
    try:
        Path(p).read_bytes().decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def cited(name, text):
    return re.search(rf"(?<![\w.-]){re.escape(name)}(?![\w-])", text) is not None


def load_cfg(strict=False):
    p = cfg_file()
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        if strict:
            raise Fail(f"config illisible, non modifiée : {p} ({e})")
        return {}


def roots():
    r = [("perso", config_dir() / "skills"), ("projet", project_root() / ".claude" / "skills")]
    return r + [("extra", Path(x)) for x in load_cfg().get("extra_roots", [])]


def unq(v):
    v = v.strip()
    return v[1:-1] if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'" else v


def parse_fm(text):
    """Frontmatter minimal : clés de premier niveau et un niveau d'imbrication."""
    lines = [l.rstrip() for l in text.split("\n")]
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return None, text
    end = lines.index("---", 1)
    fm, key = {}, None
    for l in lines[1:end]:
        m = re.match(r"([\w-]+):\s*(.*)$", l)
        if m and not l[0].isspace():
            key = m[1]
            fm[key] = "" if m[2] in (">", "|", ">-", "|-") else unq(m[2])
        elif key and l.strip():
            mm = re.match(r"\s+([\w-]+):\s*(.*)$", l)
            cur = fm[key]
            if mm and (cur == "" or isinstance(cur, dict)):
                fm[key] = {**(cur or {}), mm[1]: unq(mm[2])}
            elif isinstance(cur, str):
                fm[key] = (cur + " " + l.strip()).strip()
    return fm, "\n".join(lines[end + 1:])


def norm(s):
    return s.replace("’", "'").strip().lower()


def get_sections(body):
    secs, cur = {}, None
    for l in body.split("\n"):
        m = re.match(r"##\s+(.*?)\s*$", l)
        if m and not l.startswith("###"):
            cur = norm(m[1])
            secs[cur] = []
        elif cur is not None:
            secs[cur].append(l)
    return secs


def sec(secs, i):
    fr, en = (norm(x) for x in SECTIONS[i])
    return secs.get(fr) if fr in secs else secs.get(en)


def read_rows(p, rx):
    """Lignes `- ...` d'un fichier : (conformes, mal formées)."""
    good, bad = [], []
    if Path(p).is_file():
        for l in read(p).split("\n"):
            if l.startswith("- "):
                m = rx.match(l)
                (good.append(m.groups()) if m else bad.append(l))
    return good, bad


def read_runs(pb):
    good, bad = [], []
    p = pb / "runs.jsonl"
    if p.is_file():
        for n, l in enumerate(read(p).split("\n"), 1):
            if not l.strip():
                continue
            try:
                r = json.loads(l)
                ok = (isinstance(r, dict) and r.get("type") in ("run", "test", "audit")
                      and re.fullmatch(DATE, str(r.get("date"))) and isinstance(r.get("failed_checks"), list)
                      and all(isinstance(r.get(k), int) for k in ("passed", "failed", "unverified")))
            except ValueError:
                ok = False
            (good.append(r) if ok else bad.append(n))
    return good, bad


def list_files(pb):
    d = pb / "files"
    return sorted(f.relative_to(d).as_posix() for f in d.rglob("*")
                  if f.is_file() and f.name != "INDEX.md") if d.is_dir() else []


def near_dups(files):
    stems = [(f, Path(f).stem) for f in files]
    return [(a, b) for (a, sa), (b, sb) in combinations(stems, 2)
            if difflib.SequenceMatcher(None, sa, sb).ratio() >= 0.8]


def safe_fm(sk):
    try:
        return parse_fm(read(sk))[0]
    except (OSError, UnicodeDecodeError):
        return None


def discover():
    out, seen = [], set()
    for scope, root in roots():
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            fm = safe_fm(d / "SKILL.md") if (d / "SKILL.md").is_file() else None
            if fm and isinstance(fm.get("metadata"), dict) and "playbook-forge" in fm["metadata"] \
                    and d.resolve() not in seen:
                seen.add(d.resolve())
                out.append((scope, d))
    return out


def resolve_pb(arg):
    p = Path(arg)
    if (p / "SKILL.md").is_file():
        return p.resolve()
    if valid_name(arg):
        for _, r in roots():
            if (r / arg / "SKILL.md").is_file():
                return (r / arg).resolve()
    raise Usage(f"playbook introuvable : {arg}")


def last_activity(pb):
    runs, _ = read_runs(pb)
    notes, _ = read_rows(pb / "notes.md", NOTE)
    fm = safe_fm(pb / "SKILL.md") or {}
    created = fm.get("metadata", {}).get("created", "") if isinstance(fm.get("metadata"), dict) else ""
    return max([r["date"] for r in runs] + [n[0] for n in notes] + [created])


# ---------- validate ----------

def validate_pb(pb):
    pb, R = Path(pb), []

    def add(ok, rule, msg, bad="FAIL"):
        R.append(("PASS" if ok else bad, rule, msg))

    sk = pb / "SKILL.md"
    if not sk.is_file():
        return [("FAIL", "skill", "SKILL.md introuvable")]
    if not enc_ok(sk):
        return [("FAIL", "encodage", "SKILL.md n'est pas en UTF-8")]
    text = read(sk)
    fm, body = parse_fm(text)
    add(fm is not None, "frontmatter", "frontmatter en ligne 1" if fm is not None else "frontmatter absent ou non fermé")
    fm = fm or {}
    extra = sorted(set(fm) - PORTABLE)
    add(not extra, "cles", "clés portables uniquement" if not extra else "clés non portables : " + ", ".join(extra))
    name = fm.get("name")
    add(isinstance(name, str) and name == pb.name and valid_name(name), "nom",
        "name égal au dossier, kebab-case" if name == pb.name and valid_name(str(name))
        else f"name invalide ou différent du dossier ({name!r} / {pb.name})")
    d = fm.get("description")
    add(isinstance(d, str) and 0 < len(d.strip()) <= 1024, "description", "description non vide, 1024 caractères max")
    meta = fm.get("metadata")
    add(isinstance(meta, dict) and "playbook-forge" in meta, "metadata", "metadata.playbook-forge présent", "WARN")

    secs = get_sections(body)
    missing = [SECTIONS[i][0] for i in range(9) if sec(secs, i) is None]
    add(not missing, "sections", "9 sections présentes" if not missing else "sections manquantes : " + ", ".join(missing))
    steps = [l for l in sec(secs, 3) or [] if re.match(r"\s*\d+[.)]\s+\S", l)]
    add(steps, "etapes", f"{len(steps)} étape(s) numérotée(s)")
    dec = [l for l in sec(secs, 4) or [] if re.search(r"(?i)\b(si|if)\b.+\b(alors|then)\b", l)]
    add(dec, "decisions", f"{len(dec)} règle(s) de décision")
    dod = sec(secs, 6) or []
    checks = [l for l in dod if re.match(r"\s*- \[[ xX]\]", l)]
    full = [l for l in checks if "Preuve" in l and "Échec si" in l]
    pending = not checks and "à compléter" in " ".join(dod).lower()
    add(5 <= len(full) <= 10, "checks", f"{len(full)} check(s) complets (5 à 10 attendus)", "WARN" if pending else "FAIL")
    add(len(full) == len(checks), "checks-format", f"{len(checks) - len(full)} check(s) sans Preuve ou Échec si", "WARN")
    subj = sorted({m[1].lower() for l in checks for m in [SUBJECTIVE.search(l)] if m})
    add(not subj, "subjectif", "aucun mot subjectif dans les checks" if not subj
        else "mots subjectifs sans critère mesurable : " + ", ".join(subj), "WARN")

    files = list_files(pb)
    rows, badidx = read_rows(pb / "files" / "INDEX.md", IDX)
    idx = {r[0] for r in rows}
    unidx = [f for f in files if f not in idx]
    ghost = [n for n in idx if n not in files]
    uncited = [f for f in files if not cited(f, text)]
    dated = [f for f in files if re.search(rf"{DATE}|\d{{8}}|(?<![a-z0-9])v\d+(?![a-z])", f.lower())]
    add(not unidx, "index", "tous les fichiers sont dans INDEX.md" if not unidx else "non indexés : " + ", ".join(unidx))
    add(not ghost, "index-fichiers", "toutes les lignes d'INDEX.md ont un fichier" if not ghost
        else "indexés mais absents de files/ : " + ", ".join(ghost))
    add(not badidx, "index-format", "INDEX.md bien formé" if not badidx else f"{len(badidx)} ligne(s) d'INDEX.md mal formée(s)", "WARN")
    add(not uncited, "cites", "tous les fichiers sont cités dans SKILL.md" if not uncited
        else "non cités dans SKILL.md : " + ", ".join(uncited), "WARN")
    add(not dated, "noms", "aucune date ni version dans les noms" if not dated
        else "date ou version dans le nom : " + ", ".join(dated))
    dups = near_dups(files)
    add(not dups, "doublons", "aucun nom trop proche" if not dups
        else "noms trop proches : " + ", ".join(f"{a}/{b}" for a, b in dups), "WARN")

    if (pb / "notes.md").is_file():
        _, badn = read_rows(pb / "notes.md", NOTE)
        add(not badn, "notes", "notes.md bien formé" if not badn else f"{len(badn)} ligne(s) de notes.md mal formée(s)")
    else:
        add(False, "notes", "notes.md absent", "WARN")
    if (pb / "runs.jsonl").is_file():
        _, badr = read_runs(pb)
        add(not badr, "runs", "runs.jsonl bien formé" if not badr else "runs.jsonl lignes invalides : " + ", ".join(map(str, badr)))
    else:
        add(False, "runs", "runs.jsonl absent", "WARN")

    leaks = []
    for f in sorted(pb.rglob("*")):
        if f.is_file():
            try:
                if SECRET.search(read(f)):
                    leaks.append(f.relative_to(pb).as_posix())
            except (OSError, UnicodeDecodeError):
                pass
    add(not leaks, "secrets", "aucun secret détecté" if not leaks else "secret possible dans : " + ", ".join(leaks))
    return R


# ---------- audit ----------

def audit_pb(pb):
    pb, F = Path(pb), []
    if not enc_ok(pb / "SKILL.md"):
        return [{"kind": "encodage", "msg": "SKILL.md n'est pas en UTF-8"}]
    text = read(pb / "SKILL.md")
    files = list_files(pb)
    F += [("non_cite", f"fichier non cité dans SKILL.md : {f}") for f in files if not cited(f, text)]
    F += [("doublon", f"doublon probable : {a} / {b}") for a, b in near_dups(files)]

    notes, _ = read_rows(pb / "notes.md", NOTE)
    step = lambda n: set(re.findall(r"(?i)(?:étape|step)\s*(\d+)", n[2] + " " + n[3]))
    seen = set()
    for j, nj in enumerate(notes):
        for i in range(j):
            ni = notes[i]
            sim = ni[1] == nj[1] and difflib.SequenceMatcher(None, ni[2].lower(), nj[2].lower()).ratio() >= 0.6
            if (sim or step(ni) & step(nj)) and i not in seen:
                seen.add(i)
                F.append(("erreur_repetee", f"erreur répétée ({ni[1]}) : {ni[2]} ; candidat script ou outil dédié"))
                break

    runs, _ = read_runs(pb)
    fm = safe_fm(pb / "SKILL.md") or {}
    created = fm.get("metadata", {}).get("created", "") if isinstance(fm.get("metadata"), dict) else ""
    last = max([r["date"] for r in runs if r["type"] == "audit"] + ([created] if created else []), default=None)
    age = days_since(last)
    if age is not None and age > 30:
        F.append(("audit_du", f"audit dû : dernier repère {last} ({age} jours)"))

    cnt = Counter(c for r in [r for r in runs if r["type"] != "audit"][-5:] for c in set(r["failed_checks"]))
    F += [("check_echoue", f"check en échec dans {n} des 5 derniers runs : {c}") for c, n in cnt.items() if n >= 2]
    return [{"kind": k, "msg": m} for k, m in F]


# ---------- dashboard ----------

def layers(pb, text, rows, files):
    _, body = parse_fm(text)
    secs = get_sections(body)
    steps = [l for l in sec(secs, 3) or [] if re.match(r"\s*\d+[.)]\s+\S", l)]
    dec = [l for l in sec(secs, 4) or [] if re.search(r"(?i)\b(si|if)\b.+\b(alors|then)\b", l)]
    parts = [all(sec(secs, i) is not None for i in range(9)), len(steps) >= 3, bool(dec)]
    full = [l for l in sec(secs, 6) or [] if re.match(r"\s*- \[[ xX]\]", l) and "Preuve" in l and "Échec si" in l]
    idx = {r[0] for r in rows}
    tools = bool(files) and idx == set(files)
    lvl = lambda done, some: "fait" if done else ("partiel" if some else "à faire")
    return {"Étapes": lvl(all(parts), any(parts)),
            "Outils": lvl(tools, bool(files) or bool(idx)),
            "Checks": lvl(5 <= len(full) <= 10, bool(full))}


def collect(pairs):
    out = []
    for scope, pb in pairs:
        pb = Path(pb)
        runs, _ = read_runs(pb)
        rows, _ = read_rows(pb / "files" / "INDEX.md", IDX)
        notes, _ = read_rows(pb / "notes.md", NOTE)
        ex = [r for r in runs if r["type"] != "audit"]
        spark = [round(r["passed"] / (r["passed"] + r["failed"]), 2) for r in ex[-10:] if r["passed"] + r["failed"]]
        alerts = ["validate : " + m for lv, _, m in validate_pb(pb) if lv == "FAIL"]
        alerts += [f["msg"] for f in audit_pb(pb)]
        fails = Counter(c for r in ex for c in r["failed_checks"])
        out.append({
            "name": pb.name, "scope": scope, "path": str(pb),
            "layers": layers(pb, read(pb / "SKILL.md"), rows, list_files(pb)),
            "last_run": max((r["date"] for r in ex), default=""), "spark": spark,
            "notes_count": len(notes), "alerts": alerts,
            "index": [list(r) for r in rows],
            "notes": [dict(zip(("date", "layer", "error", "fix"), n)) for n in notes[:5]],
            "top_failing": fails.most_common(5), "runs": ex,
        })
    return out


def build_data(pairs):
    pbs = collect(pairs)
    recent = [r for p in pbs for r in p["runs"] if (d := days_since(r["date"])) is not None and d <= 30]
    passed, failed = sum(r["passed"] for r in recent), sum(r["failed"] for r in recent)
    for p in pbs:
        del p["runs"]
    return {"generated": today(), "playbooks": pbs, "stats": {
        "playbooks": len(pbs), "runs30": len(recent),
        "rate": round(100 * passed / (passed + failed)) if passed + failed else None,
        "alerts": sum(len(p["alerts"]) for p in pbs)}}


def render(data):
    js = json.dumps(data, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return HTML.replace("__DATA__", js)


def summary(data):
    s = data["stats"]
    rate = "n/a" if s["rate"] is None else f"{s['rate']} %"
    L = [f"{s['playbooks']} playbook(s), {s['runs30']} run(s) sur 30 jours, checks réussis : {rate}, {s['alerts']} alerte(s)"]
    for p in data["playbooks"]:
        ly = " ".join(f"{k}={v}" for k, v in p["layers"].items())
        L.append(f"- {p['name']} ({p['scope']}) | {ly} | alertes : {len(p['alerts'])}")
    return "\n".join(L)


HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard playbook-forge</title>
<style>
:root{--bg:#f6f7f9;--fg:#1d2330;--card:#fff;--mut:#667085;--bd:#d9dde5;--ok:#1a7f4b;--mid:#b26a00;--ko:#c0392b;--acc:#2f5fd0}
@media (prefers-color-scheme:dark){:root{--bg:#12151c;--fg:#e6e9f0;--card:#1b202b;--mut:#9aa3b5;--bd:#2c3342;--ok:#4cc38a;--mid:#e0a040;--ko:#ef6f60;--acc:#7ea2ff}}
*{box-sizing:border-box}
body{margin:0;padding:1rem;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
h1{font-size:1.4rem;margin:.2rem 0 1rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.7rem;margin-bottom:1rem}
.stat{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.7rem}
.stat b{display:block;font-size:1.6rem}
.stat span,.muted{color:var(--mut);font-size:.85rem}
.bar{display:flex;flex-wrap:wrap;gap:.7rem;align-items:center;margin-bottom:1rem}
input[type=search]{flex:1;min-width:200px;padding:.5rem .7rem;border:1px solid var(--bd);border-radius:8px;background:var(--card);color:var(--fg);font:inherit}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:.9rem;align-items:start}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:.9rem;cursor:pointer}
.card.warn{border-left:4px solid var(--ko)}
.card:focus-visible{outline:2px solid var(--acc)}
.card h2{font-size:1.1rem;margin:0 0 .4rem;display:flex;justify-content:space-between;gap:.5rem}
.badge{font-size:.75rem;border:1px solid var(--bd);border-radius:99px;padding:0 .5rem;color:var(--mut);align-self:center}
.layers{display:flex;flex-wrap:wrap;gap:.4rem;margin:.4rem 0}
.l{font-size:.8rem;border-radius:6px;padding:.1rem .45rem;border:1px solid currentColor}
.l-fait{color:var(--ok)}.l-partiel{color:var(--mid)}.l-à{color:var(--ko)}
svg{width:100%;height:36px;display:block;margin:.4rem 0}
polyline{fill:none;stroke:var(--acc);stroke-width:2;vector-effect:non-scaling-stroke}
ul{margin:.3rem 0;padding-left:1.1rem}
.al{color:var(--ko)}
.detail{margin-top:.7rem;border-top:1px solid var(--bd);padding-top:.7rem;cursor:auto}
.detail h3{font-size:.95rem;margin:.6rem 0 .2rem}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{text-align:left;padding:.25rem .3rem;border-bottom:1px solid var(--bd);word-break:break-word}
footer{margin-top:1.5rem}
</style>
</head>
<body>
<h1>Dashboard des playbooks</h1>
<section class="stats" id="stats"></section>
<div class="bar">
<input type="search" id="q" placeholder="Rechercher un playbook" aria-label="Rechercher un playbook">
<label><input type="checkbox" id="onlyAl"> Avec alertes</label>
</div>
<main class="grid" id="grid"></main>
<footer class="muted" id="foot"></footer>
<script type="application/json" id="data">__DATA__</script>
<script>
(function(){
var D=JSON.parse(document.getElementById('data').textContent);
var NS='http://www.w3.org/2000/svg';
function h(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
function spark(v){
 if(!v.length)return h('div','muted','Aucun run enregistré');
 if(v.length<2)v=[v[0],v[0]];
 var s=document.createElementNS(NS,'svg'),p=document.createElementNS(NS,'polyline');
 s.setAttribute('viewBox','0 0 100 24');s.setAttribute('preserveAspectRatio','none');
 s.setAttribute('role','img');s.setAttribute('aria-label','Taux de réussite sur les derniers runs');
 p.setAttribute('points',v.map(function(r,i){return (i*100/(v.length-1))+','+(22-r*20)}).join(' '));
 s.appendChild(p);return s}
function list(items,empty){
 if(!items.length)return h('div','muted',empty);
 var u=h('ul');items.forEach(function(t){u.appendChild(h('li',null,t))});return u}
function detail(p){
 var d=h('div','detail');d.hidden=true;
 d.appendChild(h('h3',null,'Fichiers (INDEX.md)'));
 if(p.index.length){var t=h('table'),r=h('tr');['Fichier','Usage','Date'].forEach(function(x){r.appendChild(h('th',null,x))});t.appendChild(r);
  p.index.forEach(function(row){var tr=h('tr');row.forEach(function(x){tr.appendChild(h('td',null,x))});t.appendChild(tr)});d.appendChild(t)}
 else d.appendChild(h('div','muted','Aucun fichier indexé'));
 d.appendChild(h('h3',null,'5 dernières corrections'));
 d.appendChild(list(p.notes.map(function(n){return n.date+' | '+n.layer+' | '+n.error+' -> '+n.fix}),'Aucune correction'));
 d.appendChild(h('h3',null,'Checks les plus en échec'));
 d.appendChild(list(p.top_failing.map(function(c){return c[0]+' ('+c[1]+' fois)'}),'Aucun check en échec'));
 d.appendChild(h('div','muted',p.path));
 return d}
function card(p){
 var c=h('div','card'+(p.alerts.length?' warn':''));
 c.tabIndex=0;c.setAttribute('role','button');c.setAttribute('aria-expanded','false');
 var t=h('h2',null,p.name);t.appendChild(h('span','badge',p.scope));c.appendChild(t);
 var ly=h('div','layers');
 Object.keys(p.layers).forEach(function(k){var v=p.layers[k];ly.appendChild(h('span','l l-'+v.split(' ')[0],k+' : '+v))});
 c.appendChild(ly);
 c.appendChild(h('div','muted','Dernier run : '+(p.last_run||'aucun')+' | Corrections : '+p.notes_count));
 c.appendChild(spark(p.spark));
 var a=list(p.alerts,'Aucune alerte');if(p.alerts.length)a.className='al';c.appendChild(a);
 var d=detail(p);c.appendChild(d);
 function tog(e){if(e.target.closest&&e.target.closest('.detail'))return;d.hidden=!d.hidden;c.setAttribute('aria-expanded',String(!d.hidden))}
 c.addEventListener('click',tog);
 c.addEventListener('keydown',function(e){if(e.target===c&&(e.key==='Enter'||e.key===' ')){e.preventDefault();tog(e)}});
 return c}
function stats(){
 var s=D.stats,el=document.getElementById('stats');
 [['Playbooks',s.playbooks],['Runs sur 30 jours',s.runs30],['Checks réussis',s.rate===null?'n/a':s.rate+' %'],['Alertes',s.alerts]].forEach(function(x){
  var b=h('div','stat');b.appendChild(h('b',null,String(x[1])));b.appendChild(h('span',null,x[0]));el.appendChild(b)})}
function render(){
 var q=document.getElementById('q').value.toLowerCase(),only=document.getElementById('onlyAl').checked,g=document.getElementById('grid');
 g.textContent='';
 var n=0;
 D.playbooks.forEach(function(p){
  if(only&&!p.alerts.length)return;
  if(q&&(p.name+' '+p.scope).toLowerCase().indexOf(q)<0)return;
  g.appendChild(card(p));n++});
 if(!n)g.appendChild(h('div','muted','Aucun playbook ne correspond.'))}
stats();render();
document.getElementById('q').addEventListener('input',render);
document.getElementById('onlyAl').addEventListener('change',render);
document.getElementById('foot').textContent='Généré le '+D.generated+' par playbook-forge';
})();
</script>
</body>
</html>
"""


# ---------- commandes ----------

def add_index(pb, file, purpose, d):
    p = pb / "files" / "INDEX.md"
    p.parent.mkdir(exist_ok=True)
    line = f"- {clean(file)} | {clean(purpose)} | {d}"
    lines = read(p).split("\n") if p.is_file() else ["# Index des fichiers", ""]
    lines = [l for l in lines if not l.startswith(f"- {clean(file)} | ")]
    while lines and lines[-1] == "":
        lines.pop()
    write(p, "\n".join(lines + [line]) + "\n")


def add_note(pb, layer, error, fix, d):
    p = pb / "notes.md"
    lines = read(p).split("\n") if p.is_file() else ["# Notes de corrections", ""]
    at = next((i for i, l in enumerate(lines) if l.startswith("- ")), None)
    if at is None:
        while lines and lines[-1] == "":
            lines.pop()
        at = len(lines)
    lines.insert(at, f"- {d} | {layer} | {clean(error)} | {clean(fix)}")
    write(p, "\n".join(lines).rstrip("\n") + "\n")


def add_run(pb, run):
    p = pb / "runs.jsonl"
    old = read(p) if p.is_file() else ""
    write(p, old + ("" if not old or old.endswith("\n") else "\n") + json.dumps(run, ensure_ascii=False) + "\n")


def export_zip(pb, out):
    fm = safe_fm(pb / "SKILL.md")
    if fm is None:
        raise Fail("frontmatter absent")
    extra = sorted(set(fm) - PORTABLE)
    if extra:
        raise Fail("clés non portables : " + ", ".join(extra))
    out = Path(out).resolve()
    if out == pb or pb in out.parents:
        raise Fail(f"--out dans le dossier du playbook : {out}")
    out.mkdir(parents=True, exist_ok=True)
    z = out / f"{pb.name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(pb.rglob("*")):
            rel = f.relative_to(pb).as_posix()
            if f.is_file() and rel != "runs.jsonl" and f.suffix != ".zip" and "__pycache__" not in f.parts:
                zf.write(f, f"{pb.name}/{rel}")
    return z


def cmd_doctor(a):
    ok = sys.version_info >= (3, 9)
    print(f"{'PASS' if ok else 'FAIL'} Python {sys.version.split()[0]} (3.9+ requis)")
    print(f"Config : {cfg_file()}")
    for scope, r in roots():
        t = r
        while not t.exists() and t != t.parent:
            t = t.parent
        print(f"{scope} : {r} | {'existe' if r.is_dir() else 'absent'} | écriture {'oui' if os.access(t, os.W_OK) else 'non'}")
    return 0 if ok else 1


def cmd_list(a):
    rows = [{"name": pb.name, "scope": s, "path": str(pb), "last_activity": last_activity(pb)} for s, pb in discover()]
    rows.sort(key=lambda r: r["last_activity"], reverse=True)
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif not rows:
        print("Aucun playbook trouvé.")
    for r in ([] if a.json else rows):
        print(f"{r['name']} | {r['scope']} | {r['last_activity'] or 'jamais'} | {r['path']}")
    return 0


def cmd_scaffold(a):
    if not valid_name(a.nom):
        raise Usage(f"nom invalide (kebab-case, 64 max, pas 'synced') : {a.nom}")
    root = Path(a.root) if a.root else (config_dir() / "skills" if a.scope == "perso" else project_root() / ".claude" / "skills")
    dest = root / a.nom
    if dest.exists():
        raise Fail(f"existe déjà : {dest}")
    tpl = {n: ASSETS / n for n in ("SKILL.template.md", "INDEX.template.md", "notes.template.md")}
    if not all(p.is_file() for p in tpl.values()):
        raise Usage(f"templates introuvables dans {ASSETS}")
    new_root = not root.exists()
    sub = lambda s: s.replace("[nom]", a.nom).replace("[AAAA-MM-JJ]", today())
    (dest / "files").mkdir(parents=True)
    (dest / "examples").mkdir()
    write(dest / "SKILL.md", sub(read(tpl["SKILL.template.md"])))
    write(dest / "files" / "INDEX.md", read(tpl["INDEX.template.md"]))
    write(dest / "notes.md", read(tpl["notes.template.md"]))
    write(dest / "runs.jsonl", "")
    print(f"OK playbook créé : {dest}")
    if new_root:
        print(f"NOTE : dossier skills créé ({root}). Redémarre Claude Code pour que le playbook soit détecté.")
    return 0


def cmd_validate(a):
    R = validate_pb(resolve_pb(a.cible))
    if a.json:
        print(json.dumps([{"level": l, "rule": r, "message": m} for l, r, m in R], ensure_ascii=False, indent=2))
    else:
        for l, r, m in R:
            print(f"{l} {r} : {m}")
    return 1 if any(l == "FAIL" for l, _, _ in R) else 0


def _date(a):
    d = a.date or today()
    if not re.fullmatch(DATE, d):
        raise Usage("--date attendu au format AAAA-MM-JJ")
    return d


def cmd_index(a):
    pb = resolve_pb(a.nom)
    if not (pb / "files" / a.file).is_file():
        print(f"WARN fichier absent de files/ : {a.file}", file=sys.stderr)
    add_index(pb, a.file, a.purpose, _date(a))
    print(f"OK indexé : {a.file}")
    return 0


def cmd_note(a):
    add_note(resolve_pb(a.nom), a.layer, a.error, a.fix, _date(a))
    print("OK note ajoutée")
    return 0


def cmd_audit(a):
    if bool(a.nom) == bool(a.all):
        raise Usage("donner un nom ou --all")
    pbs = discover() if a.all else [("", resolve_pb(a.nom))]
    res = [{"name": pb.name, "findings": audit_pb(pb)} for _, pb in pbs]
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for r in res:
            for f in r["findings"]:
                print(f"{r['name']} | {f['kind']} | {f['msg']}")
            if not r["findings"]:
                print(f"{r['name']} | RAS")
    return 0


def cmd_dashboard(a):
    data = build_data(discover())
    out = Path(a.out) if a.out else config_dir() / "playbook-forge" / "dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    write(out, render(data))
    print(summary(data))
    print(f"Dashboard : {out}")
    if not a.no_open:
        webbrowser.open(out.resolve().as_uri())
    return 0


def cmd_export(a):
    pb = resolve_pb(a.nom)
    print(f"OK export : {export_zip(pb, a.out or Path.cwd())}")
    return 0


def cmd_config(a):
    cfg = load_cfg(strict=True)
    if a.add_root:
        r = str(Path(a.add_root).resolve())
        if r not in cfg.setdefault("extra_roots", []):
            cfg["extra_roots"].append(r)
        cfg_file().parent.mkdir(parents=True, exist_ok=True)
        write(cfg_file(), json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
    return 0


def cmd_selftest(a):
    src = REPO / "examples" / "relance-factures"
    if not (src / "SKILL.md").is_file():
        print(f"FAIL exemple introuvable : {src}")
        return 1
    ok = True
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        pb = t / "skills" / "relance-factures"
        shutil.copytree(src, pb)

        def step(label, fn):
            nonlocal ok
            try:
                fn()
                print("PASS", label)
            except Exception as e:  # noqa: BLE001
                ok = False
                print("FAIL", label, "-", e)

        def no_fail():
            bad = [m for l, _, m in validate_pb(pb) if l == "FAIL"]
            assert not bad, bad[0]

        def idx():
            write(pb / "files" / "selftest-outil.md", "outil de test\n")
            add_index(pb, "selftest-outil.md", "outil de test", today())
            no_fail()

        def note():
            add_note(pb, "outils", "erreur test", "correction test", today())
            good, bad = read_rows(pb / "notes.md", NOTE)
            assert not bad and good[0][2] == "erreur test", "note absente ou mal placée"

        def runs():
            for i in range(5):
                add_run(pb, {"type": "run", "date": today(), "passed": 5, "failed": 1 if i < 3 else 0,
                             "unverified": 0, "failed_checks": ["check test"] if i < 3 else [], "note": "faux run"})
            assert not read_runs(pb)[1], "runs.jsonl invalide"

        def aud():
            assert any(f["kind"] == "check_echoue" for f in audit_pb(pb)), "check en échec non détecté"

        def dash():
            html = render(build_data([("perso", pb)]))
            write(t / "dashboard.html", html)
            assert not re.search(r"""(src|href)\s*=\s*["']?http""", html), "URL http dans src/href"

        def exp():
            names = zipfile.ZipFile(export_zip(pb, t)).namelist()
            assert "relance-factures/SKILL.md" in names and "relance-factures/runs.jsonl" not in names, names

        for label, fn in (("validate", no_fail), ("index", idx), ("note", note), ("runs", runs),
                          ("audit", aud), ("dashboard", dash), ("export", exp)):
            step(label, fn)
    return 0 if ok else 1


def build_parser():
    ap = argparse.ArgumentParser(prog="pbf", description="playbook-forge")
    sp = ap.add_subparsers(dest="cmd", required=True)

    def cmd(name, fn):
        p = sp.add_parser(name)
        p.set_defaults(fn=fn)
        return p

    cmd("doctor", cmd_doctor)
    cmd("list", cmd_list).add_argument("--json", action="store_true")
    p = cmd("scaffold", cmd_scaffold)
    p.add_argument("nom")
    p.add_argument("--scope", choices=["perso", "projet"], required=True)
    p.add_argument("--root")
    p = cmd("validate", cmd_validate)
    p.add_argument("cible")
    p.add_argument("--json", action="store_true")
    p = cmd("index", cmd_index)
    p.add_argument("nom")
    p.add_argument("--file", required=True)
    p.add_argument("--purpose", required=True)
    p.add_argument("--date")
    p = cmd("note", cmd_note)
    p.add_argument("nom")
    p.add_argument("--layer", choices=["instructions", "outils", "checks"], required=True)
    p.add_argument("--error", required=True)
    p.add_argument("--fix", required=True)
    p.add_argument("--date")
    p = cmd("audit", cmd_audit)
    p.add_argument("nom", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    p = cmd("dashboard", cmd_dashboard)
    p.add_argument("--out")
    p.add_argument("--no-open", action="store_true")
    p = cmd("export", cmd_export)
    p.add_argument("nom")
    p.add_argument("--out")
    p = cmd("config", cmd_config)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--add-root")
    g.add_argument("--show", action="store_true")
    cmd("selftest", cmd_selftest)
    return ap


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")
    a = build_parser().parse_args(argv)
    try:
        return a.fn(a)
    except Usage as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 2
    except Fail as e:
        print(f"FAIL {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
