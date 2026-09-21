# 07 · Sécurité et multi-tenant

## Modèle de tenant

**Un projet = un namespace Kubernetes.** C'est la frontière d'isolation, de quota, de
RBAC, de réseau et de facturation. Il n'y a pas de tenant « au-dessus » du namespace côté
Kubernetes : une organisation qui a trois projets a trois namespaces.

Le cloud hébergé est **multi-tenant par namespace** sur des clusters partagés, avec les
garde-fous ci-dessous. Une option `isolation: dedicated-nodes` (node pool dédié, taints)
existe pour les projets qui l'exigent, facturée au nœud. Le self-hosted décide de son
niveau d'isolation.

## Isolation par défaut d'un projet

| Couche | Mécanisme | Détail |
|---|---|---|
| Pods | Pod Security Standards `restricted` | Pas de root, pas de privilèges, seccomp `RuntimeDefault`, capabilities drop ALL, rootfs read-only sauf `/tmp` et volumes déclarés. |
| Runtime | gVisor (`runsc`) sur le cloud hébergé | RuntimeClass appliquée à tous les pods utilisateur. Self-hosted : `runc` par défaut, gVisor ou Kata activables. |
| Réseau | NetworkPolicy default-deny ingress + egress contrôlé (Cilium) | Entrant : Gateway et pods de la même app seulement. Sortant : Internet par défaut (`spec.network.egress`), jamais vers les autres namespaces ni le control plane, hors DNS et add-ons du projet. |
| Ressources | ResourceQuota + LimitRange | Quota par projet (`nlk project quota`). Limites par défaut sur chaque pod. |
| Nœuds | Anti-affinity + topology spread | Réplicas d'un même service répartis sur des nœuds et zones différents. |
| Stockage | PVC par projet, StorageClass chiffrée | Chiffrement au repos par le provider. Snapshots dans le même périmètre. |
| Secrets | Secrets Kubernetes chiffrés dans etcd (KMS) | Jamais dans le manifeste, jamais dans les logs, masqués dans `nlk env`. |
| Images | Registry par projet, pull par ServiceAccount du projet | Un projet ne peut pas tirer les images d'un autre. |

## Identité et accès

- **Authentification** : OIDC via Dex. Hébergé : GitHub, Google, e-mail magic link, SAML sur demande. Self-hosted : votre IdP.
- **Rôles par projet** :

| Rôle | Peut |
|---|---|
| `owner` | Tout, dont supprimer le projet, gérer les membres, la facturation, `exit cutover`. |
| `developer` | Déployer, logs, exec, secrets (écriture), scale, rollback. Pas de suppression de projet ni d'add-on. |
| `viewer` | Lire : status, logs, métriques, ArgoCD. |
| `billing` | Factures, usage. Rien d'autre. |

- **Tokens machine** : `nlk token create --role developer --ttl 90d` pour la CI. Scopés à un projet.
- **Audit** : chaque appel API authentifié est journalisé (qui, quoi, quand, depuis où) dans Loki, rétention 1 an, exportable, inclus dans le bundle. Les `kubectl` directs des opérateurs de la plateforme sont journalisés par l'audit Kubernetes.

## Supply chain

- Les images construites par buildpacks sont **reproductibles** et signées (cosign, keyless via l'OIDC du build).
- **SBOM** SPDX généré à chaque build, consultable (`nlk releases --sbom`).
- **Scan** Trivy à chaque build et quotidien sur les images déployées. Vulnérabilités critiques : alerte, jamais de blocage automatique du déploiement (c'est votre décision, `policy.blockCritical: true` pour l'activer).
- L'opérateur vérifie la signature avant d'admettre une image sur le cloud hébergé (policy-controller).
- Les composants de la plateforme sont eux-mêmes signés, avec SBOM, et le chart Helm est publié en OCI signé.

## Secrets

- `nlk secret set` chiffre en transit (TLS) et stocke en Secret Kubernetes chiffré par KMS.
- Rotation : `nlk secret set` crée une nouvelle version, un `nlk deploy` (ou rollout automatique si `secrets.autoRollout: true`) l'applique.
- External Secrets Operator disponible pour synchroniser depuis Vault, AWS SM, GCP SM, Azure KV : le manifeste référence le secret, la plateforme le récupère.
- Export : chiffré `age` vers la clé publique du contexte cible ou un destinataire fourni. Jamais en clair sur le réseau ni sur disque.

## Réseau et TLS

- TLS 1.2+ partout, certificats Let's Encrypt renouvelés automatiquement, HSTS activé sur `.nolockin.app`.
- mTLS optionnel entre services d'une même app (Cilium ou Envoy sidecarless).
- Protection L7 : rate limiting par route (`routes[].rateLimit`), taille max de requête, timeouts par défaut 30 s.
- DDoS : couche L3/L4 du provider cloud, pas de promesse au-delà.

## Données

- **Localisation** : région choisie à la création du projet, jamais déplacée sans action de l'utilisateur. Aujourd'hui une seule région, `fr-par` : cluster Kubernetes Kapsule chez Scaleway, datacenters en France, opérateur français. Registry, bases, sauvegardes, logs et métriques restent dans cette région.
- **Backups add-ons** : chiffrés, dans la même région, rétention configurable, PITR 7 jours par défaut.
- **Suppression** : délai de grâce 30 jours, puis destruction des PVC, snapshots, images, logs, secrets et attestation signée.
- **RGPD** : DPA standard, sous-traitants listés publiquement. Aucun sous-traitant hébergeur soumis à une législation extraterritoriale : à ce jour, NoLockIn est souverain français de bout en bout sur son cloud hébergé.

## Ce qui reste à la charge de l'utilisateur

- La sécurité de son code et de ses dépendances (le scan aide, ne corrige pas).
- La gestion de ses utilisateurs finaux (authentification applicative).
- La configuration DNS de ses domaines.
- En self-hosted : la sécurité du cluster lui-même (versions, CIS benchmark, accès au plan de contrôle Kubernetes).

## Divulgation responsable

`security@nolockin.io`, clé PGP publiée, réponse sous 48 h, correctifs publiés avec
advisory GitHub. Un programme de bug bounty est prévu à partir de la GA.
