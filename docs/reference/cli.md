# 03 · La CLI `nlk`

`nlk` est un binaire Go statique (Linux, macOS, Windows). C'est l'interface principale ;
la console web n'expose rien que la CLI ne fasse pas.

## Principes

- **Le déploiement par défaut, c'est `git push`.** Un push sur la branche suivie d'un environnement produit une release. `nlk deploy` est le déclencheur manuel du même chemin.
- **La CLI est un client Git avec du sucre.** `nlk deploy`, `nlk promote`, `nlk releases approve`, `nlk rollback` produisent un **commit dans le manifest store** qu'ArgoCD applique. Rien n'est appliqué au cluster en contournant Git.
- **La politique est réécrite dans le fichier, pas contournée.** `nlk scale`, `nlk env set`, `nlk domain add` modifient `nolockin.yaml` (ou l'overlay de l'environnement) et ouvrent une PR sur le dépôt source. En urgence, l'effet est immédiat et la dérive est affichée jusqu'au merge.
- **Un contexte, une plateforme.** Toute commande s'exécute contre le contexte courant. `--context <nom>` le surcharge.
- **Sortie lisible par défaut, `--json` partout.** Codes de retour stables.
- **Les commandes de sortie n'ont aucune précondition de compte.**

## Installation

```bash
curl -fsSL https://get.nolockin.io | sh      # ou brew install nolockin/tap/nlk
nlk version
```

## Contextes

```bash
nlk login                                   # OIDC vers le contexte courant (hosted par défaut)
nlk context list
nlk context add mon-cluster --server https://nlk.infra.acme.internal
nlk context use mon-cluster
nlk context current
```

Fichier : `~/.config/nolockin/config.yaml` ([format](../architecture/vue-d-ensemble.md#le-modèle-de-contexte)).

## Résolution de l'environnement

Toute commande qui agit sur une app prend `--env <nom>`. Sans le flag :

1. Si le manifeste n'a pas d'`environments`, l'environnement implicite `default`.
2. Sinon, l'environnement dont le `track` correspond à la branche Git courante du dossier.
3. Sinon, erreur : `--env` requis. Jamais de choix silencieux de la prod.

## Première mise en ligne

```bash
nlk init                       # génère nolockin.yaml, crée la deploy key et le webhook, propose le projet
nlk init --environments staging,prod
git add nolockin.yaml && git commit -m "nolockin: manifeste" && git push
# → build → release staging → https://shop-api-acme-staging.nolockin.app
```

Le premier push suffit. `nlk deploy` n'est pas nécessaire.

## Cycle de vie

| Commande | Effet |
|---|---|
| `nlk validate` | Valide le manifeste et chaque environnement fusionné ([règles](manifeste.md#validation)). |
| `nlk manifest show --env prod` | Manifeste effectif après fusion base + overlay. |
| `nlk deploy [--env <env>] [--ref <ref>] [--watch]` | **Déclencheur manuel.** Build si nécessaire, crée une release dans l'environnement, suit le rollout. Soumis à `approval` et `freeze`. Cas d'usage : ref non suivi, hotfix, dossier local (`--local`), CI externe. |
| `nlk status [--env <env>]` | Release live, services, réplicas, santé, add-ons, dérive éventuelle. |
| `nlk logs [service] [-f] [--since 1h] [--grep ...] [--env]` | Logs Loki. |
| `nlk ps [--env]` | Pods, CPU/mémoire instantanés, redémarrages. |
| `nlk exec <service> -- <cmd>` | Shell dans un pod éphémère. |
| `nlk run -- <cmd>` | Job one-shot avec l'image et l'env de la release live (migrations). |
| `nlk render [--env <env>]` | Kubernetes YAML équivalent sur stdout. |
| `nlk destroy --env <env>` | Supprime l'app dans cet environnement. Propose `nlk export` d'abord. |

## Releases et promotion

Une **release** = un digest d'image + le SHA source (code et manifeste) + l'overlay de
l'environnement, rendus ensemble. Elle vit dans le manifest store, jamais dans le dépôt source.

| Commande | Effet |
|---|---|
| `nlk releases [--env <env>]` | Historique : numéro, statut, SHA, digest, auteur, déclencheur (push, promote, deploy), durée. |
| `nlk releases show prod/#42` | Détail : commits inclus depuis la release précédente, diff du manifeste effectif, digest, analyse canari. |
| `nlk promote <from> <to> [--release <n>]` | Crée dans `<to>` une release avec le digest et le SHA de la release live de `<from>` (ou de `--release`), rendue avec l'overlay de `<to>`. **Aucun build.** Soumise à `approval` et `freeze` de `<to>`. |
| `nlk releases approve <env>/#<n>` | Réservé aux `owner`. Commit la release en attente dans le manifest store, ArgoCD synchronise. Avec `strategy: canary`, le rollout progressif démarre. |
| `nlk releases reject <env>/#<n> [--reason]` | Abandonne une release en attente. |
| `nlk releases pause / resume <env>` | Gèle ou reprend un canari en cours. |
| `nlk rollback [--env <env>] [--to <n>]` | Nouvelle release avec le digest et le SHA d'une release précédente (défaut : la précédente live). C'est un commit, donc historisé, donc lui-même annulable. |

### Statuts d'une release

```
building → pending-checks → pending-approval → queued (freeze) → rolling-out → live
                                    ↘ rejected                ↘ failed → rolled-back
                                                                        superseded
```

### Exemple de journée

```bash
git push origin main                          # release staging/#118, automatique
nlk releases --env staging                    # #118 live · 3 commits · 1m52s
nlk promote staging prod                      # prod/#42 pending-approval · diff affiché
nlk releases approve prod/#42                 # canary 10 % → 50 % → 100 %, 6 min
nlk releases show prod/#42                    # live · analyse : errorRate 0.2 % · p95 310 ms
```

## Modifications impératives et dérive

```bash
nlk scale web --min 6 --env prod
# ✔ appliqué sur acme-prod (release prod/#42 + override)
# ✔ PR ouverte : acme/shop-api#213 « nolockin: prod web.scale.min 3 → 6 »
# ⚠ dérive : 1 réglage non mergé. `nlk status --env prod` l'affiche jusqu'au merge.
```

Règles :

- L'override s'applique immédiatement à la release live et **persiste à travers les releases suivantes** tant qu'il n'est pas dans le manifeste.
- Il disparaît de lui-même quand une release contient la même valeur (PR mergée puis promue), ou explicitement avec `nlk override clear web.scale.min --env prod`.
- `nlk status` et la console affichent chaque override. ArgoCD montre la ressource comme synchronisée : l'override est rendu par l'opérateur, pas appliqué à la main.
- Commandes concernées : `nlk scale`, `nlk env set`, `nlk env rm`, `nlk domain add`, `nlk domain rm`. `--no-pr` supprime l'ouverture de PR, pas l'affichage de la dérive.

## Secrets et configuration

```bash
nlk secret set stripe secret_key=sk_live_... --env prod
nlk secret set stripe secret_key=sk_test_... --env staging
nlk secret list --env prod         # noms et clés, jamais les valeurs
nlk secret rm stripe webhook_secret --env prod
nlk env set LOG_LEVEL=debug --env staging      # réécrit l'overlay, ouvre une PR
```

Les secrets sont **par projet, donc par environnement**. C'est la place naturelle de ce qui
diffère entre staging et prod sans devoir être dans Git. Stockés en Secret Kubernetes
chiffrés au repos, exportables par `nlk export` chiffrés avec la clé publique du contexte
cible.

## Prévisualisations

```bash
nlk previews --env staging         # PR ouvertes → instance, URL, âge, coût du mois
nlk previews open 42               # ouvre https://shop-api-pr-42.acme-staging.nolockin.app
nlk previews destroy 42
```

Créées et détruites automatiquement par les événements PR quand `deploy.previews.enabled`.

## Domaines

```bash
nlk domain add api.acme.com --service web --env prod   # réécrit l'overlay, ouvre une PR
nlk domain verify api.acme.com                         # CNAME/TXT attendus, attend la propagation
nlk domain list --env prod
```

## Add-ons

```bash
nlk addon list --env prod
nlk addon psql db --env prod
nlk addon redis-cli cache --env staging
nlk addon backup db --env prod
nlk addon backups db --env prod
nlk addon restore db --at "2026-09-08T14:00:00Z" --env prod
nlk addon export db --env prod > db.dump      # jamais bridé
nlk addon copy db --from prod --to staging    # rafraîchit le staging depuis un snapshot prod
```

## Observabilité

```bash
nlk open grafana --env prod
nlk open argocd --env prod
nlk metrics [service] [--range 1h] [--env]
nlk alerts [--env]
```

## Usage et facturation

```bash
nlk usage [--project acme-prod] [--month 2026-09] [--by app|service|env|label:team]
nlk usage explain
nlk invoice list
nlk invoice get 2026-08 --pdf
nlk pricing
```

## Sortie

Détails dans [Protocole de sortie](../guides/sortie.md). La sortie se fait **par projet**,
donc par environnement : on peut migrer le staging d'abord, la prod ensuite.

```bash
nlk export --project acme-prod [--include-addons] [--to-context mon-cluster] > acme-prod.nlkbundle
nlk import acme-prod.nlkbundle --context mon-cluster [--dry-run]
nlk exit plan --project acme-prod --to mon-cluster
nlk exit cutover --project acme-prod --to mon-cluster
nlk exit verify --project acme-prod --to mon-cluster
nlk project delete acme-prod --context hosted --certificate
```

## Projets et équipe

```bash
nlk project create acme-prod
nlk project list
nlk project quota acme-prod --cpu 32 --memory 128Gi --storage 1Ti
nlk member add alice@acme.com --role developer --project acme-prod   # owner | developer | viewer | billing
nlk project set acme-prod --manifest-repo git@github.com:acme/deploy.git   # BYO manifest repo
```

Avec un manifest repo à vous, `nlk promote` ouvre une PR dans ce dépôt et la merger vaut
`approve`. Les approbations deviennent des reviews.

## Formats et codes de retour

| Flag | Effet |
|---|---|
| `--json` | Sortie JSON stable (schémas dans `schemas/cli/`). |
| `--context <nom>` | Contexte pour cette commande. |
| `--env <nom>` | Environnement. Voir [résolution](#résolution-de-lenvironnement). |
| `--project <nom>` | Projet, pour les commandes qui ne passent pas par une app. |
| `-q` | Silence sauf erreurs. |

| Code | Sens |
|---|---|
| 0 | Succès |
| 1 | Erreur générique |
| 2 | Manifeste invalide |
| 3 | Authentification requise |
| 4 | Quota dépassé |
| 5 | Rollout échoué, l'ancienne release sert toujours |
| 6 | Sortie : vérification échouée, bascule non effectuée |
| 7 | Release en attente d'approbation ou en file (freeze) : rien n'est en erreur, rien n'est encore live |
| 8 | Environnement ambigu : `--env` requis |

## Ce qui est refusé par conception

- Pas de commande qui écrit une version dans le dépôt source.
- Pas de commande qui modifie une app sans passer par un commit du manifest store.
- Pas de choix implicite de la prod.
- Pas de `--force-delete` sans export préalable proposé.
- Pas de dépendance de la CLI à un service qui n'existe pas en self-hosted.
