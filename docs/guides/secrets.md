# Secrets

Un secret n'est jamais dans `nolockin.yaml`. Le manifeste contient des **références**, les
valeurs vivent dans le projet de l'environnement, chiffrées au repos, et sont injectées dans
vos conteneurs en variables d'environnement.

## Le modèle

| Où | Quoi |
|---|---|
| `nolockin.yaml` | Des références : `{ fromSecret: stripe, key: secret_key }` |
| Le projet de l'environnement | Les valeurs, en Secret Kubernetes chiffré (etcd + KMS), une par environnement |
| Vos conteneurs | Des variables d'environnement, résolues au démarrage du pod |
| Le bundle de sortie | Les valeurs, chiffrées `age` pour la clé publique du contexte cible, jamais en clair |

Un secret est **par projet, donc par environnement**. `stripe` en staging et `stripe` en
production sont deux objets distincts, avec des valeurs différentes. C'est la place
naturelle de ce qui diffère entre environnements et n'a pas sa place dans Git.

## Créer et référencer

```bash
nlk secret set stripe secret_key=sk_live_... webhook_secret=whsec_... --env prod
nlk secret set stripe secret_key=sk_test_... webhook_secret=whsec_... --env staging
```

```yaml
spec:
  env:
    STRIPE_KEY:            { fromSecret: stripe, key: secret_key }
    STRIPE_WEBHOOK_SECRET: { fromSecret: stripe, key: webhook_secret }
```

Un secret référencé mais absent d'un environnement est un **avertissement** à la validation,
pas une erreur : vous pouvez écrire le manifeste avant de poser les valeurs. Au déploiement,
un secret manquant bloque la release avec un message explicite.

```bash
nlk secret list --env prod
# NAME    KEYS                          UPDATED
# stripe  secret_key, webhook_secret    2026-09-02 (alice@acme.com)
```

Les valeurs ne sont jamais affichées par la CLI ni par la console, et sont masquées dans les
logs et dans `nlk env`.

## Depuis un fichier

```bash
nlk secret set gcp service_account=@./sa.json --env prod       # contenu d'un fichier
nlk secret set certs tls_crt=@./tls.crt tls_key=@./tls.key --env prod
```

## Tourner un secret

```bash
nlk secret set stripe secret_key=sk_live_NEW --env prod
```

Crée une nouvelle version du secret. Les pods la voient au prochain rollout : une release
(`nlk deploy`, un push, une promotion) ou tout de suite avec `secrets.autoRollout: true`
dans le manifeste, qui redémarre les pods concernés à chaque changement.

Un secret tourné en urgence à cause d'une fuite : `nlk secret set` puis
`nlk rollback --emergency` si la release courante ne peut pas attendre, ou
`nlk restart web --env prod`.

## Jetons pour la CI et les machines

```bash
nlk token create --project acme-prod --role developer --ttl 90d
nlk token list
nlk token revoke <id>
```

Un jeton est scopé à un projet et à un rôle. `developer` peut déployer et écrire des
secrets, pas supprimer le projet ni les add-ons. Chaque appel est journalisé.

## Ce qui n'est pas un secret à gérer

- **Les identifiants d'add-ons** (`fromAddon`) sont générés par les opérateurs, tournés par eux, jamais dans Git ni dans vos mains sauf via `nlk addon psql`.
- **Les certificats TLS** des routes sont gérés par cert-manager.
- **Les deploy keys et webhooks** sont créés par `nlk init` et révocables depuis votre Git host.

## Brancher un coffre existant

Si votre organisation centralise ses secrets dans Vault, OpenBao, AWS Secrets Manager, GCP
Secret Manager ou Azure Key Vault, External Secrets Operator synchronise vers le projet :

```yaml
spec:
  secrets:
    backend: external
    external:
      provider: vault
      server: https://vault.acme.internal
      pathTemplate: "acme/{env}/{name}"
```

Le manifeste garde les mêmes références `fromSecret`. La plateforme lit le coffre, vous ne
copiez rien. La sortie ne change pas : le coffre est à vous.

## Évolution à l'étude

Nous étudions le stockage des secrets **dans le dépôt Git, chiffrés avec SOPS**, avec une
clé `age` par environnement détenue par la plateforme et des destinataires additionnels
(vos clés, un Vault Transit). Cela rendrait une release entièrement définie par un SHA,
secrets compris, et simplifierait encore la sortie. La décision fera l'objet d'un ADR ; le
modèle décrit dans cette page restera disponible.

## Règles

- Jamais de valeur littérale sensible dans `spec.env`. `nlk validate` refuse les motifs connus (`sk_live_`, `AKIA`, clés PEM).
- Un rôle `viewer` ne voit ni les noms de clés ni les valeurs. Un `developer` voit les noms.
- À la suppression d'un projet, les secrets sont détruits avec lui et listés dans l'attestation de suppression.
