# Environnements : staging et production

Un environnement est une déclinaison de votre application : un projet Kubernetes à lui, un
overlay de configuration, une politique de release. Staging et production vivent **dans le
même fichier**, et la production ne se déploie jamais par accident.

## Le modèle en trois règles

1. **Le fichier déclare la politique, pas la version.** `nolockin.yaml` dit ce que chaque environnement suit et comment il sort. Le digest déployé en production n'y est jamais écrit : il vit dans le manifest store, historisé, visible avec `nlk releases`.
2. **Un environnement suit une branche, ou ne suit rien.** `track: main` déclenche une release à chaque push. Un environnement sans `track` ne reçoit que des **promotions** explicites.
3. **Promouvoir ne reconstruit pas.** `nlk promote staging prod` prend le digest exact validé en staging et le rend avec l'overlay de production.

## Déclarer deux environnements

Depuis un manifeste à un seul environnement, `nlk init --environments staging,prod` réécrit
le fichier. Ou à la main :

```yaml
apiVersion: nolockin.io/v1
kind: App
metadata:
  name: shop-api
spec:                              # base commune
  source: { git: https://github.com/acme/shop-api }
  services:
    - name: web
      port: 8080
      resources: { cpu: 500m, memory: 512Mi }
  addons:
    - { name: db, type: postgres, version: "16" }
  env:
    DATABASE_URL: { fromAddon: db, key: url }
    STRIPE_KEY: { fromSecret: stripe, key: secret_key }

environments:
  staging:
    project: acme-staging
    track: main                    # chaque push sur main → release staging
    services:
      web: { scale: { min: 1, max: 2 } }
    addons:
      db: { plan: single, storage: 5Gi }

  prod:
    project: acme-prod             # pas de track : promotions seulement
    deploy:
      approval: owner              # un owner approuve chaque release
      strategy: canary             # 10 % → 50 % → 100 %, rollback si erreurs
    services:
      web:
        scale: { min: 3, max: 20 }
        routes: [{ host: api.acme.com }]
    addons:
      db: { plan: ha, storage: 50Gi }
```

Retirez `metadata.project` : avec `environments`, chaque environnement porte le sien. Les
règles de fusion entre la base et les overlays sont dans la
[référence](../reference/manifeste.md#règles-de-fusion). Chaque add-on est **par
environnement** : la base de staging et celle de production sont deux clusters distincts.

## Les secrets, par environnement

Les secrets vivent dans le projet de l'environnement, jamais dans le fichier :

```bash
nlk secret set stripe secret_key=sk_test_... --env staging
nlk secret set stripe secret_key=sk_live_... --env prod
```

C'est la place naturelle de ce qui diffère entre environnements et ne doit pas être dans Git.
Détails dans le [guide des secrets](../guides/secrets.md).

## Une journée type

```bash
git push origin main
# → release staging/#118, automatique, en ligne sur https://shop-api-acme-staging.nolockin.app

nlk releases --env staging
# #118  live      a1b2c3d  3 commits  1m52s  push

nlk promote staging prod
# prod/#42  pending-approval
# 7 commits depuis prod/#41 · 1 changement de manifeste (web.scale.max 10 → 20)

nlk releases approve prod/#42        # réservé aux owners du projet acme-prod
# canary 10 %  errorRate 0.1 %  p95 302 ms
# canary 50 %  errorRate 0.2 %  p95 310 ms
# canary 100 % · live · tag nlk/prod → a1b2c3d
```

Si l'analyse canari dépasse les seuils, le rollout revient seul à la release précédente et
vous êtes notifié. Sinon :

```bash
nlk rollback --env prod              # nouvelle release avec le digest de prod/#41
```

## Où se trouve quoi

| Vous cherchez | Commande |
|---|---|
| Ce qui est en production | `nlk releases --env prod` ou `nlk status --env prod` |
| Le contenu d'une release : commits, diff du manifeste, digest | `nlk releases show prod/#42` |
| Le manifeste effectif d'un environnement après fusion | `nlk manifest show --env prod` |
| Le YAML Kubernetes que ça produit | `nlk render --env prod` |
| Les releases en attente d'approbation | `nlk releases --env prod --pending` |

## Bonnes pratiques

- **Ne donnez jamais de `track` à la production.** Une production qui suit `main` se déploie à chaque merge, y compris le vendredi à 18 h. `freeze` existe, mais l'absence de `track` est plus simple.
- **Laissez la CI décider de ce qui entre en staging** avec `deploy.requireChecks: true` : un commit rouge ne produit pas de release.
- **Un changement de configuration prod suit le même chemin que le code** : commit sur `main`, release staging, promotion. Pas de raccourci, sauf urgence avec `nlk scale --env prod`, qui applique tout de suite et ouvre la PR.
- **Prévisualisez les PR** en staging avec `deploy.previews.enabled: true` : une instance par pull request, détruite au merge.

Pour aller plus loin : [Déployer et livrer](../guides/deployer.md).
