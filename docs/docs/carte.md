# Carte

Les cartes du site (projets, associations) utilisent un **fond de carte** tiré d'OpenStreetMap, hébergé par le site lui-même. Il est **mis à jour automatiquement** : les nouvelles rues, places ou bâtiments y apparaissent sans intervention.

## Réglages

Dans la barre latérale, ouvrez **Paramètres** puis **Carte**.

| Champ | Description |
|---|---|
| **Mettre à jour la carte automatiquement** | Décochez pour garder le fond de carte actuel |
| **Intervalle de mise à jour (jours)** | 30 par défaut : les rues changent lentement, une fois par mois suffit. Chaque mise à jour télécharge environ 35 Mo |

La partie **État** indique la version des données, la date de la dernière mise à jour, celle de la dernière vérification et, en cas d'échec, l'erreur rencontrée. Une mise à jour qui échoue garde la carte actuelle et sera retentée à l'intervalle suivant.

**Mettre à jour la carte maintenant** lance une mise à jour tout de suite, sans attendre l'intervalle (quelques minutes). Enregistrez d'abord vos modifications des réglages : elles seraient perdues.

La vérification automatique a lieu chaque nuit, vers 4 h 30 : si l'intervalle est écoulé et qu'OpenStreetMap a publié des données plus récentes, la nouvelle carte remplace l'ancienne.
