# Add-ons

Un add-on est une dépendance managée déclarée dans le manifeste et opérée par un opérateur
open source : Postgres par CloudNativePG, Redis par redis-operator, stockage objet par MinIO.
Chaque add-on est **par environnement**, sauvegardé, et exportable à froid comme à chaud.

## Types disponibles

| `type` | Opérateur | Ce que vous obtenez | Clés exposées via `fromAddon` |
|---|---|---|---|
| `postgres` | CloudNativePG | Postgres 14 à 17, plan `single` ou `ha` (1 primary + 2 replicas synchrones), sauvegardes continues, restauration à un instant donné, extensions | `url`, `url_ro`, `host`, `port`, `user`, `password`, `database` |
| `redis` | redis-operator | Redis 7, persistance optionnelle, métriques | `url`, `host`, `port`, `password` |
| `bucket` | MinIO | Un bucket S3-compatible, versioning, quota, accès public optionnel | `bucket`, `endpoint`, `access_key`, `secret_key`, `region` |

Un type d'add-on n'entre dans NoLockIn que s'il a une procédure d'export à froid et à chaud
testée en CI. C'est le [principe 7](../projet/vision.md#principes-de-conception).

## Déclarer et utiliser

```yaml
spec:
  addons:
    - name: db
      type: postgres
      version: "16"
      extensions: [pgvector, pg_trgm]
    - name: cache
      type: redis
    - name: uploads
      type: bucket
  env:
    DATABASE_URL:    { fromAddon: db, key: url }
    DATABASE_RO_URL: { fromAddon: db, key: url_ro }     # replicas, plan ha
    REDIS_URL:       { fromAddon: cache, key: url }
    S3_BUCKET:       { fromAddon: uploads, key: bucket }
    S3_ENDPOINT:     { fromAddon: uploads, key: endpoint }
    S3_ACCESS_KEY:   { fromAddon: uploads, key: access_key }
    S3_SECRET_KEY:   { fromAddon: uploads, key: secret_key }
```

Les identifiants sont générés par l'opérateur, injectés au démarrage, tournés par
`nlk addon rotate db`. Ils ne passent jamais par Git ni par vos mains.

## Dimensionner par environnement

```yaml
environments:
  staging:
    addons:
      db: { plan: single, storage: 5Gi }
      cache: { memory: 128Mi }
  prod:
    addons:
      db:
        plan: ha
        storage: 50Gi
        backups: { schedule: "0 */6 * * *", retention: 30d }
      cache: { memory: 512Mi, persistence: true }
      uploads: { versioning: true }
```

Le stockage est facturé au GiB provisionné : un volume de 50 GiB coûte 50 GiB même vide.
Agrandir un volume se fait en changeant `storage` ; réduire demande une restauration.

## Se connecter

```bash
nlk addon psql db --env prod            # session psql avec les bons identifiants
nlk addon redis-cli cache --env staging
nlk addon info uploads --env prod       # endpoint, bucket, politique
```

## Sauvegardes et restauration

Postgres est sauvegardé en continu (WAL vers le stockage objet) plus un snapshot selon
`backups.schedule`. La restauration à un instant donné couvre les 7 derniers jours par défaut.

```bash
nlk addon backup db --env prod                             # snapshot à la demande
nlk addon backups db --env prod                            # liste, fenêtre PITR
nlk addon restore db --at "2026-09-08T14:00:00Z" --env prod
```

`restore` crée un nouveau cluster à côté de l'ancien, bascule les identifiants au moment
que vous choisissez, et conserve l'ancien 7 jours. Rien n'est écrasé.

## Rafraîchir le staging depuis la production

```bash
nlk addon copy db --from prod --to staging
```

Restaure le dernier snapshot de production dans l'add-on de staging. Réservé aux owners des
deux projets, journalisé. Pensez à anonymiser si vos données l'exigent : la commande accepte
`--post-script ./anonymize.sql`.

## Exporter

```bash
nlk addon export db --env prod > db.dump          # pg_dump format custom, jamais bridé
nlk addon export uploads --env prod --to s3://mon-bucket-ailleurs/
```

Au moment de quitter, le [protocole de sortie](sortie.md) fait mieux qu'un export : il
établit une réplication continue vers votre cluster (réplication logique Postgres,
`REPLICAOF` Redis, miroir S3) et bascule avec quelques secondes d'écritures refusées.

## Ce que les add-ons ne couvrent pas

Un service SaaS externe (Stripe, un Postgres chez un autre fournisseur) n'est pas un add-on :
mettez son URL dans un [secret](secrets.md). Un besoin d'un autre moteur (MySQL, MongoDB,
Kafka) se traite aujourd'hui en déployant l'opérateur correspondant comme une app à vous ;
d'autres types d'add-ons arriveront avec leur procédure d'export.
