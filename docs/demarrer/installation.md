# Installation

Vous avez besoin de trois choses : la CLI `nlk`, un compte sur un **contexte** (le cloud
NoLockIn ou une installation à vous), et un dépôt Git contenant une application qui écoute
sur un port.

## Prérequis

- Un dépôt sur GitHub ou GitLab. Le déploiement par défaut se déclenche au push, NoLockIn a donc besoin d'un webhook et d'une deploy key, que `nlk init` crée pour vous.
- Une application qui écoute sur le port indiqué par la variable `PORT`, ou un port fixe que vous déclarerez. Node, Python, Go, Java, Ruby, PHP, .NET sont détectés par les buildpacks. Sinon, un `Dockerfile`.
- Sur le cloud NoLockIn : un compte, créé au premier `nlk login`. Aucune carte bancaire n'est demandée sous les seuils offerts.
- Sur votre cluster : une installation NoLockIn ([guide](../guides/self-hosting.md)) et son URL d'API.

## Installer la CLI

```bash
# macOS et Linux
curl -fsSL https://get.nolockin.io | sh

# Homebrew
brew install nolockin/tap/nlk
```

Windows : téléchargez le binaire depuis la page des releases GitHub et placez-le dans votre
`PATH`. `nlk` est un binaire Go statique, sans dépendance.

```bash
nlk version
# nlk 0.9.4 (darwin/arm64)
```

## Se connecter

```bash
nlk login
```

Ouvre votre navigateur pour une authentification OIDC. Sur le cloud NoLockIn : GitHub, Google
ou lien magique par e-mail. Sur votre installation : votre fournisseur d'identité. Le jeton
est stocké dans `~/.config/nolockin/config.yaml`.

## Comprendre les contextes

Un contexte est un pointeur vers une plateforme NoLockIn : une URL d'API et une identité.
Le contexte `hosted` est le cloud NoLockIn ; il existe par défaut. Tout autre contexte est
un cluster à vous.

```bash
nlk context list
#   NAME         SERVER                                  USER
# * hosted       https://api.nolockin.cloud              alice@acme.com
#   mon-cluster  https://api.nlk.infra.acme.internal     alice@acme.com

nlk context add mon-cluster --server https://api.nlk.infra.acme.internal
nlk login --context mon-cluster
nlk context use mon-cluster
```

Toutes les commandes s'exécutent contre le contexte courant. `--context <nom>` le surcharge
pour une commande. Le même manifeste, la même CLI, la même console fonctionnent sur tous les
contextes : c'est ce qui rend la [sortie](../guides/sortie.md) triviale.

## Jetons pour la CI

Pour un pipeline qui appelle `nlk` (par exemple `nlk deploy --env prod --ref $TAG` après vos
tests), créez un jeton machine scopé à un projet :

```bash
nlk token create --project acme-prod --role developer --ttl 90d
```

Stockez-le dans les secrets de votre CI et exposez-le en `NLK_TOKEN`. Notez que le
déploiement par push **n'a pas besoin de la CLI en CI** : le webhook suffit.

## Étape suivante

[Première application](premiere-app.md) : de `nlk init` à une URL en ligne.
