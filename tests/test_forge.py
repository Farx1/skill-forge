import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FORGE = REPO / "scripts" / "forge.py"

CHECKS = "\n".join(f"- [ ] verification {i} | Preuve : comptage {i} | Échec si : zéro" for i in range(5))
VALID = f"""---
name: @NAME@
description: Fait la démo. Utilise ce skill dès que je tape « lance la démo ».
metadata:
  skill-forge: "1"
  created: "2026-01-01"
---
# Démo

## Objectif
Faire la démo.

## Quand l'utiliser
Chaque lundi.

## Entrées
- Fichier : dossier courant

## Étapes
1. Ouvrir le modèle relance-template.md.
2. Remplir les champs.
3. Envoyer au relecteur.

## Décisions
- Si le montant dépasse 1000, alors prévenir le chef.

## Boîte à outils
| Fichier | Usage | Quand ne pas l'utiliser |
|---|---|---|
| relance-template.md | message | jamais |

## Définition de terminé
{CHECKS}

## Cas particuliers
- Client absent : reporter.

## Après chaque exécution
Ajouter une ligne à ${{CLAUDE_SKILL_DIR}}/runs.jsonl.
"""


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.tmp = Path(self._t.name)
        self.cfg = self.tmp / "cfg"
        self.proj = self.tmp / "proj"
        (self.proj / ".git").mkdir(parents=True)
        self.env = {**os.environ, "CLAUDE_CONFIG_DIR": str(self.cfg)}
        self.skills = self.cfg / "skills"

    def tearDown(self):
        self._t.cleanup()

    def run_forge(self, *args):
        p = subprocess.run([sys.executable, str(FORGE), *args], cwd=self.proj, env=self.env,
                           capture_output=True, encoding="utf-8")
        return p.returncode, p.stdout + p.stderr

    def make(self, name="demo", skill=None, tool=True):
        d = self.skills / name
        (d / "files").mkdir(parents=True)
        (d / "examples").mkdir()
        (d / "SKILL.md").write_text((skill or VALID).replace("@NAME@", name), encoding="utf-8", newline="\n")
        (d / "notes.md").write_text("# Notes\n", encoding="utf-8", newline="\n")
        (d / "runs.jsonl").write_text("", encoding="utf-8")
        idx = "# Index\n"
        if tool:
            (d / "files" / "relance-template.md").write_text("Bonjour [prénom]\n", encoding="utf-8")
            idx += "- relance-template.md | message | 2026-01-01\n"
        (d / "files" / "INDEX.md").write_text(idx, encoding="utf-8", newline="\n")
        return d


class TestForge(Base):
    def test_scaffold_creates_tree(self):
        rc, out = self.run_forge("scaffold", "mon-job", "--scope", "perso")
        self.assertEqual(rc, 0, out)
        d = self.skills / "mon-job"
        for f in ("SKILL.md", "files/INDEX.md", "notes.md", "runs.jsonl"):
            self.assertTrue((d / f).is_file(), f)
        text = (d / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: mon-job", text)
        self.assertNotIn("[nom]", text)
        self.assertRegex(text, r'created: "\d{4}-\d{2}-\d{2}"')
        self.assertIn("redémarre", out.lower())
        self.assertEqual(self.run_forge("validate", "mon-job")[0], 0)

    def test_scaffold_refuses_existing_and_bad_name(self):
        self.assertEqual(self.run_forge("scaffold", "mon-job", "--scope", "perso")[0], 0)
        self.assertEqual(self.run_forge("scaffold", "mon-job", "--scope", "perso")[0], 1)
        for bad in ("Mon_Job", "synced", "a" * 65):
            self.assertEqual(self.run_forge("scaffold", bad, "--scope", "perso")[0], 2, bad)

    def test_scaffold_projet_scope(self):
        rc, out = self.run_forge("scaffold", "p-job", "--scope", "projet")
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.proj / ".claude" / "skills" / "p-job" / "SKILL.md").is_file())

    def test_validate_valid(self):
        d = self.make()
        rc, out = self.run_forge("validate", str(d))
        self.assertEqual(rc, 0, out)
        self.assertNotIn("FAIL", out)

    def test_validate_missing_section(self):
        d = self.make(skill=VALID.replace("## Cas particuliers", "## Autre"))
        rc, out = self.run_forge("validate", str(d))
        self.assertEqual(rc, 1)
        self.assertIn("Cas particuliers", out)

    def test_validate_english_titles(self):
        en = VALID
        for fr, e in (("Objectif", "Purpose"), ("Étapes", "Steps"), ("Décisions", "Decisions")):
            en = en.replace(f"## {fr}", f"## {e}")
        self.assertEqual(self.run_forge("validate", str(self.make(skill=en)))[0], 0)

    def test_validate_unindexed_file(self):
        d = self.make()
        (d / "files" / "autre-outil.md").write_text("x\n", encoding="utf-8")
        rc, out = self.run_forge("validate", str(d))
        self.assertEqual(rc, 1)
        self.assertIn("autre-outil.md", out)

    def test_validate_secret(self):
        d = self.make()
        (d / "files" / "relance-template.md").write_text("api_key=abc123\n", encoding="utf-8")
        rc, out = self.run_forge("validate", str(d))
        self.assertEqual(rc, 1)
        self.assertIn("secret", out)

    def test_validate_invalid_name(self):
        d = self.make(skill=VALID.replace("name: @NAME@", "name: Demo_X"))
        rc, out = self.run_forge("validate", str(d))
        self.assertEqual(rc, 1)
        self.assertIn("FAIL nom", out)

    def test_validate_too_few_checks(self):
        d = self.make(skill=VALID.replace(CHECKS, "\n".join(CHECKS.split("\n")[:3])))
        rc, out = self.run_forge("validate", str(d))
        self.assertEqual(rc, 1)
        self.assertIn("FAIL checks", out)

    def test_index_adds_line(self):
        d = self.make()
        (d / "files" / "echelle.md").write_text("x\n", encoding="utf-8")
        rc, out = self.run_forge("index", str(d), "--file", "echelle.md", "--purpose", "niveaux", "--date", "2026-02-03")
        self.assertEqual(rc, 0, out)
        self.assertIn("- echelle.md | niveaux | 2026-02-03\n", (d / "files" / "INDEX.md").read_text(encoding="utf-8"))
        self.assertEqual(self.run_forge("validate", str(d))[0], 0)

    def test_note_most_recent_on_top(self):
        d = self.make()
        self.run_forge("note", str(d), "--layer", "outils", "--error", "ancienne", "--fix", "f1", "--date", "2026-01-05")
        self.run_forge("note", str(d), "--layer", "checks", "--error", "récente", "--fix", "f2", "--date", "2026-02-05")
        lines = [l for l in (d / "notes.md").read_text(encoding="utf-8").split("\n") if l.startswith("- ")]
        self.assertEqual(lines, ["- 2026-02-05 | checks | récente | f2", "- 2026-01-05 | outils | ancienne | f1"])
        self.assertEqual(self.run_forge("validate", str(d))[0], 0)

    def test_audit_repeated_error(self):
        d = self.make()
        for day in ("2026-01-05", "2026-02-05"):
            self.run_forge("note", str(d), "--layer", "instructions", "--error", "oubli de la TVA sur la facture",
                         "--fix", "règle", "--date", day)
        rc, out = self.run_forge("audit", str(d), "--json")
        self.assertEqual(rc, 0, out)
        self.assertIn("erreur_repetee", [f["kind"] for f in json.loads(out)[0]["findings"]])

    def test_audit_uncited_and_failing_checks(self):
        d = self.make()
        (d / "files" / "orphelin.md").write_text("x\n", encoding="utf-8")
        run = {"type": "run", "date": "2026-03-01", "passed": 4, "failed": 1, "unverified": 0,
               "failed_checks": ["verification 1"], "note": ""}
        (d / "runs.jsonl").write_text((json.dumps(run) + "\n") * 2, encoding="utf-8")
        rc, out = self.run_forge("audit", str(d), "--json")
        kinds = [f["kind"] for f in json.loads(out)[0]["findings"]]
        self.assertIn("non_cite", kinds)
        self.assertIn("check_echoue", kinds)
        self.assertIn("audit_du", kinds)

    def test_status_json(self):
        self.make()
        rc, out = self.run_forge("status", "--json")
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertEqual(data["stats"]["skills"], 1)
        sk = data["skills"][0]
        self.assertEqual(sk["name"], "demo")
        self.assertEqual(set(sk["layers"]), {"Étapes", "Outils", "Checks"})
        self.assertIn("top_failing", sk)
        self.assertNotIn("runs", sk)

    def test_export_contains_skill_under_name(self):
        d = self.make()
        outdir = self.tmp / "out"
        rc, out = self.run_forge("export", str(d), "--out", str(outdir))
        self.assertEqual(rc, 0, out)
        names = zipfile.ZipFile(outdir / "demo.zip").namelist()
        self.assertIn("demo/SKILL.md", names)
        self.assertIn("demo/files/relance-template.md", names)
        self.assertNotIn("demo/runs.jsonl", names)

    def test_export_refuses_non_portable_keys(self):
        d = self.make(skill=VALID.replace("metadata:", "model: x\nmetadata:", 1))
        self.assertEqual(self.run_forge("export", str(d), "--out", str(self.tmp / "o"))[0], 1)

    def log(self, *lines):
        (self.cfg / "logs").mkdir(parents=True, exist_ok=True)
        (self.cfg / "logs" / "skill-usage.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_usage_counted_namespaced_and_absent(self):
        d = self.make()
        rc, out = self.run_forge("status", "--json")
        self.assertIsNone(json.loads(out)["skills"][0]["uses_30d"])
        from datetime import date
        t = date.today().isoformat()
        self.log(f"{t}\tdemo\t/x", f"{t}T10:00:00\tplug:demo\t/x", "2020-01-01\tdemo\t/x", "n'importe quoi", f"{t}\tautre\t/x")
        rc, out = self.run_forge("status", "--json")
        s = json.loads(out)["skills"][0]
        self.assertEqual(s["uses_30d"], 2)
        self.assertEqual(s["last_used"], t)

    def test_audit_never_used(self):
        d = self.make()
        kinds = lambda: [f["kind"] for f in json.loads(self.run_forge("audit", str(d), "--json")[1])[0]["findings"]]
        self.assertNotIn("jamais_utilise", kinds())
        from datetime import date
        self.log(f"{date.today().isoformat()}\tautre\t/x")
        self.assertNotIn("jamais_utilise", kinds())  # journal récent : pas de couverture 60 jours, pas d'alerte
        self.log("2020-01-01\tdemo\t/x")
        self.assertIn("jamais_utilise", kinds())

    def test_paths_warn_and_export_strips(self):
        for fm in ('paths:\n  - "**/*.tsx"\n  - "*.sql"\n', 'paths: ["**/*.tsx", "*.sql"]\n'):
            d = self.make(name="pth", skill=VALID.replace("metadata:", fm + "metadata:", 1))
            rc, out = self.run_forge("validate", str(d))
            self.assertEqual(rc, 0, out)
            self.assertRegex(out, r"WARN.*paths")
            outdir = self.tmp / "o"
            self.assertEqual(self.run_forge("export", str(d), "--out", str(outdir))[0], 0)
            sk = zipfile.ZipFile(outdir / "pth.zip").read("pth/SKILL.md").decode("utf-8")
            self.assertNotIn("paths", sk)
            self.assertNotIn("tsx", sk)
            self.assertIn("skill-forge", sk)
            shutil.rmtree(d)

    def test_accents_roundtrip(self):
        d = self.make()
        err = "Échec à l'étape été : œuf ç ñ"
        self.run_forge("note", str(d), "--layer", "outils", "--error", err, "--fix", "corrigé", "--date", "2026-02-05")
        raw = (d / "notes.md").read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertIn(f"- 2026-02-05 | outils | {err} | corrigé".encode("utf-8"), raw)
        self.assertIn(err, json.loads(self.run_forge("status", "--json")[1])["skills"][0]["notes"][0]["error"])
        rc, out = self.run_forge("validate", str(d), "--json")
        self.assertEqual(rc, 0, out)

    def test_list_and_config_extra_root(self):
        self.make()
        extra = self.tmp / "extra"
        (extra / "autre").mkdir(parents=True)
        (extra / "autre" / "SKILL.md").write_text(VALID.replace("@NAME@", "autre"), encoding="utf-8")
        self.assertEqual(self.run_forge("config", "--add-root", str(extra))[0], 0)
        rc, out = self.run_forge("list", "--json")
        self.assertEqual(rc, 0, out)
        self.assertEqual(sorted(r["name"] for r in json.loads(out)), ["autre", "demo"])

    def test_status_survives_latin1_skill(self):
        d = self.make()
        (d / "SKILL.md").write_bytes(VALID.replace("@NAME@", "demo").encode("latin-1", "replace"))
        (d / "SKILL.md").write_bytes((d / "SKILL.md").read_bytes() + "é".encode("latin-1"))
        rc, out = self.run_forge("status", "--json")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("Traceback", out)
        self.assertIn("UTF-8", out)
        self.assertEqual(self.run_forge("validate", str(d))[0], 1)

    def test_citation_is_whole_word(self):
        d = self.make(skill=VALID.replace("relance-template.md", "data.md"))
        (d / "files" / "a.md").write_text("x\n", encoding="utf-8")
        (d / "files" / "data.md").write_text("x\n", encoding="utf-8")
        (d / "files" / "INDEX.md").write_text("- a.md | u | 2026-01-01\n- data.md | u | 2026-01-01\n", encoding="utf-8")
        rc, out = self.run_forge("validate", str(d))
        self.assertIn("non cités dans SKILL.md : a.md", out)

    def test_doctor(self):
        rc, out = self.run_forge("doctor")
        self.assertEqual(rc, 0, out)
        self.assertIn("Python", out)

    @unittest.skipUnless((REPO / "examples" / "relance-factures" / "SKILL.md").is_file(), "démo absente")
    def test_selftest(self):
        rc, out = self.run_forge("selftest")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("FAIL", out)


if __name__ == "__main__":
    unittest.main()
