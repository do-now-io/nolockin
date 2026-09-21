# ADR-0005 · Licence Apache-2.0, sans exception

**Statut** : acceptée · 2026-09

## Contexte

Plusieurs projets d'infrastructure sont passés d'une licence open source à une licence
« source available » (BSL, SSPL, Elastic License) pour empêcher les clouds de les
héberger. C'est précisément une forme de lock-in : l'utilisateur ne peut plus faire
héberger le produit par qui il veut.

## Décision

Tout le code de NoLockIn (control plane, opérateur, CLI, chart, metering, billing,
console, dashboards) est sous **Apache-2.0**. Pas d'édition entreprise, pas de module
sous autre licence, pas de CLA qui permettrait un changement de licence unilatéral :
les contributions restent sous Apache-2.0 via DCO.

## Raisons

- La promesse « pas de lock-in » inclut le droit de faire héberger NoLockIn par un tiers, concurrent compris.
- Le modèle économique repose sur l'hébergement et le support, pas sur l'exclusivité du code.
- Un DCO plutôt qu'un CLA rend un changement de licence pratiquement impossible sans l'accord de tous les contributeurs. C'est voulu.

## Conséquences

- Un hébergeur peut proposer « NoLockIn hébergé » sans nous payer. On l'accepte : ça agrandit le marché de la sortie, et notre avantage est l'exécution et le support.
- Les dépendances doivent être compatibles (Apache-2.0, MIT, BSD, MPL-2.0). Pas de dépendance AGPL ou BSL dans le chemin critique. Les composants sous AGPL (Grafana, Loki, MinIO) sont **utilisés tels quels**, non modifiés, non liés : ils restent sous leur licence et sont remplaçables (Grafana par Perses, MinIO par SeaweedFS ou Ceph RGW).

## Alternatives écartées

- **AGPL** : protège contre le SaaS-washing, mais fait peur aux DSI et compliquerait l'adoption self-hosted.
- **BSL avec conversion après 4 ans** : c'est la définition du lock-in temporel.
