# 00 · Vision et principes

## Le problème

Un PaaS vend de la productivité : `git push`, et l'app tourne, avec logs, métriques, TLS,
scaling. Le prix caché, c'est la rançon au moment de partir :

- **API propriétaire** : le `Procfile`, les buildpacks maison, le format d'add-on ne tournent nulle part ailleurs.
- **Données captives** : la base managée s'exporte par un dump lent, throttlé, parfois payant.
- **Frais d'egress** : sortir un téraoctet coûte plus cher que le stocker un an.
- **Tarif unilatéral** : le fournisseur change la grille, supprime le plan gratuit, et il n'y a nulle part où aller sans tout réécrire.
- **Fonctionnalités « entreprise »** : SSO, audit, régions, tout ce qui compte quand on grandit est derrière un devis.

Résultat : les équipes qui grandissent finissent par reconstruire elles-mêmes sur Kubernetes,
en perdant six mois. Les autres restent et paient.

## La promesse

> **NoLockIn est un PaaS dont la sortie est une fonctionnalité, pas une négociation.**

Trois garanties, vérifiables, écrites dans le code plutôt que dans un contrat :

### 1. Tout est open source

La plateforme entière est publiée sous **Apache-2.0** : control plane, opérateur, CLI,
chart Helm, metering, moteur de facturation, dashboards. Il n'existe pas d'édition
« entreprise ». Le SSO, l'audit, le multi-région, les quotas : tout est dans le dépôt public.

Ce qui est payant : **l'hébergement** (notre cloud) et **le support** (SLA, astreinte,
aide à la migration). Jamais une fonctionnalité.

### 2. Paiement à l'usage, à la seconde

Sur le cloud NoLockIn, vous payez quatre choses, mesurées à la seconde et facturées au mois :

| Ressource | Unité |
|---|---|
| CPU | vCPU-seconde consommée (pas réservée) |
| Mémoire | GiB-seconde (working set) |
| Stockage | GiB-mois provisionné |
| Trafic sortant | GiB (egress Internet) |

Pas de plan, pas de siège, pas de minimum, pas d'engagement. La grille de prix est un
fichier YAML versionné dans le dépôt. La facture est un dashboard Grafana : les mêmes
requêtes PromQL, les mêmes chiffres. Voir [Tarification et metering](../reference/tarification.md).

### 3. La sortie est une fonctionnalité

Partir tient en quatre commandes ([Protocole de sortie](../guides/sortie.md)) :

```bash
helm install nolockin oci://ghcr.io/nolockin/charts/nolockin -n nolockin-system --create-namespace
nlk export --project acme > acme.nlkbundle
nlk import acme.nlkbundle --context mon-cluster
nlk exit cutover --project acme --to mon-cluster
```

Engagements, sans condition :

- `nlk export` fonctionne **même si le compte est impayé ou suspendu**.
- L'export n'est **jamais throttlé** et **l'egress de sortie est facturé 0 €**.
- Le protocole de sortie est **un test d'intégration** exécuté à chaque release :
  déploiement sur un cluster A, export, import sur un cluster B (kind), bascule, vérification.
  Une release qui casse la sortie ne sort pas.
- Le manifeste `nolockin.yaml` se rend en Kubernetes standard (`nlk render`). Si un jour
  vous voulez quitter NoLockIn lui-même, vous avez du YAML `kubectl apply`-able.

## Ce que ça change pour l'utilisateur

**Jour 1** : `nlk init`, `git push`. L'app est en ligne avec TLS, un dashboard Grafana
par service, les logs dans Loki, l'app visible dans ArgoCD, un autoscaler configuré.
Zéro fichier Kubernetes écrit, zéro commande de déploiement à retenir.

**Jour 30** : un environnement `prod` à côté du `staging`, dans le même fichier. Chaque push
va en staging. `nlk promote staging prod`, un owner approuve, le canari fait le reste.

**Jour 400** : l'équipe a grandi, la facture aussi, un cluster interne existe. Le DevOps
installe NoLockIn dessus en une commande Helm, migre projet par projet un vendredi
après-midi. Les développeurs ne changent rien : même CLI, même manifeste, même dashboards.
Seul le contexte change.

**Jour 401** : le cloud NoLockIn a perdu un client et gagné une référence. C'est voulu.

## Où ça tourne

Le cloud hébergé tourne aujourd'hui sur **une seule région, `fr-par`** : un cluster Kubernetes
Kapsule chez Scaleway, à Paris, opéré par une équipe française, sous droit français. Aucun
hyperscaler américain sur le chemin de la donnée. Une deuxième région européenne est prévue
([roadmap](roadmap.md)) ; elle sera annoncée, jamais imposée. Et le self-hosted reste la
réponse pour qui veut choisir son hébergeur.

## Modèle économique (pour qu'il n'y ait pas de mystère)

| Source de revenu | Pourquoi ça tient |
|---|---|
| Marge sur l'hébergement à l'usage | Une PME sans équipe infra paie l'exploitation, pas la captivité. La plupart ne partiront jamais : c'est plus simple de rester. |
| Support et SLA sur le self-hosted | Les entreprises qui migrent chez elles veulent un interlocuteur. |
| Assistance à la migration | Nous vendons le service de faire partir les gens. C'est la meilleure preuve qu'on ne les retient pas. |

Ce qu'on ne fera **jamais** :

- Changer de licence vers BSL, SSPL ou une licence « source available ».
- Ajouter des frais d'egress à la sortie.
- Créer une fonctionnalité réservée au cloud hébergé.
- Dégrader volontairement l'expérience self-hosted.

## Non-objectifs

- **Pas une distribution Kubernetes.** NoLockIn s'installe sur n'importe quel cluster conforme (EKS, GKE, AKS, OVH, Scaleway, k3s, Talos, kind). On n'installe pas le cluster.
- **Pas d'abstraction multi-cloud au-dessus de Kubernetes.** Kubernetes est le substrat unique et assumé ([ADR-0001](../architecture/adr/0001-kubernetes-only.md)).
- **Pas de runtime propriétaire.** Les builds produisent des images OCI standard (buildpacks ou Dockerfile).
- **Pas de FaaS / serverless en v1.** Des conteneurs longue durée, des workers, des crons. Le scale-to-zero est prévu, pas les fonctions.
- **Pas de marketplace d'add-ons tiers en v1.** Postgres, Redis, stockage objet, opérés par des opérateurs open source.

## Personas

| Persona | Ce qu'il veut | Ce qui le fait rester | Ce qui le fait partir |
|---|---|---|---|
| **CTO de startup (3-15 devs)** | Livrer sans DevOps | Simplicité, prix lisible | Levée de fonds + recrutement infra |
| **DevOps de scale-up** | Un cluster à lui, sans réécrire le tooling des devs | Même CLI hébergé et self-hosted | Rien : il installe direct chez lui |
| **Agence / studio** | Un projet par client, facturation par projet | Facture par projet, export par projet | Le client reprend son infra : `nlk export` |
| **DSI réglementée** | Souveraineté, audit, pas de dépendance | Self-hosted dès le jour 1, support payant | N/A |

## Principes de conception

1. **Rien de propriétaire sur le chemin critique.** Chaque composant a un projet open source derrière lui et une sortie standard (images OCI, YAML Kubernetes, dumps SQL, S3).
2. **La politique dans le dépôt source, l'état dans le manifest store.** `nolockin.yaml` dit ce qui tourne, où et comment ça sort. Le manifest store dit quelle release est live. Aucune version n'est écrite chez l'utilisateur, aucune configuration n'existe hors de son fichier. La console écrit dans le manifeste ([ADR-0007](../architecture/adr/0007-policy-in-repo-state-in-store.md)).
3. **Un environnement = un projet = un namespace.** Isolation, quota, secrets et facturation suivent la même frontière.
4. **La facture est un dashboard.** Si un chiffre est facturé, il est visible en PromQL dans Grafana, avec la requête.
5. **L'export n'est jamais conditionnel.** Aucun état de compte ne bloque `nlk export`.
6. **Hébergé et self-hosted exécutent le même code.** Une seule branche, un seul chart, un flag `billing.mode`.
7. **La sortie est testée avant la fonctionnalité.** Une fonctionnalité qui n'a pas de chemin d'export documenté et testé n'est pas mergée.
