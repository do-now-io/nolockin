# 02 · Le manifeste `nolockin.yaml`

Le manifeste est **le seul fichier que l'utilisateur écrit**. Il vit à la racine du dépôt
de l'application, il est versionné avec le code, et il est la source de vérité de la
**politique** de déploiement : ce qui tourne, où, comment ça sort.

Ce qu'il ne contient pas : **la version déployée**. Le digest d'image et le SHA en
production vivent dans le manifest store ([ADR-0007](../architecture/adr/0007-policy-in-repo-state-in-store.md)).
Le fichier dit « la prod, c'est ce projet, avec ces réglages, avec approbation » ; le
manifest store dit « la prod exécute la release #42 ».

## Règles de conception

1. **Chaque champ correspond à des objets Kubernetes standards** ([tableau](../architecture/vue-d-ensemble.md#correspondance-manifeste--kubernetes)). Aucun champ ne dépend d'un service qui n'existerait que sur le cloud hébergé.
2. **Les valeurs par défaut sont production-ready** : 2 réplicas, health check, limites, PDB, TLS.
3. **Les secrets ne sont jamais dans le manifeste.** On y met des références.
4. **La version n'est jamais dans le manifeste.** Pas de SHA, pas de digest. Sinon chaque promotion serait un commit sur le dépôt source, qui déclencherait un build, en boucle.
5. **Un fichier pour tous les environnements.** Une base commune, un overlay par environnement. Deux fichiers divergent en silence ; un overlay rend la différence relisible.
6. **Le schéma est versionné** (`apiVersion`) et publié en JSON Schema dans `schemas/`. `nlk validate` l'applique.
7. **Tout ce que la CLI peut faire, le manifeste peut le déclarer.** Les commandes impératives réécrivent le fichier et ouvrent une PR.
8. **`nolockin.yaml` est exclu du contexte de build.** Un commit qui ne touche que le manifeste ne reconstruit pas l'image : même digest, seul le rendu change.

## Exemple complet

```yaml
apiVersion: nolockin.io/v1
kind: App
metadata:
  name: shop-api
  labels:
    team: checkout

# ------------------------------------------------------------------
# Base : identique dans tous les environnements
# ------------------------------------------------------------------
spec:
  source:
    git: https://github.com/acme/shop-api
    path: .                      # sous-dossier (monorepo)
    build:
      type: buildpacks           # buildpacks | dockerfile | image
      builder: paketobuildpacks/builder-jammy-base
      # dockerfile: ./Dockerfile
      # image: ghcr.io/acme/shop-api   (type: image → pas de build, le tag vient du track ou du deploy)

  services:
    - name: web
      command: ["node", "server.js"]
      port: 8080
      protocol: http             # http | grpc | tcp
      resources: { cpu: 500m, memory: 512Mi }
      scale: { min: 2, max: 10, targetCPU: 70 }
      health: { path: /healthz, interval: 10s, timeout: 3s }
      env:
        PORT: "8080"

  workers:
    - name: queue
      command: ["node", "worker.js"]
      resources: { cpu: 250m, memory: 256Mi }
      scale:
        min: 1
        max: 5
        targetQueue: { addon: cache, key: "jobs:pending", perPod: 100 }

  crons:
    - name: cleanup
      schedule: "0 3 * * *"
      timezone: Europe/Paris
      command: ["node", "cleanup.js"]
      concurrency: forbid

  addons:
    - name: db
      type: postgres
      version: "16"
      extensions: [pgvector, pg_trgm]
    - name: cache
      type: redis
      version: "7"
    - name: uploads
      type: bucket

  env:
    NODE_ENV: production
    DATABASE_URL: { fromAddon: db, key: url }
    REDIS_URL:    { fromAddon: cache, key: url }
    S3_BUCKET:    { fromAddon: uploads, key: bucket }
    STRIPE_KEY:   { fromSecret: stripe, key: secret_key }

  network:
    egress: internet

  observability:
    metrics: { path: /metrics }
    alerts:
      errorRate: 5%
      p95Latency: 800ms
    logs: { retention: 7d }

  deploy:                        # politique par défaut, surchargée par environnement
    requireChecks: true
    strategy: rolling

# ------------------------------------------------------------------
# Environnements : un projet chacun, un overlay chacun
# ------------------------------------------------------------------
environments:
  staging:
    project: acme-staging
    track: main                  # chaque push sur main → build → release staging
    deploy:
      previews: { enabled: true, ttl: 7d }
    services:
      web:
        scale: { min: 1, max: 2 }
        routes: [{ host: staging-api.acme.com }]
    addons:
      db: { plan: single, storage: 5Gi }
      cache: { memory: 128Mi }
    env:
      LOG_LEVEL: debug
    observability:
      alerts: { notify: [slack:checkout-staging] }

  prod:
    project: acme-prod
    # pas de track : la prod ne suit rien, elle reçoit des promotions (nlk promote)
    deploy:
      approval: owner
      strategy: canary
      canary:
        steps: [10%, 50%, 100%]
        interval: 2m
        analysis: { errorRate: 1%, p95Latency: 500ms }
        onFailure: rollback
      freeze: ["Fri 16:00 - Mon 08:00 Europe/Paris"]
      tagOnRelease: true
    services:
      web:
        scale: { min: 3, max: 20 }
        routes:
          - { host: api.acme.com, redirectWWW: true }
    addons:
      db:
        plan: ha
        storage: 50Gi
        backups: { schedule: "0 */6 * * *", retention: 30d }
      cache: { memory: 512Mi }
      uploads: { versioning: true }
    observability:
      alerts: { notify: [slack:checkout-alerts, pagerduty:checkout] }
      logs: { retention: 30d }
```

## Environnements

### Deux formes valides

| Forme | Quand | Règles |
|---|---|---|
| **Sans `environments`** | Un seul environnement | `metadata.project` obligatoire, `spec.source.ref` (défaut `main`) est la branche suivie. Équivaut à un environnement implicite `default`. C'est la forme de [`examples/minimal.yaml`](../../examples/minimal.yaml). |
| **Avec `environments`** | Plusieurs environnements | `metadata.project` et `spec.source.ref` interdits. Chaque environnement porte son `project` et son `track`. |

### Champs d'un environnement

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `project` | string DNS-1123 | oui | Projet cible = namespace, quota, facture. Un projet par environnement. |
| `track` | string | non | Branche (`main`), glob de tags (`tags/v*`). Chaque push correspondant déclenche build et release. **Absent : l'environnement ne reçoit que des promotions** (`nlk promote`) ou des déploiements manuels (`nlk deploy --env`). |
| `deploy` | objet | non | Politique de release, fusionnée sur `spec.deploy`. |
| `services`, `workers`, `crons`, `addons` | map nom → overlay | non | Surcharges par nom d'élément. |
| `env`, `network`, `observability` | objet | non | Fusionnés sur la base. |

### Règles de fusion

- **Scalaires** : l'overlay remplace (`scale.min: 3` remplace `2`).
- **Maps** : fusion clé par clé, récursive (`env`, `resources`, `alerts`).
- **Listes de la base indexées par nom** (`services[]`, `workers[]`, `crons[]`, `addons[]`) : l'overlay les adresse **par nom sous forme de map**. Un nom absent de la base crée l'élément (tous les champs obligatoires requis). `disabled: true` retire l'élément pour cet environnement.
- **Listes à l'intérieur d'un élément** (`routes`, `extensions`, `notify`, `freeze`, `steps`) : l'overlay **remplace la liste entière**. Pas de fusion d'éléments de liste : c'est prévisible et ça se relit.
- `nlk manifest show --env prod` affiche le manifeste effectif après fusion.

### Overlays dans des fichiers séparés

Pour une équipe qui veut une propriété distincte de la prod (CODEOWNERS), un overlay peut
vivre dans `environments/<env>.yaml` à côté du manifeste. Même sémantique, même fusion.
Un environnement ne peut être défini qu'à un seul endroit.

```
nolockin.yaml                # base + environments.staging
environments/prod.yaml       # environments.prod, protégé par CODEOWNERS
```

### Prévisualisations (previews)

Sur un environnement qui suit une branche avec `deploy.previews.enabled: true`, chaque pull
request ciblant cette branche déploie une instance éphémère `<app>-pr-<n>` dans le projet
de cet environnement, avec ses propres add-ons (plans minimaux) et une route
`<app>-pr-<n>.<project>.nolockin.app`. Détruite au merge ou à la fermeture, ou après `ttl`.
Facturée sur le projet de l'environnement.

## Politique de release : `deploy`

Définie dans `spec.deploy` (défauts) et surchargée par environnement.

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `requireChecks` | bool | `true` | Attend que les checks du Git host (GitHub Checks, GitLab pipelines) du commit soient verts avant de builder. Un commit rouge ne produit pas de release. |
| `strategy` | enum | `rolling` | `rolling` : Deployment standard. `blueGreen` : nouvelle version sans trafic pendant `blueGreen.previewDuration`, joignable sur `<app>-preview.<project>.nolockin.app`, puis bascule. `canary` : trafic pondéré par étapes, analyse automatique. |
| `canary.steps` | []% | `[10%, 50%, 100%]` | Parts de trafic successives. |
| `canary.interval` | durée | `2m` | Durée de chaque étape. |
| `canary.analysis` | objet | seuils de `observability.alerts` | `errorRate`, `p95Latency` mesurés sur la version canari seulement. |
| `canary.onFailure` | enum | `rollback` | `rollback` : retour automatique. `pause` : gel, décision humaine. |
| `blueGreen.previewDuration` | durée | `10m` | Avec `approval: owner`, la bascule attend l'approbation au lieu du délai. |
| `approval` | enum | `none` | `owner` : la release attend `nlk releases approve` par un `owner` du projet. |
| `freeze` | []string | `[]` | Fenêtres pendant lesquelles les releases sont mises en file. Format `"<jour> <hh:mm> - <jour> <hh:mm> <fuseau>"`. |
| `previews.enabled` | bool | `false` | Voir ci-dessus. Uniquement sur un environnement avec `track` de branche. |
| `previews.ttl` | durée | `7d` | |
| `tagOnRelease` | bool | `false` | Pose un tag `nlk/<env>` sur le SHA source à chaque release live. Lecture seule, aucun commit, pas de boucle. |

### Comment une release naît

| Déclencheur | Commande | Ce qui se passe |
|---|---|---|
| **Push** sur la branche ou le tag suivi | aucune | `requireChecks` → build → release dans l'environnement qui `track` ce ref. C'est le défaut. |
| **Promotion** | `nlk promote staging prod` | Prend la release **live** de `staging` (digest + SHA du manifeste), la rend avec l'overlay `prod`. **Aucun build.** Ce qui a été testé est ce qui part. |
| **Manuel** | `nlk deploy --env prod --ref v1.4.2` | Build si nécessaire, release dans l'environnement indiqué. Échappatoire, même politique (`approval`, `freeze`) appliquée. |

Une promotion vers un environnement qui `track` un ref est autorisée mais sera remplacée
par le prochain push sur ce ref.

Une release exécute toujours **code + manifeste + overlay au même SHA**. Modifier
`environments.prod.services.web.scale` est un commit sur `main`, il produit une release
staging (sans effet là, l'overlay prod n'y est pas appliqué), puis il est promu. Ce qui est
en prod est exactement ce qui a été relu. Grâce à la règle 8, cette promotion n'a pas
reconstruit l'image.

## Référence des champs de la base

### `metadata`

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `name` | string DNS-1123 | oui | Nom de l'app, unique dans chaque projet cible. Préfixe des objets Kubernetes. |
| `project` | string DNS-1123 | sans `environments` | Projet cible. Interdit avec `environments`. |
| `labels` | map | non | Propagés sur tous les objets. Utilisables dans Grafana et la facture. |

### `spec.source`

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `git` | URL | — | Dépôt source. HTTPS ou SSH. Accès via deploy key créée par `nlk init`. |
| `ref` | string | `main` | **Sans `environments` uniquement** : branche ou glob de tags suivi. |
| `path` | string | `.` | Sous-dossier à builder. |
| `build.type` | enum | `buildpacks` | `buildpacks`, `dockerfile`, `image`. |
| `build.builder` | string | Paketo jammy-base | Builder CNB. |
| `build.dockerfile` | string | `./Dockerfile` | Si `type: dockerfile`. |
| `build.image` | string | — | Si `type: image` : dépôt d'image sans tag. Le tag ou digest vient du `track` (tags) ou de `nlk deploy --ref`. |
| `build.args` | map | — | Build args non secrets. |
| `build.ignore` | []glob | `[nolockin.yaml, environments/**]` | Exclus du contexte de build. Les valeurs par défaut sont toujours ajoutées. |

### `spec.services[]`

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `name` | string | — | Unique dans l'app. |
| `command` | []string | CMD de l'image | |
| `port` | int | détecté (`PORT`) | |
| `protocol` | enum | `http` | `http`, `grpc`, `tcp`. |
| `resources.cpu` | quantité | `250m` | **Requête** CPU. Limite = 2× la requête. |
| `resources.memory` | quantité | `256Mi` | Requête = limite. |
| `scale.min` / `scale.max` | int | `2` / `10` | `min: 0` active le scale-to-zero (v1.1). |
| `scale.targetCPU` | % | `70` | Exclusif avec `targetRPS`. |
| `scale.targetRPS` | int | — | Requêtes/s par pod (métrique Gateway). |
| `health.path` | string | `/` | Readiness et liveness. Pour `tcp` : check de connexion. |
| `routes[]` | liste | `<app>-<project>.nolockin.app` | `host`, `path` (`/`), `tls` (`auto` \| `secret:<nom>` \| `off`), `redirectWWW`, `rateLimit` (`100/s`). |
| `env` | map | — | Fusionné avec `spec.env` et l'overlay. |

### `spec.workers[]`

Comme un service, sans `port`, `health.path` ni `routes`. Scale sur `targetCPU` ou
`targetQueue: { addon, key, perPod }`.

### `spec.crons[]`

| Champ | Défaut | Description |
|---|---|---|
| `schedule` | — | Cron 5 champs. |
| `timezone` | `UTC` | IANA. |
| `command` | — | |
| `concurrency` | `forbid` | `forbid`, `allow`, `replace`. |
| `timeout` | `1h` | |
| `retries` | `2` | |

### `spec.addons[]`

| `type` | Champs | Opérateur | Clés `fromAddon` |
|---|---|---|---|
| `postgres` | `version` (14–17), `plan` (`single`/`ha`), `storage`, `backups { schedule, retention }`, `extensions` | CloudNativePG | `url`, `url_ro`, `host`, `port`, `user`, `password`, `database` |
| `redis` | `version`, `memory`, `persistence` | redis-operator | `url`, `host`, `port`, `password` |
| `bucket` | `versioning`, `quota`, `public` | MinIO | `bucket`, `endpoint`, `access_key`, `secret_key`, `region` |

Chaque add-on a une procédure d'export **à froid et à chaud** testée
([Protocole de sortie](../guides/sortie.md#export-des-add-ons)). Les add-ons sont **par
environnement** : `db` en staging et `db` en prod sont deux clusters Postgres distincts.

### `spec.env`

| Forme | Résolution |
|---|---|
| `"texte"` | Littéral. Jamais pour un secret. |
| `{ fromSecret, key }` | Secret du **projet de l'environnement**, créé par `nlk secret set <nom> <clé>=<valeur> --env prod`. Les secrets sont la place naturelle de ce qui diffère entre environnements et ne doit pas être dans Git. |
| `{ fromAddon, key }` | Credential de l'add-on de cet environnement. |
| `{ fromService, key: url }` | URL interne d'un autre service de l'app. |

### `spec.network`, `spec.observability`

Inchangés : `allowFrom`, `egress` ; `metrics.path`, `alerts { errorRate, p95Latency, notify }`,
`logs.retention`. Tous surchargeables par environnement.

## Zero-config

Un dépôt sans `nolockin.yaml` ne déploie rien : le fichier est un artefact de sortie, il
doit exister chez l'utilisateur. Mais il ne doit pas être écrit à la main :

- `nlk init` détecte le langage, le port, un `Procfile` ou `docker-compose.yml` existants, et génère un manifeste minimal avec un seul environnement.
- « Connecter un dépôt » dans la console ouvre une **PR** qui ajoute ce même fichier.
- `nlk init --environments staging,prod` génère la forme à deux environnements.

Le zero-config **génère** le fichier, il ne le remplace jamais.

## Validation

`nlk validate` vérifie :

- Le schéma JSON (`schemas/v1/app.json`).
- L'exclusivité `metadata.project` / `environments`, et `spec.source.ref` / `track`.
- L'unicité des noms de services/workers/crons/add-ons après fusion, pour chaque environnement.
- Qu'un environnement n'est défini qu'une fois (fichier principal ou `environments/<env>.yaml`).
- Que `previews` n'est activé que sur un environnement avec `track` de branche.
- Que chaque `fromAddon` référence un add-on présent (non `disabled`) dans l'environnement.
- Que chaque `fromSecret` existe dans le projet de l'environnement (avertissement).
- Que `routes[].host` custom est vérifié ou vérifiable, et unique entre environnements.
- Que le quota de chaque projet peut absorber `scale.max × resources`.
- Que `freeze` est parsable et que `canary.steps` finit par `100%`.

## Rendu Kubernetes

```bash
nlk render --env prod > k8s-prod.yaml
kubectl apply -f k8s-prod.yaml
```

Le rendu prend l'environnement demandé, applique la fusion, et écrit les objets standards.
Avec `strategy: canary` ou `blueGreen`, le Deployment devient un `Rollout` Argo Rollouts.
`nlk render` est déterministe à manifeste et digest donnés. La CI compare le rendu et les
objets réellement créés par l'opérateur.

## Migration de schéma

Un changement de `apiVersion` est accompagné de `nlk manifest migrate` et d'un support de
la version précédente pendant 18 mois minimum. Les champs supprimés passent d'abord par
`deprecated` avec avertissement.
