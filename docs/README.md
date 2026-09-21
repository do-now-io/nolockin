# Documentation NoLockIn

NoLockIn est une Platform-as-a-Service open source construite sur Kubernetes. Un fichier
`nolockin.yaml` dans votre dépôt, un `git push`, et votre application tourne avec TLS,
autoscaling, Grafana, logs et ArgoCD. Vous payez à la seconde ce que vous consommez sur notre
cloud, et le jour où vous voulez partir, la même plateforme s'installe sur votre cluster.

> **État du projet : spécification (jalon M0).** Cette documentation décrit le produit tel qu'il
> est spécifié. La CLI `nlk` et le chart Helm arrivent au jalon M1 ([roadmap](projet/roadmap.md)).
> Les commandes, fichiers et comportements décrits ici sont la cible que le code doit respecter.

## Commencer

| Page | Vous y apprenez |
|---|---|
| [Introduction](demarrer/introduction.md) | Ce qu'est NoLockIn, pour qui, les trois garanties, comment lire cette documentation |
| [Installation](demarrer/installation.md) | Installer la CLI `nlk`, se connecter, comprendre les contextes |
| [Première application](demarrer/premiere-app.md) | De `nlk init` à une URL en ligne, avec dashboards et logs, en cinq minutes |
| [Environnements](demarrer/environnements.md) | Ajouter un staging et une production dans le même fichier, promouvoir, approuver |

## Guides

| Page | Vous y apprenez |
|---|---|
| [Déployer et livrer](guides/deployer.md) | Déclencheurs, releases, canari, approbation, fenêtres de gel, previews, rollback, dérive |
| [Secrets](guides/secrets.md) | Où vivent les secrets, comment les référencer, les tourner, les exporter |
| [Domaines et TLS](guides/domaines.md) | Brancher un domaine, vérifier le DNS, certificats, redirections |
| [Add-ons](guides/add-ons.md) | Postgres, Redis, stockage objet : déclarer, utiliser, sauvegarder, restaurer, exporter |
| [Observabilité](guides/observabilite.md) | Ce que Grafana, Loki, ArgoCD et les alertes vous donnent sans configuration |
| [Héberger NoLockIn chez vous](guides/self-hosting.md) | Installer la plateforme sur votre cluster, la configurer, la maintenir |
| [Quitter le cloud NoLockIn](guides/sortie.md) | Le protocole de sortie complet, ses garanties, son retour arrière |

## Référence

| Page | Contenu |
|---|---|
| [Manifeste `nolockin.yaml`](reference/manifeste.md) | Chaque champ, ses défauts, les environnements, la politique de release, la validation |
| [CLI `nlk`](reference/cli.md) | Toutes les commandes, les flags, les codes de retour |
| [Chart Helm](reference/chart.md) | Installation, `values.yaml`, arborescence |
| [Tarification et metering](reference/tarification.md) | Ce qui est mesuré, comment, à quel prix, comment le vérifier |
| [Sécurité et multi-tenant](reference/securite.md) | Isolation, identité, supply chain, données, souveraineté |
| [Glossaire](reference/glossaire.md) | Les termes utilisés dans cette documentation |

## Architecture

| Page | Contenu |
|---|---|
| [Vue d'ensemble](architecture/vue-d-ensemble.md) | Les composants, les flux de déploiement et de metering, le modèle de release |
| [Décisions d'architecture](architecture/adr/README.md) | Les sept ADR : les choix structurants et les alternatives écartées |

## Projet

| Page | Contenu |
|---|---|
| [Vision et principes](projet/vision.md) | Pourquoi ce produit existe, ce qu'il promet, ce qu'il refuse de faire |
| [Roadmap](projet/roadmap.md) | Les jalons et leurs critères de sortie |
| [Questions fréquentes](projet/faq.md) | Les questions qu'on nous pose avant de commencer |

## Exemples

Les manifestes de [`examples/`](../examples/) sont rendus dans la section Exemples de la
documentation : l'[app de référence](../examples/nolockin.yaml) à deux environnements, le
[manifeste minimal](../examples/minimal.yaml), et la variante à
[propriété séparée](../examples/split-ownership/) pour un CODEOWNERS sur la production.
