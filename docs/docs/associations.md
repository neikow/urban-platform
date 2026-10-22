# Associations de quartier

Chaque habitant est rattaché à une **association de quartier** (CIQ…). À l'inscription ou dans son profil, il **choisit son CIQ** dans une liste. Dès qu'il choisit son adresse dans les suggestions, la liste se classe du plus proche au plus loin, avec la distance, et **le CIQ le plus proche est sélectionné** ; l'habitant peut en choisir un autre.

S'il laisse « Le plus proche de mon adresse », il est rattaché :

1. au CIQ dont le **secteur** (s'il est dessiné) contient son adresse ;
2. sinon, au CIQ dont l'**adresse** (le siège) est la plus proche.

Un CIQ sans adresse localisée n'est jamais proposé comme le plus proche, mais reste dans la liste.

L'habitant peut aussi cocher **« Je ne souhaite pas adhérer à un CIQ »** : il n'est alors rattaché à aucun CIQ, même plus tard (le rattachement en arrière-plan respecte ce choix). Une adhésion payée dans ce cas n'a pas de CIQ.

## Modifier une association

Dans la barre latérale, ouvrez **Paramètres** puis **Associations de quartier**.

| Champ | Description |
|---|---|
| **Nom** | Le nom de l'association, tel qu'affiché aux habitants |
| **Code** | Le numéro dans l'annuaire de la Confédération (par exemple 712). Sert à l'import |
| **Responsable** | Un compte de l'équipe : **rédacteur**, **modérateur** ou **administrateur**. Il voit les adhérents du CIQ (liste des adhésions et tableau de bord), sans pouvoir les modifier |
| **Adresse** | Le siège ou le local. Tapez quelques lettres et choisissez l'adresse dans la liste. Sert à trouver le CIQ le plus proche des habitants |
| **Secteur** | La zone couverte (voir ci-dessous) |
| **Email de contact**, **Numéro de téléphone**, **Site web** | Les coordonnées montrées aux habitants rattachés |

## Dessiner le secteur

- Cliquez sur l'icône **polygone** (ou rectangle), puis cliquez point par point sur la carte. Terminez en cliquant sur le premier point.
- Les secteurs des **autres associations** apparaissent en **gris**, avec leur nom au survol. Les nouveaux points **s'accrochent à leurs bords** : deux secteurs voisins se touchent sans se chevaucher ni laisser de trou.
- **Rechercher une adresse** au-dessus de la carte pour s'y rendre directement.
- Les outils de la barre permettent de modifier, déplacer ou supprimer le secteur. Un nouveau secteur remplace l'ancien.

Après l'enregistrement d'un secteur ou d'une adresse nouveaux ou modifiés, les habitants qui n'ont pas choisi leur CIQ sont rattachés de nouveau, en arrière-plan (quelques secondes à quelques minutes selon leur nombre). Ceux qui ont choisi leur CIQ le gardent. Supprimer une association rattache ses habitants au CIQ le plus proche, y compris ceux qui l'avaient choisie.

## Importer les CIQ depuis l'annuaire

Les CIQ d'un arrondissement s'importent depuis une copie CSV de l'annuaire de la Confédération (colonnes `code`, `name`, `address`, `contact_email`, `contact_phone`, `website` ; seules `code` et `name` sont obligatoires), encodée en UTF-8.

1. **Paramètres › Comités d'intérêt de quartier**, bouton **Import** en haut de la liste (administrateurs).
2. Choisissez le fichier et la **fédération** : 7 importe les codes 701 à 799 (700 est la fédération elle-même). Cliquez sur **Aperçu**.
3. L'aperçu liste les CIQ qui seraient créés ou mis à jour, les lignes refusées (email invalide…) et les CIQ dont l'adresse n'a pas été localisée. Rien n'est encore enregistré.
4. Cliquez sur **Importer ces CIQ** pour confirmer.

Relancer l'import met à jour les CIQ existants, retrouvés par leur code (ou par leur nom pour ceux créés à la main). Les CIQ sans adresse localisée ne sont jamais proposés comme le plus proche : complétez leur adresse dans l'administration. Le fichier n'est pas conservé sur le site (il contient des coordonnées personnelles).

L'équipe technique peut faire de même en ligne de commande (`--dry-run` pour l'aperçu) :

```
python manage.py import_associations annuaire.csv --federation 7
```

**Adresses.** Les adresses viennent de la **Base Adresse Nationale**, limitées à Marseille. Si le service ne répond pas, l'adresse est enregistrée telle quelle et sera localisée au prochain enregistrement.
