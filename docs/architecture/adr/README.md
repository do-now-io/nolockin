# Architecture Decision Records

| ADR | Décision | Statut |
|---|---|---|
| [0001](0001-kubernetes-only.md) | Kubernetes est le substrat unique | Acceptée |
| [0002](0002-manifest-maps-to-plain-kubernetes.md) | Le manifeste se rend en Kubernetes standard, sans intermédiaire opaque | Acceptée |
| [0003](0003-argocd-plus-operator.md) | ArgoCD réconcilie, un opérateur rend : pas l'un sans l'autre | Acceptée |
| [0004](0004-metering-from-prometheus.md) | Le metering lit Prometheus, la facture lit le metering | Acceptée |
| [0005](0005-apache-2-license.md) | Licence Apache-2.0, sans exception | Acceptée |
| [0006](0006-exit-is-a-ci-gate.md) | Le protocole de sortie est un test bloquant de la CI | Acceptée |
| [0007](0007-policy-in-repo-state-in-store.md) | Push-to-deploy par défaut ; la politique dans le dépôt source, l'état (releases) dans le manifest store ; un fichier, des overlays ; promotion explicite sans build | Acceptée |
