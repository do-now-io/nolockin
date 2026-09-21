# NoLockIn

**Le PaaS que vous pouvez quitter.**

NoLockIn est une Platform-as-a-Service open source (Apache-2.0) construite sur Kubernetes.
Vous déployez depuis un `nolockin.yaml`, vous payez à la seconde ce que vous consommez
(CPU, mémoire, stockage, trafic sortant) sur notre cloud, et le jour où vous voulez partir,
vous installez la même plateforme sur votre cluster, vous importez votre export, et vous
changez de contexte. Rien d'autre.

```bash
# Déployer : un fichier dans votre dépôt, puis git push
nlk init && git push
# → staging en ligne. Puis, quand vous êtes prêts :
nlk promote staging prod && nlk releases approve prod/#1

# Partir
helm install nolockin oci://ghcr.io/nolockin/charts/nolockin -n nolockin-system --create-namespace
nlk export --project acme > acme.nlkbundle
nlk import acme.nlkbundle --context mon-cluster
nlk exit cutover --project acme --to mon-cluster
```

## Trois garanties

| Garantie | Ce que ça veut dire concrètement |
|---|---|
| **Tout est open source** | Plateforme, CLI, opérateur, metering, facturation : un seul dépôt, une seule licence, aucune fonctionnalité « entreprise » cachée. |
| **Paiement à l'usage, à la seconde** | Pas de plan, pas de siège, pas d'engagement. La facture est un dashboard Grafana que vous pouvez recalculer vous-même. |
| **GitOps sans y penser** | Un push déploie. La version n'est jamais écrite dans votre dépôt. Staging et prod dans un seul fichier, promotion sans rebuild, canari et approbation déclarés en YAML. |
| **La sortie est une fonctionnalité** | `nlk export` n'est jamais conditionné au paiement, jamais bridé, sans frais d'egress. Le protocole de sortie est testé en CI à chaque release. |

## Structure du dépôt

```
docs/            Documentation (commencer par docs/README.md)
  demarrer/      Introduction, installation, première app, environnements
  guides/        Déployer, secrets, domaines, add-ons, observabilité, self-hosting, sortie
  reference/     Manifeste, CLI, chart, tarification, sécurité, glossaire
  architecture/  Vue d'ensemble et ADR
  projet/        Vision, roadmap, FAQ
examples/        Manifestes nolockin.yaml d'exemple
charts/nolockin/ Chart Helm umbrella (scaffold)
site/            Site vitrine et générateur de la documentation (site/build-docs.py)
```

## Lire la documentation

Le [sommaire](docs/README.md) est le point d'entrée. Pour aller vite :
[Introduction](docs/demarrer/introduction.md), [Première application](docs/demarrer/premiere-app.md),
[Protocole de sortie](docs/guides/sortie.md), [Décisions d'architecture](docs/architecture/adr/README.md).

## Site vitrine et documentation

La documentation est du Markdown versionné dans `docs/`. Le site la régénère : en local avec
`python3 site/build-docs.py`, et automatiquement à chaque push sur `main` via
[`.github/workflows/site.yml`](.github/workflows/site.yml), qui vérifie les liens puis publie
sur GitHub Pages et, si configuré, sur un bucket Scaleway (voir [`site/README.md`](site/README.md)).

```bash
python3 site/build-docs.py && python3 site/check-docs.py
cd site && python3 -m http.server 8080
# http://localhost:8080        vitrine
# http://localhost:8080/docs/  documentation
```

## Licence

Apache-2.0. La licence fait partie de la promesse : pas de BSL, pas de SSPL, pas de clause
« sauf si vous êtes un cloud provider ».
