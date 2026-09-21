# ADR-0001 · Kubernetes est le substrat unique

**Statut** : acceptée · 2026-09

## Contexte

Un PaaS doit tourner quelque part. Les options : orchestrateur maison (Heroku, Fly),
Nomad, Docker Swarm, Kubernetes, ou une abstraction multi-substrat.

## Décision

NoLockIn s'installe **uniquement** sur un cluster Kubernetes conforme (≥ 1.29) et ne
propose pas d'autre cible. Il n'installe pas le cluster.

## Raisons

- La promesse de sortie repose sur un substrat que le client peut obtenir partout : chez tous les clouds, chez tous les hébergeurs européens, sur du bare metal (k3s, Talos), sur un laptop (kind).
- Tous les composants choisis (ArgoCD, CNPG, Gateway API, cert-manager, Prometheus) sont natifs Kubernetes. Une abstraction multi-substrat obligerait à réécrire ou dégrader chacun.
- `nlk render` vers du Kubernetes standard est la sortie de niveau 2. Sans Kubernetes comme cible unique, ce rendu n'aurait pas de sens.

## Conséquences

- Un utilisateur qui veut faire du self-hosted doit avoir ou louer un cluster Kubernetes. C'est accepté : les Kubernetes managés coûtent aujourd'hui entre 0 et 70 €/mois de control plane.
- On dépend des évolutions de Gateway API et des opérateurs tiers. On fige des versions et on teste les montées.
- Pas de support Docker Compose ou Swarm, même pour le développement local : `nlk dev` utilisera kind.

## Alternatives écartées

- **Nomad** : plus simple, mais l'écosystème d'opérateurs (bases HA, GitOps) est trop mince pour tenir la promesse « tout fonctionne tout de suite ».
- **Orchestrateur maison** : c'est exactement ce qui crée du lock-in.
