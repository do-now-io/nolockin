# 04 · Protocole de sortie

La sortie est la fonctionnalité qui définit le produit. Ce document décrit les trois
niveaux de sortie, le format d'export, la procédure de migration à chaud, et les garanties
contractuelles et techniques qui l'entourent.

## Trois niveaux de sortie

| Niveau | Vous quittez… | Vous gardez… | Effort |
|---|---|---|---|
| **1 · Changer de cluster** | Le cloud NoLockIn | NoLockIn (self-hosted), la CLI, le manifeste, les dashboards, l'expérience dev | 4 commandes, un après-midi |
| **2 · Quitter NoLockIn** | La plateforme NoLockIn | Kubernetes standard : `nlk render` produit le YAML, vos images OCI, vos dumps | Un sprint |
| **3 · Quitter Kubernetes** | Kubernetes | Vos images OCI (tournent sous Docker, Nomad, ECS), vos dumps Postgres, vos objets S3 | Selon la cible |

La sortie se fait **par projet**, donc par environnement : on migre `acme-staging` un
mardi, `acme-prod` le vendredi suivant, avec le même manifeste. Le bundle emporte les
releases, les approbations et les promotions du manifest store.

Le niveau 1 est le cas nominal et le seul qui soit orchestré. Les niveaux 2 et 3 sont
garantis par le choix de formats standards à chaque couche ([Architecture](../architecture/vue-d-ensemble.md#composants)).

## Niveau 1 · Migration vers votre cluster

### Prérequis côté cible

- Un cluster Kubernetes ≥ 1.29, 3 nœuds recommandés, une StorageClass par défaut, un LoadBalancer (cloud ou MetalLB).
- Un domaine wildcard pour les sous-domaines fournis (optionnel si vous n'utilisez que vos domaines).
- Un IdP OIDC (Google Workspace, Entra, Keycloak…) ou l'IdP Dex local du chart.

### Étape 1 · Installer la plateforme

```bash
helm install nolockin oci://ghcr.io/nolockin/charts/nolockin \
  -n nolockin-system --create-namespace \
  --set global.domain=nlk.infra.acme.internal \
  --set billing.mode=showback \
  --set auth.oidc.issuer=https://sso.acme.com
```

Durée : 5 à 8 minutes. À la fin : `nlk-api`, ArgoCD, Grafana, Loki, Prometheus, CNPG,
Envoy Gateway, cert-manager sont en place. `helm test nolockin` valide l'installation.

### Étape 2 · Ajouter le contexte

```bash
nlk context add mon-cluster --server https://api.nlk.infra.acme.internal
nlk login --context mon-cluster
```

### Étape 3 · Exporter

```bash
nlk export --project acme --to-context mon-cluster > acme.nlkbundle
```

`--to-context` récupère la clé publique du cluster cible pour chiffrer les secrets. Sans ce
flag, les secrets sont chiffrés avec une clé `age` que vous fournissez (`--recipient`).

L'export est **streamé**, jamais limité en débit, et **l'egress correspondant est facturé
0 €** (le trafic est étiqueté `nolockin.io/egress-class=export` et exclu du metering).

### Étape 4 · Importer

```bash
nlk import acme.nlkbundle --context mon-cluster --dry-run   # affiche ce qui sera créé
nlk import acme.nlkbundle --context mon-cluster
```

L'import :

1. Crée le projet, le namespace, le quota, les membres.
2. Copie les images vers la registry cible (`crane copy`, digest vérifié).
3. Déchiffre et crée les secrets.
4. Restaure les add-ons depuis les snapshots du bundle **puis** établit la réplication continue depuis la source (voir ci-dessous).
5. Applique les manifestes. Les apps démarrent sur le cluster cible avec les routes en mode `shadow` (pas exposées publiquement, mais joignables par un hostname de test).

### Étape 5 · Planifier et basculer

```bash
nlk exit plan --project acme --to mon-cluster
```

Le plan affiche pour chaque app et add-on : l'état de la réplication (lag), les enregistrements DNS à modifier, les TTL actuels, la coupure estimée par service, et l'ordre de bascule.

```bash
nlk exit cutover --project acme --to mon-cluster
```

Séquence orchestrée :

| # | Action | Coupure |
|---|---|---|
| 1 | Vérifie que la cible est `Ready` et que le lag de réplication < 1 s | 0 |
| 2 | Abaisse les TTL DNS à 60 s (si le DNS est géré par NoLockIn) ou attend confirmation manuelle | 0 |
| 3 | Passe les workers et crons de la source en `paused` | 0 (les files s'accumulent) |
| 4 | Met la source en lecture seule au niveau Postgres (`default_transaction_read_only`) | Écritures refusées ~5 s |
| 5 | Attend le drain de la réplication, promeut la cible en primary | |
| 6 | Bascule les routes : la source répond par un `307` vers la cible pendant la propagation DNS, les routes cibles passent de `shadow` à `live` | 0 pour les clients qui suivent la redirection |
| 7 | Met à jour le DNS (ou affiche les changements à faire) | |
| 8 | Reprend workers et crons **sur la cible** | |
| 9 | Coupe la réplication, la source devient une copie figée conservée 30 jours | |

Coupure typique mesurée en CI : **4 à 8 secondes d'écritures refusées**, zéro erreur de
lecture.

### Étape 6 · Vérifier et fermer

```bash
nlk exit verify --project acme --to mon-cluster
```

Compare source et cible : nombre de lignes par table (échantillonné), objets S3 (count +
checksum), réponse des health checks, certificats valides, alertes silencieuses.

```bash
nlk project delete acme --context hosted --certificate
```

Supprime le projet sur le cloud hébergé après un délai de grâce de 30 jours (annulable),
puis émet une **attestation de suppression** signée (JSON + PDF) listant les ressources
détruites, les snapshots effacés et la date.

## Format du bundle `.nlkbundle`

Un bundle est une archive tar+zstd, signée (cosign), avec la structure :

```
acme.nlkbundle
├── manifest.json            version du format, contexte source, date, checksums
├── project.yaml             projet, quota, membres, labels
├── apps/
│   ├── shop-api/nolockin.yaml
│   └── shop-api/releases.json      historique (SHA, digest, auteur, date)
├── images.json              liste digest → nom, pour crane copy
├── secrets/
│   └── shop-api.age         secrets chiffrés (age, destinataire = clé cible)
├── addons/
│   ├── db/snapshot.pgbase   base backup CNPG + WAL jusqu'au moment de l'export
│   ├── db/replication.json  slot, publication, credentials temporaires
│   ├── cache/dump.rdb
│   └── uploads/manifest.jsonl     liste des objets (la copie se fait en streaming S3→S3)
├── dns/plan.json            enregistrements à modifier, TTL actuels
├── observability/
│   ├── dashboards/*.json    dashboards Grafana custom de l'utilisateur
│   └── alerts.yaml          règles d'alerte custom
└── usage/2026-*.parquet     historique d'usage et factures (pour continuité comptable)
```

`nlk export --include-addons=false` produit un bundle léger (manifestes + secrets +
images) ; les add-ons sont alors migrés par réplication seule.

## Export des add-ons

Chaque type d'add-on a une procédure d'export **à froid** (snapshot) et **à chaud**
(réplication continue), toutes deux testées en CI.

| Add-on | À froid | À chaud | Outil |
|---|---|---|---|
| `postgres` | Base backup CNPG + WAL (PITR) | Réplication logique (publication/subscription), lag surveillé | CloudNativePG, `pg_dump` en secours |
| `redis` | RDB | `REPLICAOF` vers la cible, puis `REPLICAOF NO ONE` à la bascule | redis-operator |
| `bucket` | Listing + copie | `mc mirror --watch` source→cible jusqu'à la bascule | MinIO client |

## Niveau 2 · Quitter NoLockIn pour du Kubernetes nu

```bash
nlk render --project acme > acme-k8s.yaml
```

Le rendu contient les Namespaces, Deployments, Services, HTTPRoutes, HPA, PDB, CronJobs,
NetworkPolicies, PVC, `Cluster` CNPG, ressources Redis et MinIO. Il suppose la présence
de Gateway API, cert-manager, CNPG, redis-operator et MinIO operator, tous installables
indépendamment de NoLockIn. La CI vérifie que ce rendu appliqué sur un cluster `kind` nu
(avec ces opérateurs) produit une app fonctionnelle.

Ce qui n'est pas dans le rendu : le build (remplacé par vos propres images), les
dashboards provisionnés (exportés en JSON dans le bundle), le metering.

## Niveau 3 · Quitter Kubernetes

Vous avez : des images OCI (`docker run` fonctionne), des dumps Postgres standards, des
objets S3, un `nolockin.yaml` lisible qui documente commandes, ports, variables et
dépendances. Aucun format NoLockIn n'est nécessaire pour redémarrer ailleurs.

## Garanties

### Techniques (dans le code)

- `nlk export` et `nlk addon export` sont servis par un chemin d'API **sans vérification d'état de compte**. Un compte suspendu pour impayé peut exporter. Testé.
- Aucun rate limit sur les endpoints d'export.
- Le trafic d'export est exclu du metering egress (label `egress-class=export`).
- Le protocole complet (installer B, exporter A, importer B, basculer, vérifier) est un job CI bloquant sur chaque release, exécuté sur deux clusters `kind`.
- Le bundle est signé ; `nlk import` refuse un bundle dont la signature ne correspond pas.

### Contractuelles (dans les CGU du cloud hébergé)

- Rétention des données 30 jours après suppression, exportables pendant toute cette période.
- Aucun frais de sortie, aucun frais d'egress sur l'export.
- Préavis de 12 mois minimum avant tout arrêt de service hébergé, avec assistance à la migration incluse.
- Le prix unitaire ne peut augmenter qu'avec 90 jours de préavis, et jamais rétroactivement.

## Retour arrière

`nlk exit cutover` conserve la source intacte (lecture seule) 30 jours. Si la cible
défaille après bascule :

```bash
nlk exit rollback --project acme --to hosted
```

Inverse la réplication (cible → source), rétablit les écritures sur la source, rebascule
les routes. Coupure équivalente à la bascule aller. Après 30 jours ou `project delete`, le
retour arrière n'est plus possible.

## Ce que la sortie ne fait pas

- Elle ne migre pas les enregistrements DNS chez un registrar externe : elle affiche le plan et attend.
- Elle ne migre pas les données d'un service tiers (Stripe, Auth0…). Les secrets, oui.
- Elle ne réécrit pas le code de l'app. Si le code dépend d'une URL `*.nolockin.app`, la redirection 307 couvre la transition, mais le code doit être mis à jour.
