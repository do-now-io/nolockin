# ADR-0006 · Le protocole de sortie est un test bloquant de la CI

**Statut** : acceptée · 2026-09

## Contexte

Une promesse de portabilité qui n'est pas testée se dégrade à chaque release. Les
procédures de migration « documentées » chez les concurrents sont typiquement obsolètes.

## Décision

Le pipeline CI de `main` inclut un job `exit-e2e` bloquant :

1. Deux clusters `kind` : `source` et `target`.
2. Installer NoLockIn sur les deux (`source` en `billing.mode=stripe-test`, `target` en `showback`).
3. Déployer l'app de référence (`examples/reference-app` : web + worker + cron + Postgres HA + Redis + bucket) sur `source`, injecter du trafic et des écritures continues.
4. `nlk export` → `nlk import` → `nlk exit plan` → `nlk exit cutover` → `nlk exit verify`.
5. Assertions : aucune erreur de lecture, < 10 s d'écritures refusées, égalité des comptages, checksums S3 identiques, certificats valides sur `target`, `nlk usage` de `source` exclut l'egress d'export.
6. `nlk exit rollback` puis re-cutover, mêmes assertions.

Une PR qui fait échouer `exit-e2e` ne peut pas être mergée. Une fonctionnalité qui
ajoute un type de ressource doit étendre l'app de référence et le job.

## Raisons

- C'est la seule façon de rendre la promesse crédible dans la durée.
- Cela force chaque fonctionnalité à avoir un chemin d'export avant d'exister.
- Le rapport du job (durée, coupure mesurée) est publié sur le site : la preuve est un artefact CI, pas un argument marketing.

## Conséquences

- CI plus lente (~25 min). Accepté ; le job tourne sur `main` et sur les PR qui touchent `operator/`, `cli/exit`, `charts/`, `addons/`.
- Il faut maintenir l'app de référence comme un produit.
