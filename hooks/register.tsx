import type { Register } from 'claude-code'

import { panelAfterTool, panelStart, register as panel } from './panel'
import { guardWriter, watchAfterTool, watchStart, register as watch } from './watch'

// hooks.json ne prend qu'un module, et un événement sans matcher qu'un hook : ils sont partagés ici.
export const register: Register = (on, options) => {
  on('session.start', async ($, e, next) => {
    try {
      await panelStart($)
      await watchStart($, e)
    } catch {
      // une commande non enregistrée ne doit pas bloquer la session
    }
    return next(e)
  })

  on('tool.call', async ($, e, next) => {
    const deny = await guardWriter($, e)
    if (deny) return { deny }
    const ran = await next(e)
    try {
      await panelAfterTool($, e)
      await watchAfterTool($, e, ran)
    } catch {
      // observation seulement : jamais relancer l'outil pour une erreur ici
    }
    return ran
  }).catch(($, e, next) => (e.agentId ? { deny: 'skill-forge : garde en erreur, appel refusé' } : next(e)))

  panel(on, options)
  watch(on, options)
}
