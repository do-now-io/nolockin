# Héberger NoLockIn chez vous

NoLockIn s'installe sur n'importe quel cluster Kubernetes conforme avec un chart Helm. C'est
**la même installation** que le cloud hébergé : un seul flag change, `billing.mode`. Vos
développeurs gardent la même CLI, le même manifeste, les mêmes dashboards.

## Prérequis

| Besoin | Détail |
|---|---|
| Kubernetes ≥ 1.29 | EKS, GKE, AKS, Scaleway Kapsule, OVH, k3s, Talos… `kind` pour essayer. |
| 3 nœuds recommandés | 4 vCPU / 16 GiB chacun pour de la production. Le control plane consomme ~2 vCPU / 6 GiB au repos. |
| Une StorageClass par défaut | Pour les add-ons, Prometheus, Loki, le manifest store. |
| Un LoadBalancer | Celui du cloud, ou MetalLB en bare metal. |
| Un domaine | `nlk.infra.acme.internal` pour l'API, Grafana, ArgoCD. Un wildcard si vous voulez fournir des sous-domaines aux apps. |
| Un IdP OIDC (optionnel) | Google Workspace, Entra ID, Keycloak… Sinon, le Dex embarqué avec ses connecteurs. |

## Installer

```bash
helm install nolockin oci://ghcr.io/nolockin/charts/nolockin \
  -n nolockin-system --create-namespace \
  --set global.domain=nlk.infra.acme.internal \
  --set global.appsDomain=apps.acme.internal \
  --set billing.mode=showback \
  --set auth.oidc.issuer=https://sso.acme.com \
  --set auth.oidc.clientId=nolockin \
  --set gateway.certManager.email=ops@acme.com

helm test nolockin -n nolockin-system
```

Cinq à huit minutes. À la fin : `nlk-api`, `nlk-operator`, ArgoCD, Argo Rollouts, Prometheus,
Grafana, Loki, CloudNativePG, Envoy Gateway, cert-manager, Dex, registry, metering. `helm
test` vérifie que l'API répond, qu'ArgoCD a synchronisé la plateforme et que Grafana est
provisionné.

Pour essayer sur un poste :

```bash
kind create cluster --name nlk
helm install nolockin oci://ghcr.io/nolockin/charts/nolockin -n nolockin-system --create-namespace --set global.profile=dev
```

Le profil `dev` passe tout en un réplica avec des rétentions courtes.

## Se connecter et créer un premier projet

```bash
nlk context add acme --server https://api.nlk.infra.acme.internal
nlk login --context acme
nlk context use acme
nlk project create demo
```

Puis, dans une app : `nlk init`, `git push`. Rien ne change par rapport au cloud hébergé.

## Les values qui comptent

| Clé | Rôle |
|---|---|
| `billing.mode` | `showback` mesure et affiche par équipe sans facturer ; `off` désactive le metering ; `stripe` si vous facturez des tiers. |
| `billing.pricing` | Votre grille : le coût réel de vos nœuds, pour un chargeback interne juste. |
| `auth.oidc.issuer` | Votre IdP. Les groupes OIDC peuvent mapper les rôles de projet. |
| `controlPlane.manifestStore.mirrorTo` | Un dépôt Git externe où pousser une copie de l'historique des releases. Recommandé. |
| `build.registry.mode` | `embedded` ou `external` avec votre Harbor, ECR, GAR. |
| `observability.metrics.remoteWrite` | Mimir, Thanos ou un Grafana Cloud à vous pour la rétention longue. |
| `security.runtimeClass` | `runsc` si vous avez gVisor ; vide pour `runc`. |
| `exit.agePublicKey` | La clé qui chiffrera les secrets des bundles importés ici. Générée à l'installation si vide. |

La liste complète est dans la [référence du chart](../reference/chart.md).

## Mettre à jour

```bash
helm upgrade nolockin oci://ghcr.io/nolockin/charts/nolockin -n nolockin-system --version 0.10.0 --reuse-values
```

Les versions de la plateforme suivent le semver. Une montée de version mineure ne touche pas
aux apps déployées : ArgoCD ne resynchronise que ce qui change. Les CRD sont versionnées avec
18 mois de compatibilité.

## Sauvegarder la plateforme

Trois choses portent l'état :

| État | Où | Sauvegarde |
|---|---|---|
| Les releases et leur historique | Manifest store (Git) | `mirrorTo` vers un dépôt externe, ou `git clone` régulier |
| Les données des add-ons | Volumes CNPG, Redis, MinIO | Sauvegardes CNPG vers un stockage objet ; snapshots de volumes |
| Les secrets et clés (dont la clé `age` du projet) | Secrets Kubernetes dans `nolockin-system` et les namespaces de projet | Sauvegarde etcd ou Velero |

Le code source des apps est chez vous, le manifeste aussi. Une plateforme réinstallée à vide
avec ces trois sauvegardes retrouve tout.

## Ce qui diffère du cloud hébergé

Rien, sauf `billing.mode` et ce que vous décidez : votre IdP, votre registry, votre
runtime, votre rétention. Le code est le même, le chart est le même, la CI qui teste la
sortie installe exactement ce chart sur le cluster cible.

## Aller plus loin

- [Quitter le cloud NoLockIn](sortie.md) : migrer un projet existant vers cette installation.
- [Sécurité et multi-tenant](../reference/securite.md) : ce que la plateforme garantit et ce qui reste à votre charge sur votre cluster.
