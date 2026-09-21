# ADR-0007 · La politique dans le dépôt source, l'état dans le manifest store

**Statut** : acceptée · 2026-09

## Contexte

Un PaaS GitOps doit répondre à trois questions : qu'est-ce qui déclenche un déploiement,
où vit la version déployée, et comment on gère plusieurs environnements. Les réponses
courantes sont contradictoires : « la version dans le repo » est GitOps pur mais crée des
boucles de build ; « deux fichiers de config » est simple mais diverge ; « une commande
`deploy` » est explicite mais ce n'est pas ce que les développeurs attendent en 2026.

## Décision

1. **Le déclencheur par défaut est le push.** Un environnement `track` une branche ou un glob de tags. Chaque push correspondant produit une release. `nlk deploy` est un déclencheur manuel du même chemin.
2. **Le dépôt source porte la politique, le manifest store porte l'état.** `nolockin.yaml` déclare les environnements, ce qu'ils suivent, comment ils sortent (approbation, canari, freeze). Le manifest store, un Git opéré par NoLockIn ou fourni par l'utilisateur, porte la release live de chaque environnement : digest, SHA, rendu. **Aucune version n'est jamais écrite dans le dépôt source.** Un tag en lecture seule (`tagOnRelease`) est le seul marqueur autorisé.
3. **Un fichier, des overlays.** Une base commune et un overlay par environnement dans le même fichier, ou dans `environments/<env>.yaml` pour une propriété séparée. Jamais deux manifestes complets.
4. **Un environnement = un projet.** Namespace, quota, secrets et facture suivent la même frontière.
5. **La promotion est explicite et sans build.** `nlk promote <from> <to>` copie le digest et le SHA de la release live de `<from>` et les rend avec l'overlay de `<to>`. Il n'y a pas de champ `promoteFrom` dans le manifeste : la source d'une promotion est un choix au moment de promouvoir, pas une propriété de l'environnement. Un environnement sans `track` ne reçoit que des promotions ou des `nlk deploy` explicites.
6. **La CLI est un client Git.** Toute commande qui change ce qui tourne produit un commit dans le manifest store. Toute commande qui change la politique réécrit le manifeste et ouvre une PR sur le dépôt source ; en urgence l'effet est immédiat et la dérive est affichée jusqu'au merge.
7. **Une release exécute code, manifeste et overlay au même SHA.** Un changement de configuration prod passe par la branche suivie puis par une promotion, comme du code. `nolockin.yaml` est exclu du contexte de build pour que ce trajet ne reconstruise pas l'image.

## Raisons

- **Pas de boucle.** Écrire « prod = abc123 » dans le dépôt source crée un commit, donc un push, donc un build de staging d'un commit qui n'a rien changé. Séparer politique et état supprime le problème à la racine, comme le font ArgoCD Image Updater et Flux image automation.
- **Historique propre.** Le dépôt source raconte le code. Le manifest store raconte l'exploitation. Les deux sont clonables.
- **Pas de divergence.** Un overlay prod est petit et relu en tant que tel. Deux fichiers complets divergent sans que personne ne le voie.
- **Build once, promote many.** Le digest promu en prod est exactement celui qui a tourné en staging. Aucune reconstruction ne peut introduire une différence.
- **Pas de `promoteFrom`.** Le déclarer figerait une topologie (staging → prod) que les équipes contournent dès le premier hotfix. La promotion reste une action nommée, tracée, avec sa source visible dans `nlk releases`.
- **Cohérence avec la sortie.** Le manifest store est déjà l'historique exporté dans le bundle. Les releases, les approbations et les promotions y sont, et partent avec.

## Conséquences

- Deux dépôts Git dans le modèle mental : le sien et le manifest store. La console et `nlk releases` masquent le second pour l'usage courant ; les équipes GitOps avancées le prennent en main (`--manifest-repo`).
- Le manifest store devient critique : répliqué, miroir externe configurable, inclus dans le bundle.
- Argo Rollouts entre dans la plateforme pour `canary` et `blueGreen`.
- Les commandes impératives sont plus complexes qu'un simple `kubectl scale` : elles appliquent, tracent l'override et ouvrent une PR.

## Alternatives écartées

- **Version épinglée dans `nolockin.yaml`** : GitOps pur, mais boucle de build et pollution de l'historique.
- **`nolockin.staging.yaml` + `nolockin.prod.yaml`** : divergence silencieuse, revue impossible du delta.
- **`promoteFrom: staging` dans le manifeste** : topologie figée, et une promotion automatique implicite qui rend la question « pourquoi la prod a changé ? » plus difficile à répondre.
- **Pas de push-to-deploy, `nlk deploy` seul** : explicite, mais à rebours des attentes, et une friction qu'on oubliera d'expliquer.
