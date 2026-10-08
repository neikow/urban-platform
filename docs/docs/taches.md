# Tâches

Certaines opérations tournent **en arrière-plan** : envoi des emails, clôture des votes, rappels d'événements, mise à jour de la [carte](carte.md), rattachement des habitants aux [associations](associations.md)… La page **Tâches** montre ce qui tourne et ce qui a tourné. Elle est réservée aux **administrateurs**.

Dans la barre latérale, ouvrez **Paramètres** puis **Tâches**. La page se met à jour toute seule toutes les quelques secondes (en pause quand l'onglet est en arrière-plan).

## Lancer maintenant

| Bouton | Effet |
|---|---|
| **Mettre à jour la carte** | Télécharge les dernières données OpenStreetMap (environ 35 Mo) |
| **Rattacher les habitants aux associations** | Recalcule l'association de chaque habitant ayant une adresse |
| **Clore les votes échus** | Clôt les votes dont la date de fin est passée et envoie leurs résultats |

Une tâche déjà en cours n'est pas relancée.

## En cours et en attente

Le nombre de **workers** (les processus qui exécutent les tâches) en ligne, le nombre de tâches en attente, et la liste des tâches en cours, réservées ou planifiées.

**Aucun worker ne répond** signifie que les tâches de fond ne tournent plus : plus d'emails, plus de clôture automatique des votes. Prévenez la personne qui gère le serveur.

## Exécutions récentes

Les 50 dernières exécutions, avec leur statut (**en cours**, **réussie**, **échouée**), leur durée et leur résultat ou leur erreur. L'historique est conservé 30 jours.
