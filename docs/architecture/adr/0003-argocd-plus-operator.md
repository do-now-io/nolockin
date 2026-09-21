# ADR-0003 · ArgoCD réconcilie, l'opérateur rend

**Statut** : acceptée · 2026-09

## Contexte

Deux façons d'appliquer un manifeste : un opérateur qui fait tout (rend et applique), ou
GitOps pur (ArgoCD applique du YAML pré-rendu). Chacune a un défaut : l'opérateur seul
n'a pas d'historique ni d'UI de réconciliation ; ArgoCD seul ne sait pas rendre un
`nolockin.yaml`.

## Décision

Hybride :

1. Un push (ou `nlk deploy`, `nlk promote`, `nlk releases approve`, `nlk rollback`) amène `nlk-api` à commiter une **release** dans le manifest store Git : une CR `App` contenant le manifeste effectif de l'environnement et le digest d'image. La CLI est un client Git : elle ne parle jamais au cluster directement ([ADR-0007](0007-policy-in-repo-state-in-store.md)).
2. ArgoCD synchronise la CR `App` dans le namespace du projet.
3. `nlk-operator` réconcilie la CR `App` en objets Kubernetes standards (ou en `Rollout` Argo Rollouts pour `canary`/`blueGreen`) et en reporte le status.
4. ArgoCD affiche l'arbre complet (il suit les `ownerReferences`) et la santé.

## Raisons

- L'utilisateur obtient l'UI ArgoCD gratuitement : arbre des ressources, sync status, historique, rollback. C'est une partie de « tout fonctionne tout de suite ».
- Le manifest store Git est l'historique des déploiements, exportable par `git clone`.
- L'opérateur reste petit : il rend et il reporte, il ne gère ni Git ni l'historique.
- Un utilisateur qui préfère un GitOps « pur » peut pointer ArgoCD sur son propre dépôt de manifestes (`nlk project set --manifest-repo`), NoLockIn commit alors chez lui.

## Conséquences

- Deux composants à opérer (ArgoCD + opérateur) au lieu d'un. Accepté : ArgoCD est déjà nécessaire pour gérer la plateforme elle-même (app-of-apps).
- La latence d'un déploiement inclut un cycle de sync ArgoCD. On configure le webhook Git → ArgoCD pour rester < 5 s.

## Alternatives écartées

- **Flux** : équivalent techniquement, mais pas d'UI intégrée. L'UI est un argument produit ici.
- **Opérateur seul** : perd l'historique Git et l'UI.
