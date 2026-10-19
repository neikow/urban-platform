# Paiement des adhésions (HelloAsso)

Les adhésions se paient sur **HelloAsso**, sur le compte de la Fédération des CIQ. Cette page s'adresse à l'équipe technique.

## Configuration

Dans le back-office HelloAsso de la Fédération, **Mon compte › Intégrations et API** :

1. Récupérez le **client ID** et le **client secret** de l'API. Ils doivent avoir le droit **Checkout**.
2. Renseignez l'**URL de notification** : `https://<le site>/adhesion/notification/`.

Puis, dans l'environnement du serveur :

| Variable | Valeur |
|---|---|
| `HELLOASSO_CLIENT_ID` | Le client ID |
| `HELLOASSO_CLIENT_SECRET` | Le client secret |
| `HELLOASSO_ORGANIZATION_SLUG` | L'identifiant de la Fédération dans ses adresses HelloAsso (`helloasso.com/associations/<slug>`) |
| `HELLOASSO_API_URL` | `https://api.helloasso.com`, ou `https://api.helloasso-sandbox.com` pour les essais |
| `MEMBERSHIP_FEE_CENTS` | Le montant en centimes (`1000` par défaut, soit 10 €) |

Tant que ces variables manquent, la page d'adhésion indique que le paiement en ligne n'est pas encore ouvert.

## Déroulement

1. L'habitant valide son adresse et son CIQ : le site enregistre un **paiement en attente** et l'envoie sur la page de paiement HelloAsso (valable 15 minutes).
2. Après le paiement, HelloAsso le renvoie sur le site et envoie une **notification**.
3. Dans les deux cas, le site **redemande le paiement à HelloAsso** : ni le retour ni la notification ne suffisent seuls. Une fois le paiement confirmé, l'adhésion est enregistrée (une seule fois) et un email de confirmation part.
4. Toutes les 15 minutes, une tâche vérifie les paiements en attente, au cas où une notification se serait perdue. Sans paiement au bout de 45 minutes, le paiement passe en **abandonné** ; il est encore enregistré si HelloAsso le confirme plus tard.

Avant d'ouvrir, activez **Réserver la participation aux adhérents** dans les [fonctionnalités](fonctionnalites.md) : tous les comptes, y compris les existants, devront alors adhérer pour voter.
