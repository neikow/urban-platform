# Transfert de contenu

Copie le contenu d'un site à un autre, par exemple de la **production** vers la **préproduction** : les projets, les événements, les fiches « Informations utiles », la page d'accueil, et les images et documents qu'ils utilisent. Réservé aux **superutilisateurs**.

Dans la barre latérale, ouvrez **Paramètres** puis **Transfert de contenu**.

## Copier la production vers la préproduction

1. Sur la **production**, cliquez sur **Préparer une archive**. L'export tourne en arrière-plan ; la page se met à jour toute seule. Une fois terminé, cliquez sur **Télécharger**.
2. Sur la **préproduction**, choisissez l'archive, puis ce qu'il faut faire des pages et médias qui existent déjà :
    - **Remplacer les pages et médias existants** : une page qui a la même adresse (le même slug, sous la même page parente) est mise à jour, la page d'accueil aussi ; les images et documents gardent leur numéro et sont remplacés. Relancer le même import ne crée pas de doublons.
    - **Créer de nouvelles pages, sans rien modifier de l'existant** : chaque page est ajoutée, avec une adresse libre (`mon-projet-2` si `mon-projet` existe) ; la page d'accueil, unique, n'est pas touchée ; une image ou un document déjà présent à l'identique est réutilisé, sinon il est ajouté, et les pages importées pointent vers lui.
3. Cliquez sur **Importer**. L'archive est vérifiée tout de suite (une archive refusée l'est avant de démarrer), puis l'import tourne en arrière-plan, en une seule fois : en cas d'erreur, rien n'est importé. Le résultat s'affiche dans **Transferts récents**.

Les archives sont supprimées au bout de **7 jours**. Chaque export, téléchargement et import est inscrit au [journal d'activité](journal.md).

## Sécurité

- **Superutilisateurs seulement**, y compris pour télécharger une archive. Les archives ne sont jamais accessibles par une adresse publique.
- **Pas d'import en production** : l'import y est désactivé (variable `CONTENT_IMPORT_ENABLED`), pour qu'une archive de préproduction ne puisse pas écraser le site public.
- **Signature** : avec la même clé `CONTENT_TRANSFER_KEY` sur les deux sites, chaque archive est signée à l'export, et l'import refuse une archive non signée, signée par un autre site, ou modifiée depuis. Chaque fichier est aussi vérifié par son empreinte. Sans clé, la page l'indique.
- **Contenu limité** : seuls ces types de pages, sous leurs pages parentes habituelles, et les formats d'images et de documents acceptés par le site peuvent être importés ; une archive trop volumineuse ou mal formée est refusée.

## Configuration (équipe technique)

| Variable | Valeur |
|---|---|
| `CONTENT_TRANSFER_KEY` | Une longue valeur aléatoire, **identique** sur la production et la préproduction (par exemple `openssl rand -hex 32`) |
| `CONTENT_IMPORT_ENABLED` | Vide par défaut : désactivé si `ENVIRONMENT=production`, activé ailleurs |

Les archives jusqu'à 2 Go sont acceptées. En ligne de commande : `manage.py export_content` et `manage.py import_content archive.zip --mode replace|create`.
