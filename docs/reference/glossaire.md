# Glossaire

| Terme | Définition |
|---|---|
| **Add-on** | Une dépendance managée déclarée dans le manifeste (`postgres`, `redis`, `bucket`) et opérée par un opérateur open source. Un add-on est par environnement. |
| **App** | Un dépôt de code déployé. Une app contient des services, des workers, des crons, des add-ons, et des environnements. |
| **Approbation** | Étape optionnelle (`deploy.approval: owner`) où une release attend qu'un owner du projet la libère avec `nlk releases approve`. |
| **Base** | La partie `spec` du manifeste, commune à tous les environnements, sur laquelle chaque overlay est fusionné. |
| **Bundle** | L'export complet d'un projet au format `.nlkbundle` : manifestes, releases, images, secrets chiffrés, snapshots d'add-ons, plan DNS. Signé. |
| **Buildpacks** | Cloud Native Buildpacks : la méthode de build par défaut, qui détecte le langage et produit une image OCI reproductible sans Dockerfile. |
| **Canari** | Stratégie de rollout où la nouvelle version reçoit une part croissante du trafic, avec analyse automatique des erreurs et de la latence, et rollback si les seuils sont dépassés. |
| **Contexte** | Un pointeur de la CLI vers une plateforme NoLockIn : URL d'API et identité. `hosted` est le cloud NoLockIn ; tout autre contexte est une installation à vous. |
| **Control plane** | L'API, l'opérateur et les composants qui transforment un manifeste en objets Kubernetes. Une installation NoLockIn = un control plane. |
| **Cutover** | La bascule de trafic d'un contexte à un autre pendant une sortie, orchestrée par `nlk exit cutover`. |
| **Dérive** | Un écart entre ce qui tourne et ce que dit le manifeste, créé par une commande impérative (`nlk scale`). Toujours affichée, jamais silencieuse. |
| **Environnement** | Une déclinaison d'une app (`staging`, `prod`) : un projet cible, un overlay, une politique de release. Déclaré sous `environments`. |
| **Freeze** | Une fenêtre de temps (`deploy.freeze`) pendant laquelle les releases sont mises en file d'attente. |
| **Manifest store** | Le dépôt Git, opéré par NoLockIn ou fourni par vous, qui porte l'état : la release live de chaque environnement, les releases en attente, l'historique. ArgoCD le synchronise. |
| **Manifeste** | Le fichier `nolockin.yaml` à la racine de votre dépôt. Il déclare la politique : ce qui tourne, où, comment ça sort. Jamais la version déployée. |
| **Metering** | La mesure de la consommation (CPU, mémoire, stockage, egress) à partir de recording rules Prometheus publiques, agrégée par `nlk-meter`. |
| **Override** | La valeur appliquée par une commande impérative par-dessus la release live, en attendant que le manifeste la rattrape. |
| **Overlay** | La partie d'un environnement qui surcharge la base : `services`, `addons`, `env`, `deploy`… Fusionnée selon des règles fixes. |
| **Owner** | Le rôle qui peut tout faire sur un projet : approuver, supprimer, gérer les membres et la facturation, lancer une sortie. |
| **Preview** | Une instance éphémère d'une app déployée pour une pull request, détruite au merge. |
| **Projet** | L'unité d'isolation et de facturation : un namespace Kubernetes, un quota, des secrets, une facture. Un environnement = un projet. |
| **Promotion** | `nlk promote <from> <to>` : créer dans `<to>` une release avec le digest et le SHA de la release live de `<from>`. Sans build. |
| **Release** | Un digest d'image + le SHA source (code et manifeste) + l'overlay d'un environnement, rendus ensemble. Vit dans le manifest store. |
| **Rendu** | Le YAML Kubernetes standard produit par l'opérateur à partir du manifeste effectif. `nlk render` l'affiche. C'est la sortie de niveau 2. |
| **Rollback** | Une nouvelle release qui reprend le digest et le manifeste d'une release passée. Historisée, donc annulable. |
| **Service** | Un processus exposé (HTTP, gRPC, TCP) d'une app. Génère Deployment ou Rollout, Service, HTTPRoute, HPA, PDB. |
| **Showback** | Le mode de facturation du self-hosted : le metering mesure et affiche par équipe, sans émettre de facture. |
| **Sortie** | La migration d'un projet d'un contexte vers un autre, avec bascule de trafic. Trois niveaux : changer de cluster, quitter NoLockIn, quitter Kubernetes. |
| **Track** | La branche ou le glob de tags qu'un environnement suit. Chaque push correspondant produit une release. Un environnement sans `track` ne reçoit que des promotions. |
| **Worker** | Un processus non exposé d'une app, qui scale sur le CPU ou sur la longueur d'une file. |
