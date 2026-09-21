# Chart `nolockin`

Chart Helm umbrella qui installe l'intégralité du control plane NoLockIn sur un cluster
Kubernetes existant. C'est **la même installation** que celle du cloud hébergé, seul
`billing.mode` change.

## État

Scaffold au jalon M0 : `Chart.yaml` et `values.yaml` reflètent la spécification
([docs/architecture/vue-d-ensemble.md](../../docs/architecture/vue-d-ensemble.md)). Les templates, CRDs,
dashboards et recording rules arrivent au jalon M1 ([roadmap](../../docs/projet/roadmap.md)).

## Installation cible

```bash
helm install nolockin oci://ghcr.io/nolockin/charts/nolockin \
  -n nolockin-system --create-namespace \
  --set global.domain=nlk.infra.acme.internal \
  --set billing.mode=showback \
  --set auth.oidc.issuer=https://sso.acme.com

helm test nolockin -n nolockin-system
```

## Arborescence prévue

```
charts/nolockin/
├── Chart.yaml
├── values.yaml
├── crds/               App, Addon, Domain (nolockin.io/v1)
├── templates/          nlk-api, nlk-operator, nlk-meter, nlk-billing, manifest store, RBAC, Gateway
├── dashboards/         JSON Grafana provisionnés (App, Projet, Add-ons, Facture)
├── rules/metering.yaml recording rules Prometheus publiques du metering
├── rules/alerts.yaml   alertes par défaut
└── tests/              helm test : API joignable, ArgoCD synced, Grafana provisionné
```
