# Questions fréquentes

## Est-ce vraiment gratuit sur mon cluster ?

Oui. Le chart Helm, l'opérateur, la CLI, la console, le metering : tout est Apache-2.0, sans
licence, sans clé, sans compteur. Ce qui coûte, c'est votre cluster, et si vous le voulez, un
contrat de support. Aucune fonctionnalité n'est réservée au cloud hébergé, et l'ADR-0005
explique pourquoi on ne changera pas de licence.

## Que se passe-t-il si NoLockIn disparaît ?

Vos apps tournent sur Kubernetes standard, rendues par un opérateur open source que vous
pouvez continuer à faire tourner. Vos images sont des images OCI, vos bases des Postgres,
vos fichiers des objets S3. `nlk render` produit du YAML que `kubectl apply` comprend sans
NoLockIn. Et sur le cloud hébergé, nos conditions imposent 12 mois de préavis avec assistance
à la migration incluse.

## Faut-il connaître Kubernetes ?

Non pour l'utiliser : vous écrivez `nolockin.yaml`, vingt lignes, et vous poussez. Oui pour
l'héberger vous-même : il faut un cluster et savoir le maintenir, mais pas plus que pour
n'importe quel logiciel qui tourne dessus.

## Dois-je installer la CLI pour déployer ?

Pour le premier `nlk init`, oui. Ensuite, non : le déploiement par défaut est un `git push`,
déclenché par un webhook. La CLI sert à regarder (`status`, `logs`), à promouvoir, à gérer
les secrets et les domaines. Tout ce qu'elle fait, la console le fait aussi.

## Comment la facture est-elle calculée ?

À la seconde, sur quatre choses : le CPU réellement consommé, la mémoire réellement utilisée,
le stockage provisionné, le trafic sortant. Les requêtes Prometheus qui produisent ces
chiffres sont publiées dans le dépôt, et `nlk usage explain` les affiche ligne par ligne.
Si la facture et le dashboard divergent, la facture a tort. Il n'y a ni siège, ni plan, ni
minimum, ni prix par requête.

## Puis-je partir avec une facture impayée ?

Oui. Les endpoints d'export ne vérifient pas l'état du compte, c'est testé. On ne retient
pas les données de quelqu'un pour se faire payer.

## Où sont mes données ?

Aujourd'hui dans une seule région, `fr-par` : un cluster Kubernetes Scaleway à Paris,
opéré par une équipe française, sous droit français. Registry, bases, sauvegardes, logs et
métriques ne quittent pas cette région. Une deuxième région européenne viendra ; elle sera
annoncée, jamais imposée.

## Quelle différence avec Heroku, Render ou Fly.io ?

L'expérience de déploiement est comparable. La différence est ce qui se passe le jour où vous
voulez partir : chez eux, une réécriture ; chez nous, quatre commandes vers votre cluster,
sans frais de sortie, avec le protocole testé en CI. Et le prix : à la seconde, sans plan.

## Quelle différence avec Coolify, Dokploy ou CapRover ?

Ce sont d'excellents PaaS open source à auto-héberger, plutôt orientés serveur unique ou
Docker. NoLockIn est construit sur Kubernetes avec ArgoCD, Prometheus, CloudNativePG, pour des
équipes qui veulent de la haute disponibilité, du GitOps et des environnements, et qui
veulent pouvoir passer du cloud hébergé à leur cluster sans rien changer.

## Puis-je utiliser mon propre dépôt Git de déploiement, ma propre registry ?

Oui. `nlk project set --manifest-repo` pointe le manifest store sur un dépôt à vous, et les
promotions deviennent des PR. `build.registry.mode: external` branche votre Harbor, ECR ou
GAR. NoLockIn est fait pour s'insérer dans ce que vous avez.

## Y a-t-il un niveau gratuit ?

Pas de plan gratuit, mais des seuils offerts chaque mois : 100 GiB de trafic sortant, 300
minutes de build, une adresse IP publique. Une petite app à un réplica coûte quelques euros
par mois, et un projet vide coûte zéro.

## Comment sont gérés les secrets ?

Hors de Git, par environnement, chiffrés au repos, référencés depuis le manifeste. Vous
pouvez brancher votre Vault ou votre gestionnaire de secrets cloud. Nous étudions aussi le
chiffrement dans Git avec SOPS. Détails dans le [guide des secrets](../guides/secrets.md).

## Le projet est-il utilisable aujourd'hui ?

Nous sommes au jalon M0 : la spécification, que vous lisez. La CLI et le chart arrivent au
jalon M1, le protocole de sortie au M2, la bêta hébergée au M3. La [roadmap](roadmap.md)
donne les critères de sortie de chaque étape. Cette documentation est le contrat que le code
devra respecter.
