# Introduction

NoLockIn est un PaaS : vous lui donnez un dépôt Git, il vous rend une application en ligne,
observée, sauvegardée, qui scale. Ce qui le distingue tient en une phrase : **c'est le PaaS
que vous pouvez quitter.** La sortie est une fonctionnalité, testée à chaque release, pas une
clause de contrat.

## Ce que vous obtenez

Après un `git push` :

- Votre application construite en image OCI (buildpacks ou votre Dockerfile), signée, scannée.
- Une URL HTTPS, un certificat renouvelé tout seul, votre domaine si vous le voulez.
- Deux réplicas minimum, un autoscaler, des health checks, une répartition sur plusieurs nœuds.
- Un dashboard Grafana par application, vos logs dans Loki, vos alertes routées vers Slack ou PagerDuty.
- L'arbre complet de vos ressources dans ArgoCD : Deployments, Pods, Services, routes, bases.
- Des add-ons managés : Postgres, Redis, stockage objet S3, avec sauvegardes et restauration à un instant donné.
- Une facture calculée à la seconde, dont chaque ligne est une requête Prometheus que vous pouvez rejouer.

Vous n'écrivez aucun fichier Kubernetes. Vous écrivez `nolockin.yaml`, et la
[référence du manifeste](../reference/manifeste.md) tient en une page.

## Pour qui

| Vous êtes | NoLockIn vous sert à |
|---|---|
| Une équipe produit sans DevOps | Livrer en production dès le premier jour, sans apprendre Kubernetes, sans craindre la facture |
| Une scale-up qui a maintenant une équipe infra | Reprendre l'hébergement chez vous, sur votre cluster, sans réécrire l'outillage des développeurs |
| Une agence ou un studio | Un projet par client, une facture par projet, et rendre l'infrastructure au client quand il la veut |
| Une DSI soumise à des contraintes de souveraineté | Un cloud hébergé en France chez Scaleway aujourd'hui, ou la même plateforme sur votre infrastructure |

## Les trois garanties

**Tout est open source.** Control plane, opérateur, CLI, chart Helm, metering, facturation,
dashboards : un dépôt, une licence Apache-2.0, pas d'édition « entreprise ». Le SSO, l'audit,
le multi-région sont dans le code public. Ce qui est payant : l'hébergement et le support.

**Paiement à la seconde.** vCPU consommé, mémoire utilisée, stockage provisionné, trafic
sortant. Pas de plan, pas de siège, pas de minimum. La facture est un dashboard Grafana, et
`nlk usage explain` affiche la requête derrière chaque ligne.

**La sortie est une fonctionnalité.** Quatre commandes pour migrer vers votre cluster.
L'export fonctionne même si le compte est impayé, sans limitation de débit, sans frais de
trafic. Et le protocole complet est un test d'intégration bloquant sur chaque release.

## Comment ça marche, en cinq lignes

1. `nolockin.yaml` dans votre dépôt déclare vos services, workers, crons, add-ons et environnements.
2. Un push sur la branche suivie par un environnement déclenche un build, puis une **release** dans cet environnement.
3. La release est un commit dans un dépôt Git que la plateforme opère, le manifest store. ArgoCD l'applique.
4. L'opérateur NoLockIn transforme votre manifeste en objets Kubernetes standards : rien de propriétaire.
5. Pour la production, vous **promouvez** la release validée en staging : même image, aucun rebuild, approbation si vous l'exigez.

Le détail est dans la [vue d'ensemble de l'architecture](../architecture/vue-d-ensemble.md).

## Comment lire cette documentation

| Vous voulez | Allez à |
|---|---|
| Mettre une app en ligne maintenant | [Installation](installation.md) puis [Première application](premiere-app.md) |
| Séparer staging et production | [Environnements](environnements.md) |
| Comprendre un champ du manifeste ou une commande | [Manifeste](../reference/manifeste.md), [CLI](../reference/cli.md) |
| Installer NoLockIn sur votre cluster | [Héberger NoLockIn chez vous](../guides/self-hosting.md) |
| Savoir comment on part | [Quitter le cloud NoLockIn](../guides/sortie.md) |
| Comprendre pourquoi c'est construit ainsi | [Décisions d'architecture](../architecture/adr/README.md) |

## État du projet

Nous sommes au jalon M0, la spécification. Cette documentation est écrite avant le code, et
c'est voulu : elle est le contrat que l'implémentation doit respecter. La CLI et le chart
arrivent au jalon M1, le protocole de sortie au jalon M2, la bêta hébergée au jalon M3
([roadmap](../projet/roadmap.md)). Si une page décrit un comportement et que le code fait
autre chose, c'est le code qui a tort.
