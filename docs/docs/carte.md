# Carte

Les cartes du site (projets, associations) utilisent un **fond de carte** tiré d'OpenStreetMap, hébergé par le site lui-même. Il est **mis à jour automatiquement** : les nouvelles rues, places ou bâtiments y apparaissent sans intervention.

## Réglages

Dans la barre latérale, ouvrez **Paramètres** puis **Carte**.

| Champ | Description |
|---|---|
| **Mettre à jour la carte automatiquement** | Décochez pour garder le fond de carte actuel |
| **Intervalle de mise à jour (jours)** | 30 par défaut : les rues changent lentement, une fois par mois suffit. Chaque mise à jour télécharge 35 à 60 Mo selon le territoire |

La partie **État** indique la version des données, la date de la dernière mise à jour, celle de la dernière vérification et, en cas d'échec, l'erreur rencontrée. Une mise à jour qui échoue garde la carte actuelle et sera retentée à l'intervalle suivant.

**Mettre à jour la carte maintenant** lance une mise à jour tout de suite, sans attendre l'intervalle (quelques minutes). Enregistrez d'abord vos modifications des réglages : elles seraient perdues.

La vérification automatique a lieu chaque nuit, vers 4 h 30 : si l'intervalle est écoulé et qu'OpenStreetMap a publié des données plus récentes, la nouvelle carte remplace l'ancienne.

## Territoire

Le **territoire** est la zone couverte par le site : son contour est tracé sur les cartes, et le fond de carte couvre ses alentours. Ouvrez **Paramètres** puis **Territoire**.

| Champ | Description |
|---|---|
| **Nom** | Le nom affiché seul, par exemple « 7e arrondissement de Marseille » |
| **Nom dans une phrase** | Complète « Les projets situés… », par exemple « dans le 7e arrondissement de Marseille » |
| **Ville** | Les adresses (inscription, associations) sont recherchées dans cette ville |
| **Code INSEE de la ville** | Le code officiel de la commune, à ne pas confondre avec le code postal |
| **Codes postaux locaux** | Les statistiques de participation comptent par défaut les habitants ayant ces codes postaux |

Le **contour** est défini à l'installation du site, d'après les limites officielles de la commune ou de l'arrondissement. Pour le changer, contactez le support : le fond de carte est alors téléchargé à nouveau pour la nouvelle zone.
