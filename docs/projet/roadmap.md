# 08 · Roadmap

Chaque jalon a un **critère de sortie** vérifiable. La règle du projet : le protocole de
sortie précède la fonctionnalité, donc le jalon « sortie » arrive avant le lancement
commercial.

| Jalon | Contenu | Critère de sortie | Cible |
|---|---|---|---|
| **M0 · Spécification** | Ce dossier `docs/`, le site vitrine, le schéma JSON du manifeste v1. | Specs relues par 5 CTO/DevOps externes, 3 lettres d'intention. | Sept. 2026 |
| **M1 · Alpha self-hosted** | Chart Helm installable sur kind/k3s. `nlk init/deploy/logs/status/render`. Buildpacks + Dockerfile. Gateway + TLS. Grafana/Loki/ArgoCD provisionnés. | `nlk deploy` d'une app Node + Postgres single sur kind en < 5 min depuis un cluster vide. | Déc. 2026 |
| **M2 · Sortie (niveau 1)** | `nlk export/import`, bundle signé, réplication Postgres/Redis/S3, `exit plan/cutover/verify/rollback`. Job CI bloquant sur deux clusters kind. | Migration d'un projet de A vers B avec < 10 s de coupure d'écriture, en CI, à chaque commit sur `main`. | Fév. 2027 |
| **M3 · Bêta hébergée** | Cloud NoLockIn fr-par (Scaleway Kapsule, région Paris), Dex + GitHub/Google, metering + `nlk usage`, facturation Stripe en mode test, console web v1. | 20 projets externes en production, facture recalculée manuellement = facture émise sur 3 mois. | Mai 2027 |
| **M4 · GA** | Grille de prix publique, CGU avec les engagements de sortie, page de statut, support Business, add-ons `ha`. | 99,9 % de disponibilité control plane sur 90 jours de bêta, audit de sécurité externe publié. | Sept. 2027 |
| **M5 · Élargissement** | Deuxième région européenne (annoncée, jamais imposée : un projet ne change pas de région sans action de son owner), scale-to-zero, Tempo par défaut, External Secrets, `isolation: dedicated-nodes`, multi-cluster self-hosted (un control plane, N clusters). | Défini à M4 en fonction des retours. | 2028 |

## Hors roadmap tant que non demandé

- FaaS / fonctions.
- Runtimes non conteneurisés (WASM, VM).
- Marketplace d'add-ons tiers.
- Une console qui ferait quelque chose que la CLI ne fait pas.

## Comment on décide

- Une fonctionnalité entre dans la roadmap si elle a un chemin d'export documenté.
- Une fonctionnalité qui n'existerait que sur le cloud hébergé est refusée.
- Les choix structurants passent par un ADR dans `docs/architecture/adr/`.
