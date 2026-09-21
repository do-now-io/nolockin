# ADR-0002 · Le manifeste se rend en Kubernetes standard

**Statut** : acceptée · 2026-09

## Contexte

Un manifeste de PaaS peut être un langage propre interprété par un moteur opaque, ou une
couche de sucre au-dessus d'objets standards.

## Décision

Chaque champ de `nolockin.yaml` correspond à des objets Kubernetes standards ou à des CRD
d'opérateurs open source tiers (CNPG, redis-operator, MinIO, Gateway API, cert-manager).
`nlk render` produit exactement ce que l'opérateur applique. La CI compare les deux.

## Raisons

- C'est la sortie de niveau 2 : sans NoLockIn, `kubectl apply` du rendu fonctionne.
- Un utilisateur avancé peut lire le rendu pour comprendre ce qui tourne, sans documentation NoLockIn.
- Cela interdit structurellement d'ajouter une fonctionnalité qui n'aurait pas d'équivalent standard.

## Conséquences

- Certaines commodités sont impossibles ou plus lentes à livrer (exemple : un « add-on » qui serait un service SaaS externe sans équivalent Kubernetes).
- Le manifeste expose des concepts Kubernetes (quantités `500m`, `512Mi`) plutôt que des « tailles » abstraites. On l'assume : ce sont les unités qui apparaissent sur la facture et dans Grafana.
- Le rendu doit rester déterministe : pas de valeur générée aléatoirement au rendu (les mots de passe d'add-ons sont générés par les opérateurs, pas par le rendu).

## Alternatives écartées

- **Manifeste abstrait (« small/medium/large »)** : plus accueillant, mais chaque abstraction est une opinion à maintenir et une opacité de plus sur la facture.
- **Helm chart généré par app** : plus standard encore, mais Helm ajoute une couche de templating que l'opérateur devrait gérer. Le rendu YAML plat est plus simple à lire et à diff.
