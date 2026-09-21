# Première application

Cinq minutes, de zéro à une application en ligne avec TLS, autoscaling, Grafana, logs et
ArgoCD. Aucun fichier Kubernetes à écrire.

## 1. Générer le manifeste

Dans le dossier de votre application :

```bash
nlk init
```

`nlk init` :

- détecte le langage et le port (ou lit un `Procfile` ou un `docker-compose.yml` existant) ;
- vous demande le projet cible, ou le crée (`demo` ci-dessous) ;
- crée la deploy key et le webhook sur votre dépôt ;
- écrit `nolockin.yaml`.

```yaml
apiVersion: nolockin.io/v1
kind: App
metadata:
  name: hello
  project: demo
spec:
  source:
    git: https://github.com/acme/hello
  services:
    - name: web
      port: 8080
```

C'est le [manifeste minimal](../../examples/minimal.yaml). Tout le reste a une valeur par
défaut pensée pour la production : 2 réplicas, autoscaling jusqu'à 10, health check sur `/`,
limites de ressources, TLS, anti-affinité entre nœuds. La [référence](../reference/manifeste.md)
liste chaque champ.

## 2. Pousser

```bash
git add nolockin.yaml
git commit -m "Ajoute le manifeste NoLockIn"
git push origin main
```

Le déploiement par défaut, c'est le push. Suivez-le :

```bash
nlk status --watch
# ▸ push       a1b2c3d → demo/hello (track: main)
# ▸ checks     aucun check déclaré, on continue
# ▸ build      buildpacks · node 22 · 1m12s
# ✔ image      ghcr.io/demo/hello@sha256:9e0f…
# ▸ release    default/#1 → manifest store → argocd Synced
# ▸ rollout    web 0/2 → 1/2 → 2/2
# ✔ live       https://hello-demo.nolockin.app   1m41s
```

Le premier build prend une à deux minutes. Les suivants profitent du cache : une trentaine de
secondes pour un changement de code, moins de trente secondes pour un changement de manifeste
seul, qui ne reconstruit pas l'image.

## 3. Regarder ce qui tourne

```bash
nlk status
# hello · demo · release default/#1 · live depuis 2 min
# SERVICE  READY  CPU        MEM       IMAGE
# web      2/2    0.04 vCPU  71 MiB    sha256:9e0f…
# ROUTES   https://hello-demo.nolockin.app   TLS ok

nlk logs -f
nlk ps
nlk open grafana      # le dashboard de l'app : RPS, latence, erreurs, CPU, mémoire, réplicas
nlk open argocd       # l'arbre des ressources : Deployment, ReplicaSet, Pods, Service, HTTPRoute
```

Dans ArgoCD vous voyez exactement ce que `nlk render` produit : des objets Kubernetes
standards, rien d'autre. Dans Grafana, le dashboard « App » est provisionné, et le dashboard
« Facture » montre déjà la consommation du mois.

## 4. Changer quelque chose

Modifiez votre code, poussez : nouvelle release. Modifiez le manifeste, poussez : nouvelle
release sans rebuild. Ajoutez une base de données :

```yaml
spec:
  addons:
    - name: db
      type: postgres
      version: "16"
  env:
    DATABASE_URL: { fromAddon: db, key: url }
```

Au push suivant, un cluster Postgres est créé et son URL injectée. `nlk addon psql db` ouvre
une session.

## Ce que vous avez maintenant

| Vous avez | Sans avoir configuré |
|---|---|
| Une URL HTTPS avec un certificat Let's Encrypt renouvelé automatiquement | cert-manager, Gateway API |
| 2 à 10 réplicas selon le CPU, répartis sur plusieurs nœuds | HPA, PodDisruptionBudget, topology spread |
| Health checks, redémarrage automatique, limites de ressources | probes, LimitRange, ResourceQuota |
| Un dashboard Grafana, des logs interrogeables, quatre alertes | Prometheus, Loki, Alertmanager |
| L'arbre des ressources et l'historique des releases dans ArgoCD | ArgoCD, un dépôt Git de déploiement |
| Une facture au centime, recalculable | recording rules, metering |

## Étapes suivantes

- [Environnements](environnements.md) : un staging qui suit `main`, une production qui reçoit des promotions approuvées.
- [Domaines et TLS](../guides/domaines.md) : `api.acme.com` à la place du sous-domaine fourni.
- [Secrets](../guides/secrets.md) : une clé Stripe sans la mettre dans Git.
