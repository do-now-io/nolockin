# ADR-0004 · Le metering lit Prometheus, la facture lit le metering

**Statut** : acceptée · 2026-09

## Contexte

Un PaaS peut mesurer la consommation avec un agent propriétaire, via l'API cloud
sous-jacente, ou via les métriques Kubernetes déjà collectées.

## Décision

Le metering est un ensemble de **recording rules Prometheus publiques** agrégées par
`nlk-meter` en enregistrements d'usage, puis valorisées par `nlk-billing` selon une grille
YAML versionnée. Le dashboard Grafana « Facture » lit les mêmes séries.

## Raisons

- Vérifiabilité : l'utilisateur peut recalculer sa facture avec `nlk usage explain` et Grafana.
- Aucun agent à ajouter dans les conteneurs.
- Le même pipeline fonctionne en self-hosted en mode `showback`, ce qui en fait une fonctionnalité et pas seulement un mécanisme de facturation.

## Conséquences

- La précision dépend de Prometheus : scrape à 15 s, agrégation à la minute. Une rafale CPU de 3 s est moyennée. Accepté et documenté.
- Si Prometheus est indisponible, on perd des points de mesure. Règle : les trous sont **en faveur du client** (non facturés), jamais interpolés.
- Il faut deux réplicas Prometheus et un `nlk-meter` idempotent (dédoublonnage par fenêtre).

## Alternatives écartées

- **API de facturation du cloud sous-jacent** : opaque, non reproductible en self-hosted.
- **OpenCost** : très proche et envisagé comme brique. Écarté en v1 parce qu'il alloue les coûts de nœud (modèle « coût du cluster ») alors qu'on facture l'usage à des prix unitaires. Il pourrait alimenter le mode `showback` en v1.1.
