# Domaines et TLS

Chaque service exposé reçoit un sous-domaine `<app>-<project>.nolockin.app` avec un
certificat valide. Ce guide explique comment brancher vos propres domaines, par
environnement, et ce qui se passe au moment de quitter.

## Le sous-domaine fourni

Sans rien déclarer, un service `web` de l'app `shop-api` dans le projet `acme-staging`
répond sur `https://shop-api-acme-staging.nolockin.app`. HTTPS obligatoire, HSTS activé,
certificat Let's Encrypt renouvelé automatiquement. Ce sous-domaine reste actif en plus de
vos domaines.

## Ajouter un domaine

Dans le manifeste, dans l'overlay de l'environnement concerné :

```yaml
environments:
  prod:
    services:
      web:
        routes:
          - host: api.acme.com
          - host: www.acme.com
            redirectWWW: true          # www.acme.com → acme.com
```

Ou par la CLI, qui réécrit le manifeste et ouvre une PR :

```bash
nlk domain add api.acme.com --service web --env prod
```

## Vérifier le DNS

Un domaine à vous doit être prouvé avant de servir du trafic :

```bash
nlk domain verify api.acme.com
# Ajoutez chez votre registrar :
#   api.acme.com.          CNAME  edge.fr-par.nolockin.cloud.
#   _nolockin.api.acme.com TXT    "nlk-verify=7f3a9c…"
# En attente de propagation… ✔ vérifié (42 s)
```

Pour un apex (`acme.com`) qui n'accepte pas de CNAME, utilisez l'enregistrement `A` ou
`ALIAS` indiqué par la commande. Une fois vérifié, le certificat est émis (HTTP-01), et le
domaine répond en quelques secondes.

## Certificats

| `tls` | Comportement |
|---|---|
| `auto` (défaut) | Let's Encrypt, renouvellement automatique 30 jours avant expiration. Wildcard possible via DNS-01 si votre DNS est délégué. |
| `secret:<nom>` | Votre certificat, posé avec `nlk secret set <nom> tls_crt=@cert.pem tls_key=@key.pem`. Vous gérez le renouvellement ; une alerte part 14 jours avant expiration. |
| `off` | HTTP seul. Interdit sur `.nolockin.app`, déconseillé partout. |

## Options de route

```yaml
routes:
  - host: api.acme.com
    path: /v2                 # préfixe de chemin (défaut /)
    tls: auto
    redirectWWW: false
    rateLimit: 200/s          # par adresse IP source
```

Les timeouts par défaut sont de 30 s, la taille maximale de requête de 10 MiB. Les deux se
surchargent par route (`timeout`, `maxBodySize`).

## Un domaine par environnement

Un même hôte ne peut appartenir qu'à un environnement : `nlk validate` refuse
`api.acme.com` à la fois en staging et en production. La convention habituelle :

| Environnement | Hôte |
|---|---|
| staging | `staging-api.acme.com` |
| prod | `api.acme.com` |
| previews | `shop-api-pr-42.acme-staging.nolockin.app`, fourni |

## Au moment de quitter

Le [protocole de sortie](sortie.md) abaisse les TTL, fait répondre l'ancienne plateforme par
une redirection `307` pendant la propagation DNS, et affiche les enregistrements à modifier
chez votre registrar. NoLockIn ne modifie jamais votre DNS externe : il vous dit quoi
changer et attend.
