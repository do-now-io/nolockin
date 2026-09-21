# Site vitrine NoLockIn

Deux parties, toutes deux statiques, sans dépendance :

- `index.html` : la page vitrine, tout inclus (CSS, JS, SVG).
- `docs/` : la documentation, **générée** depuis les Markdown du dépôt (`docs/`, `examples/`,
  `charts/nolockin/README.md`, `README.md`). Ne pas éditer `site/docs/` à la main.

```bash
python3 site/build-docs.py           # régénère site/docs/ après toute modification des Markdown
cd site && python3 -m http.server 8080
# http://localhost:8080          vitrine
# http://localhost:8080/docs/    documentation
```

Le générateur (`build-docs.py`, Python standard, zéro dépendance) produit une page HTML par
document avec barre latérale, sommaire de page, recherche plein texte côté client, pagination,
thème clair/sombre, diagrammes Mermaid, et un `search-index.json`. La navigation est déclarée
dans la constante `NAV` du script : ajouter un Markdown = ajouter une ligne.

`python3 site/build-docs.py --bundle fichier.html` produit la même documentation en un seul
fichier à navigation par hash, utile pour un aperçu hors serveur.

Déployable tel quel sur n'importe quel hébergement statique (ou… comme une app NoLockIn
avec `build.type: dockerfile` et une image nginx).

## Publication automatique

Le Markdown est la source versionnée ; `site/docs/` est **généré** et ignoré par Git. Le
workflow [`.github/workflows/site.yml`](../.github/workflows/site.yml) fait le reste à chaque
push sur `main` qui touche `docs/`, `examples/`, le chart ou `site/` :

1. `python3 site/build-docs.py` : régénère la documentation.
2. `python3 site/check-docs.py` : échoue si un lien interne, une ancre ou un asset est cassé.
3. Assemble `public/` (vitrine + `docs/` + `404.html`) et publie.

Sur une pull request, seules les étapes 1 et 2 tournent : une doc cassée bloque le merge.

### Cible GitHub Pages (par défaut)

Dans le dépôt GitHub : *Settings → Pages → Build and deployment → Source : GitHub Actions*.
Le site est servi sur `https://<org>.github.io/<repo>/`, la doc sur `/docs/`. Tous les liens
du site sont relatifs, il fonctionne sous n'importe quel préfixe. Pour un domaine personnalisé
(`nolockin.io`), renseignez-le dans les réglages Pages et ajoutez un fichier `site/CNAME`
contenant le domaine ; le workflow le copiera avec le reste.

### Cible Scaleway Object Storage (souveraine, fr-par)

Pour héberger le site au même endroit que la plateforme :

```bash
scw object bucket create name=nolockin-site region=fr-par
aws s3 website s3://nolockin-site --index-document index.html --error-document 404.html \
  --endpoint-url https://s3.fr-par.scw.cloud
```

Puis, dans le dépôt GitHub : variable `SCW_BUCKET=nolockin-site`, secrets `SCW_ACCESS_KEY` et
`SCW_SECRET_KEY` (une clé API scopée au bucket). Le job `deploy-scaleway` se déclenche dès que
la variable existe et synchronise `public/` vers le bucket. Le site répond sur
`https://nolockin-site.s3-website.fr-par.scw.cloud`, à mettre derrière un CNAME ou Scaleway
Edge Services pour le domaine et le TLS.

### Plus tard : dogfooding

Quand la plateforme existera, le site se déploiera comme n'importe quelle app NoLockIn : un
`Dockerfile` nginx dans `site/`, un `nolockin.yaml`, un push.

### En local

```bash
python3 site/build-docs.py && python3 site/check-docs.py
cd site && python3 -m http.server 8080
```
