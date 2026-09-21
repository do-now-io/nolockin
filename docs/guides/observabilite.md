# 06 · Observabilité livrée par défaut

Un `nlk deploy` réussi produit, sans configuration, un dashboard Grafana, des logs
interrogeables, une vue ArgoCD et quatre alertes. L'objectif : que l'utilisateur voie
**tous ses conteneurs et tout ce qui les entoure** dès la première minute.

## Ce qui est provisionné automatiquement

| Élément | Par | Contenu |
|---|---|---|
| Dashboard « App » | app | Un par app : RPS, p50/p95/p99, taux d'erreur, réplicas vs HPA, CPU/mémoire par pod, redémarrages, déploiements annotés. |
| Dashboard « Projet » | projet | Vue agrégée de toutes les apps, add-ons, quota consommé vs quota alloué. |
| Dashboard « Add-on Postgres » | add-on | Connexions, TPS, cache hit ratio, lag de réplication, taille, backups, WAL. |
| Dashboard « Add-on Redis » | add-on | Ops/s, mémoire, hit ratio, clients, évictions. |
| Dashboard « Facture » | projet | [Voir 05](../reference/tarification.md#vérifier-sa-facture). |
| Explore Logs | projet | Loki, filtré sur le namespace du projet. Requête pré-remplie par service. |
| Application ArgoCD | projet | Arbre complet : App CR → Deployments → ReplicaSets → Pods, Services, HTTPRoutes, add-ons. Sync et health status. Lecture seule pour les rôles `developer` et `viewer`. |
| Alertes | app | Taux d'erreur, p95, pods en CrashLoop, add-on Postgres indisponible. Routage vers l'e-mail du projet par défaut. |

Tous les dashboards sont des fichiers JSON dans `charts/nolockin/dashboards/`, versionnés
et exportables. Les dashboards custom créés dans Grafana sont inclus dans le bundle de sortie.

## Accès

- `nlk open grafana` : SSO via Dex, l'utilisateur arrive sur le dashboard de l'app courante. Rôle Grafana `Viewer` par défaut, `Editor` pour les `owner` du projet, sur un dossier par projet.
- `nlk open argocd` : SSO, l'Application du projet. Le rôle `owner` peut déclencher un `sync` manuel ou un `rollback` ; les autres lisent.
- Console web : intègre Grafana (panels embarqués) et l'arbre ArgoCD (API) dans la page de l'app, pour ne pas obliger à changer d'outil.

## Métriques

| Source | Comment | Coût pour l'utilisateur |
|---|---|---|
| Ressources conteneurs | cAdvisor via kubelet | 0, toujours actif |
| HTTP (RPS, latence, codes) | Envoy Gateway, par route | 0, toujours actif |
| Applicatives | `spec.observability.metrics.path` → ServiceMonitor | Cardinalité limitée à 10 000 séries par app (alerte avant blocage) |
| Add-ons | Exporters des opérateurs (CNPG, redis-exporter, MinIO) | 0 |

Rétention Prometheus : 15 jours en local, remote write configurable (Mimir, Thanos, un
Grafana Cloud à vous) en self-hosted.

## Logs

- Collecte : Grafana Alloy en DaemonSet, stdout/stderr de tous les pods du projet.
- Labels : `namespace`, `app`, `service`, `pod`, `release`.
- Parsing : JSON détecté automatiquement, champs `level` et `msg` extraits.
- Rétention par défaut 7 jours, configurable par projet (`spec.observability.logs.retention`), facturée en stockage.
- `nlk logs -f` streame via l'API Loki tail. `nlk logs --grep` compile en LogQL.

## Traces (optionnel)

Tempo activable par projet (`--set tracing.enabled=true`). Les apps envoient en OTLP vers
`otel-collector.nolockin-observability:4317`, variable `OTEL_EXPORTER_OTLP_ENDPOINT`
injectée automatiquement. Propagation des traces Gateway → app via Envoy.

## Alertes par défaut

| Alerte | Condition | Sévérité |
|---|---|---|
| `AppHighErrorRate` | 5xx / total > `alerts.errorRate` sur 5 min | warning, critical si > 2× le seuil |
| `AppHighLatency` | p95 > `alerts.p95Latency` sur 5 min | warning |
| `AppCrashLooping` | > 3 redémarrages en 10 min | critical |
| `AppScaledToMax` | réplicas = `scale.max` pendant 15 min | info |
| `AddonPostgresDown` | primary indisponible > 1 min | critical |
| `AddonPostgresReplicationLag` | lag > 30 s | warning |
| `AddonDiskAlmostFull` | > 85 % | warning, critical > 95 % |
| `ProjectQuotaNearLimit` | > 90 % du quota CPU ou mémoire | warning |
| `BillingProjectionSpike` | projection fin de mois > 150 % du mois précédent | info (hébergé) |

Routage : `spec.observability.alerts.notify`. Récepteurs supportés : e-mail, Slack,
webhook, PagerDuty, Opsgenie. Les alertes du control plane lui-même vont à l'opérateur de
la plateforme, pas aux utilisateurs.

## ArgoCD : ce que l'utilisateur voit

Un projet = un `AppProject` ArgoCD restreint à son namespace. Chaque app du manifeste =
une `Application` ArgoCD pointant sur le chemin du projet dans le manifest store. L'arbre
montre :

```
Application acme-prod/shop-api   ✔ Synced   ♥ Healthy   release prod/#42
├── App (nolockin.io) shop-api
├── Rollout shop-api-web          3/3   canary 100 % · analyse ok
│   └── ReplicaSet shop-api-web-7d9f   3 pods
│       ├── Pod shop-api-web-7d9f-x2k   Running
│       ├── Pod shop-api-web-7d9f-m8q   Running
│       └── Pod shop-api-web-7d9f-4hv   Running
├── Deployment shop-api-queue     1/1
├── CronJob shop-api-cleanup
├── Service shop-api-web
├── HTTPRoute api.acme.com
├── Certificate api.acme.com      Ready
├── HorizontalPodAutoscaler shop-api-web   2 → 10
├── Cluster (CNPG) shop-api-db    3 instances, primary shop-api-db-1
└── Redis shop-api-cache
```

L'historique ArgoCD correspond à `nlk releases`. Un `nlk rollback` est un nouveau commit
dans le manifest store, donc une nouvelle entrée dans l'historique ArgoCD.

## Ce qui n'est pas activé par défaut

- Profiling continu (Pyroscope) : activable par projet.
- Synthetic monitoring externe : recommandé mais hors périmètre (Uptime Kuma s'installe comme une app).
- Rétention métriques longue durée : à brancher via remote write.
