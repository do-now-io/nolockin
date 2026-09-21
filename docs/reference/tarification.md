# 05 · Tarification et metering

## Principe

**On facture ce qui est consommé, mesuré à la seconde, avec des requêtes PromQL
publiques.** La facture et le dashboard Grafana « Facture » lisent les mêmes séries. La
grille de prix est un fichier YAML versionné. Il n'y a pas de plan.

## Grille (cloud hébergé, région fr-par, tarifs indicatifs de lancement)

```yaml
# pricing/fr-par.yaml   (Scaleway Kapsule, Paris)
version: 2026-09
currency: EUR
units:
  cpu:      { unit: vcpu-hour,  price: 0.018 }   # facturé à la seconde consommée
  memory:   { unit: gib-hour,   price: 0.0045 }  # working set, à la seconde
  storage:  { unit: gib-month,  price: 0.09 }    # PVC + snapshots + logs Loki
  egress:   { unit: gib,        price: 0.02 }    # Internet sortant, 100 GiB/mois offerts
  build:    { unit: build-minute, price: 0.004 } # minutes de build, 300/mois offertes
  lb:       { unit: ip-hour,    price: 0.006 }   # une IP publique par projet, la première offerte
free:
  egress_gib_per_month: 100
  build_minutes_per_month: 300
  public_ips: 1
exempt:
  - egress-class=export        # sortie : 0 €
  - namespace=nolockin-*       # le control plane n'est pas facturé au client
```

### Exemples

| Charge | Calcul | Mois (730 h) |
|---|---|---|
| API 2 pods, 0,25 vCPU et 300 MiB moyens chacun | 2 × (0,25 × 0,018 + 0,29 × 0,0045) × 730 | **≈ 8,50 €** |
| + Postgres HA 3 × 0,5 vCPU / 1 GiB, 20 GiB | 3 × (0,5 × 0,018 + 1 × 0,0045) × 730 + 60 × 0,09 | **≈ 34,80 €** |
| + Worker 1 pod 0,1 vCPU / 200 MiB | (0,1 × 0,018 + 0,2 × 0,0045) × 730 | **≈ 1,97 €** |
| + 50 GiB egress, 120 min de build | 0 (sous les seuils offerts) | **0 €** |
| **Total** | | **≈ 45 €/mois** |

Sur votre cluster : **0 €** de licence. Le metering tourne en mode `showback` et affiche
ces mêmes chiffres par équipe, avec la grille de votre choix (coût interne du cluster).

## Ce qui est mesuré et comment

Toutes les recording rules sont dans `charts/nolockin/rules/metering.yaml`. Elles
s'évaluent à la minute et s'agrègent par `namespace` (= projet), `app`, `service` et
labels utilisateur.

| Ressource | Série source | Recording rule (nom) | Note |
|---|---|---|---|
| CPU | `container_cpu_usage_seconds_total` | `nlk:cpu_seconds:rate1m` | Usage réel, **pas la requête**. Un pod qui dort ne coûte presque rien. |
| Mémoire | `container_memory_working_set_bytes` | `nlk:memory_gib_seconds:sum1m` | Working set, c'est ce que le kernel ne peut pas reprendre. |
| Stockage | `kubelet_volume_stats_capacity_bytes` + snapshots CNPG + `loki_ingester_*` | `nlk:storage_gib:avg1m` | Provisionné (un PVC de 20 GiB coûte 20 GiB, même vide). |
| Egress | Envoy `envoy_cluster_upstream_cx_tx_bytes_total` (côté Gateway) + Cilium/eBPF egress par pod | `nlk:egress_bytes:increase1m` | Trafic intra-cluster et export exclus. |
| Build | `kpack_build_duration_seconds` | `nlk:build_minutes:sum` | |
| IP publique | `nlk_gateway_public_ips` | | |

`nlk-meter` lit ces séries chaque minute, écrit une ligne `usage_records(ts, project,
app, service, labels, resource, quantity)` dans sa base (Postgres via CNPG), et
`nlk-billing` fait la somme mensuelle × grille. La base est exportable
(`nlk usage export --format parquet`), et le bundle de sortie l'inclut.

## Vérifier sa facture

```bash
nlk usage --month 2026-09 --by service
nlk usage explain
```

`explain` affiche, pour chaque ligne, la requête PromQL exacte et un lien Grafana vers la
série. Le dashboard « Facture » (provisionné pour chaque projet) affiche en temps réel :
consommation du mois en cours, projection à fin de mois, répartition par app et par
label (ex. `team`), historique 12 mois, et le prix unitaire appliqué.

Si le dashboard et la facture divergent, la facture a tort : elle est recalculée à partir
des séries, et l'écart est documenté publiquement dans le changelog du metering.

## Arrondis et granularité

- Mesure à la seconde, agrégation à la minute, facturation au mois calendaire (UTC).
- Prix appliqué avec 6 décimales, total arrondi au centime.
- Pas de minimum de facturation par ressource ni par mois. Un projet vide coûte 0 €.
- Pas de facturation pendant les incidents déclarés (statut « major outage » sur la page de statut) pour les projets impactés.

## Changements de prix

- Grille versionnée dans le dépôt, un tag par version.
- Toute hausse : préavis 90 jours par e-mail et bannière dans la console, application au 1er du mois suivant le préavis.
- Toute baisse : immédiate.
- Jamais rétroactif.

## Mode `showback` (self-hosted)

```yaml
billing:
  mode: showback
  pricing: ./pricing/internal.yaml    # votre grille : coût réel de vos nœuds
```

Même pipeline, même dashboard, aucune facture émise. Sert au chargeback interne par
équipe via les labels du manifeste. `mode: off` désactive le metering pour économiser
~0,3 vCPU.

## Ce qu'on ne facture pas

- Le control plane, l'observabilité, ArgoCD, Grafana, Loki, les dashboards.
- Les utilisateurs / sièges / membres.
- Les domaines custom, les certificats TLS.
- Les requêtes HTTP (pas de prix « par million de requêtes »).
- L'export, la sortie, l'egress de sortie.
- Le support communautaire.

## Support payant (optionnel, hébergé ou self-hosted)

| Offre | Contenu | Prix indicatif |
|---|---|---|
| **Community** | GitHub Discussions, Discord | 0 € |
| **Business** | Support e-mail 8×5, réponse < 4 h, aide à la migration incluse | 490 €/mois |
| **Enterprise** | 24×7, SLA 99,9 % sur le control plane self-hosted, astreinte, revue d'architecture | Sur devis |

Aucune offre de support ne débloque une fonctionnalité. Elles achètent du temps humain.
