# Déployer et livrer

Ce guide couvre tout ce qui fait passer un commit en production : les déclencheurs, le
cycle de vie d'une release, les stratégies de rollout, l'approbation, les fenêtres de gel,
les previews, le rollback et la gestion de la dérive.

## Trois déclencheurs, un seul chemin

| Déclencheur | Comment | Quand l'utiliser |
|---|---|---|
| **Push** | Un commit arrive sur la branche ou le tag suivi (`track`) par un environnement | Le défaut. Trunk-based sur `main` vers le staging, ou `tags/v*` vers un environnement de recette. |
| **Promotion** | `nlk promote <from> <to>` copie le digest et le SHA de la release live de `<from>` | La production. Aucun build : ce qui a été testé est ce qui part. |
| **Manuel** | `nlk deploy --env <env> --ref <ref>` | Un hotfix depuis une branche non suivie, un test d'une branche, un déploiement piloté par votre propre CI. |

Les trois produisent la même chose : une **release**, un commit dans le manifest store, que
ArgoCD applique. La CLI n'applique jamais rien au cluster en contournant Git.

## Le cycle de vie d'une release

```
building → pending-checks → pending-approval → queued (freeze) → rolling-out → live
                                    ↘ rejected                ↘ failed → rolled-back
                                                                        superseded
```

| Statut | Signification |
|---|---|
| `building` | Image en construction. Un changement de manifeste seul saute cette étape. |
| `pending-checks` | Attend que les checks du Git host soient verts (`deploy.requireChecks`). |
| `pending-approval` | Attend `nlk releases approve` par un owner (`deploy.approval: owner`). |
| `queued` | Dans une fenêtre de gel (`deploy.freeze`), partira à la fin. |
| `rolling-out` | Rollout en cours : rolling, canari ou blue-green. |
| `live` | Sert le trafic. Une seule release live par environnement. |
| `failed` / `rolled-back` | Rollout échoué ; l'ancienne release sert toujours ou a été restaurée. |
| `superseded` | Remplacée par une release plus récente avant d'être live. |

```bash
nlk releases --env prod
nlk releases show prod/#42          # commits inclus, diff du manifeste, digest, analyse canari
```

## Stratégies de rollout

Déclarées dans `deploy.strategy`, par défaut ou par environnement.

### `rolling` (défaut)

Deployment Kubernetes standard : les pods sont remplacés progressivement, jamais moins de
`scale.min` disponibles. Convient au staging et aux services sans état où un mélange de deux
versions pendant quelques secondes est acceptable.

### `canary`

```yaml
deploy:
  strategy: canary
  canary:
    steps: [10%, 50%, 100%]
    interval: 2m
    analysis: { errorRate: 1%, p95Latency: 500ms }
    onFailure: rollback          # ou pause
```

La nouvelle version reçoit 10 % du trafic pendant deux minutes. Argo Rollouts mesure le
taux d'erreur et la latence p95 **de la version canari seulement**, via les métriques
Prometheus déjà collectées. Si les seuils tiennent, 50 %, puis 100 %. Sinon, retour
automatique à la release précédente et notification. `onFailure: pause` gèle à la place, pour
une décision humaine (`nlk releases resume prod` ou `nlk rollback`).

### `blueGreen`

```yaml
deploy:
  strategy: blueGreen
  blueGreen: { previewDuration: 10m }
```

La nouvelle version démarre sans trafic, joignable sur `<app>-preview.<project>.nolockin.app`
pendant `previewDuration`, puis bascule d'un coup. Avec `approval: owner`, la bascule attend
l'approbation au lieu du délai. Utile quand un mélange de versions est inacceptable
(migrations de schéma non rétro-compatibles).

## Approbation

```yaml
environments:
  prod:
    deploy: { approval: owner }
```

Chaque release de production attend un owner. `nlk promote` affiche le diff, la console et
Slack notifient, `nlk releases approve prod/#42` libère. `nlk releases reject prod/#42
--reason "..."` abandonne. Avec un manifest repo à vous, la PR de promotion remplace tout ça :
la merger vaut approbation.

## Fenêtres de gel

```yaml
deploy:
  freeze:
    - "Fri 16:00 - Mon 08:00 Europe/Paris"
    - "Dec 20 - Jan 3 Europe/Paris"
```

Pendant une fenêtre, les releases passent en `queued` et partent à la fin. Un owner peut
forcer avec `nlk releases approve --override-freeze`, tracé comme tel.

## Prévisualisations par pull request

```yaml
environments:
  staging:
    track: main
    deploy: { previews: { enabled: true, ttl: 7d } }
```

Chaque PR vers `main` déploie `shop-api-pr-42` dans le projet de staging, avec ses propres
add-ons en plan minimal et une URL `shop-api-pr-42.acme-staging.nolockin.app`, postée en
commentaire sur la PR. Détruite au merge, à la fermeture, ou après `ttl`. Les previews
utilisent les secrets du staging : n'y mettez rien de production.

```bash
nlk previews --env staging
nlk previews open 42
nlk previews destroy 42
```

## Rollback

```bash
nlk rollback --env prod                 # vers la release live précédente
nlk rollback --env prod --to 39         # vers une release précise
```

Un rollback est une **nouvelle release** avec le digest et le manifeste d'une release
passée. Il est historisé, donc lui-même annulable. Il respecte `approval` et `freeze` sauf
`--emergency`, qui les court-circuite et notifie les owners.

## Modifications d'urgence et dérive

Les commandes impératives appliquent tout de suite et réécrivent le manifeste via une PR :

```bash
nlk scale web --min 6 --env prod
# ✔ appliqué sur acme-prod (release prod/#42 + override)
# ✔ PR ouverte : acme/shop-api#213 « nolockin: prod web.scale.min 3 → 6 »
# ⚠ dérive : 1 réglage non mergé
```

L'override persiste à travers les releases suivantes jusqu'à ce que le manifeste contienne la
même valeur (PR mergée puis promue) ou que vous l'effaciez :

```bash
nlk status --env prod                   # affiche les overrides actifs
nlk override clear web.scale.min --env prod
```

## Intégrer votre CI

Deux façons, cumulables :

- **Laisser NoLockIn attendre vos checks.** `deploy.requireChecks: true` : la release ne part que si les checks GitHub ou GitLab du commit sont verts. Aucune configuration côté CI.
- **Piloter depuis la CI.** Après vos tests, `nlk deploy --env recette --ref $GITHUB_SHA` avec un jeton `nlk token create`. Utile pour un environnement qui ne suit aucune branche mais reçoit les builds d'un pipeline précis.

À la fin d'une release, NoLockIn poste un commit status `nolockin/<env>: live` avec un lien
vers Grafana, et pose le tag `nlk/<env>` si `tagOnRelease` est activé.

## Voir aussi

- [Référence du manifeste, section `deploy`](../reference/manifeste.md#politique-de-release--deploy)
- [Référence de la CLI, releases et promotion](../reference/cli.md#releases-et-promotion)
- [ADR-0007, politique dans le dépôt source, état dans le manifest store](../architecture/adr/0007-policy-in-repo-state-in-store.md)
