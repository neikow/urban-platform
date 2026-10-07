import html
import re

from django.db import migrations

# The cookies policy only lists the cookies the site actually sets (session, CSRF,
# flash messages, dismissed announcement). The previous text described analytics
# cookies and a consent banner that never existed.

_OLD_CONTENT = """\
<h2>Préambule</h2>
<p>La présente politique vous informe sur l’utilisation des cookies et technologies similaires sur notre plateforme de co-construction urbaine. Ces outils nous permettent d'améliorer votre expérience et d'analyser l'utilisation de nos services.</p>
<h2>1. Qu'est-ce qu'un cookie ?</h2>
<p>Un cookie est un petit fichier texte déposé sur votre terminal (ordinateur, tablette ou smartphone) lors de la visite d'un site. Il permet au site de reconnaître votre navigateur et de mémoriser certaines informations techniques ou vos préférences.</p>
<h2>2. Les types de cookies que nous utilisons</h2>
<p>Nous utilisons trois catégories de cookies :</p>
<ul>
<li><strong>Cookies techniques (Indispensables) :</strong> Ils permettent le bon fonctionnement du site (session utilisateur, mémorisation du consentement, sécurité). Sans eux, le site ne peut fonctionner correctement.</li>
<li><strong>Cookies de mesure d'audience :</strong> Ils nous permettent de comprendre comment les citoyens utilisent la plateforme afin d'en améliorer l'ergonomie et la pertinence des contenus.</li>
<li><strong>Cookies de fonctionnalités :</strong> Ils servent à mémoriser vos choix, comme la langue ou la zone géographique que vous consultez sur la carte interactive.</li>
</ul>
<h2>3. Durée de conservation</h2>
<p>Les cookies ont une durée de vie limitée. La durée de conservation de nos cookies n'excède pas 13 mois après leur premier dépôt dans votre terminal. Votre choix de consentement est, quant à lui, conservé pendant 6 mois.</p>
<h2>4. Gestion de vos préférences</h2>
<p>Lors de votre première visite, un bandeau vous demande d'accepter ou de refuser les cookies non essentiels. Vous pouvez modifier vos choix à tout moment :</p>
<ul>
<li>Via notre panneau de gestion des cookies accessible en bas de chaque page.</li>
<li>Via les réglages de votre navigateur (Chrome, Firefox, Safari, Edge) qui permettent de bloquer ou de supprimer les cookies.</li>
</ul>
<h2>5. Cookies tiers</h2>
<p>Certaines fonctionnalités du site (intégration de cartes, vidéos de projets urbains) s'appuient sur des services tiers. Si vous refusez ces cookies, certaines parties interactives du site pourraient ne pas s'afficher correctement.</p>
<h2>6. Mise à jour de la politique</h2>
<p>Nous nous réservons le droit de modifier cette politique pour refléter les évolutions de nos services ou de la réglementation. Nous vous invitons à la consulter régulièrement.</p>"""

_NEW_CONTENT = """\
<h2>Préambule</h2>
<p>La présente politique vous informe sur les cookies déposés par notre plateforme de co-construction urbaine. Nous n'utilisons que des cookies strictement nécessaires au fonctionnement du site : aucun cookie de mesure d'audience, de publicité ou de réseau social n'est déposé sur votre terminal.</p>
<h2>1. Qu'est-ce qu'un cookie ?</h2>
<p>Un cookie est un petit fichier texte déposé sur votre terminal (ordinateur, tablette ou smartphone) lors de la visite d'un site. Il permet au site de reconnaître votre navigateur et de mémoriser certaines informations techniques ou vos choix.</p>
<h2>2. Les cookies que nous utilisons</h2>
<ul>
<li><strong>sessionid</strong> : maintient votre connexion lorsque vous êtes connecté à votre compte. Il est supprimé à la déconnexion et expire au plus tard après deux semaines.</li>
<li><strong>csrftoken</strong> : protège les formulaires du site (connexion, inscription, votes, idées) contre les requêtes frauduleuses émises depuis d'autres sites. Il est conservé un an.</li>
<li><strong>messages</strong> : transmet un message de confirmation ou d'erreur d'une page à la suivante (par exemple après l'enregistrement de votre profil). Il est supprimé dès que le message est affiché.</li>
<li><strong>announcement_dismissed</strong> : retient que vous avez fermé le bandeau d'annonce, afin qu'il ne s'affiche plus tant que l'annonce n'a pas changé. Il est conservé un an.</li>
</ul>
<p>Ces cookies sont déposés par notre propre site et ne sont jamais transmis à des tiers.</p>
<h2>3. Pourquoi aucun bandeau de consentement ?</h2>
<p>Les cookies strictement nécessaires au fonctionnement d'un site, ou à la fourniture d'un service que vous demandez expressément, sont exemptés de consentement (article 82 de la loi Informatique et Libertés). Comme nous n'utilisons que de tels cookies, nous n'avons pas besoin de vous demander votre accord.</p>
<h2>4. Services tiers</h2>
<p>La carte interactive et les polices de caractères sont servies directement par notre serveur : leur affichage ne dépose aucun cookie tiers. Les liens vers des sites extérieurs (par exemple OpenStreetMap) ne déposent des cookies que si vous les suivez, selon la politique propre à ces sites.</p>
<h2>5. Gestion des cookies</h2>
<p>Vous pouvez à tout moment bloquer ou supprimer les cookies depuis les réglages de votre navigateur (Chrome, Firefox, Safari, Edge). Refuser ces cookies vous empêchera toutefois de vous connecter et d'envoyer des formulaires sur la plateforme.</p>
<h2>6. Mise à jour de la politique</h2>
<p>Cette politique sera mise à jour si nous venons à utiliser de nouveaux cookies. Tout cookie non essentiel, comme un outil de mesure d'audience, ne serait alors déposé qu'avec votre accord préalable.</p>"""


def _text(content):
    """The visible text of rich text HTML, so the editor's markup changes
    (block keys, whitespace) do not hide an otherwise untouched text."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", content or ""))
    return " ".join(text.split())


def _replace_content(apps, current, replacement, fill_empty):
    """Swap `current` for `replacement` on the page and its revisions, leaving
    a text that editors have changed alone."""
    CookiesPolicyPage = apps.get_model("legal", "CookiesPolicyPage")
    Revision = apps.get_model("wagtailcore", "Revision")
    replaceable = {_text(current)} | ({""} if fill_empty else set())

    for page in CookiesPolicyPage.objects.all():
        if _text(page.content) not in replaceable:
            print(f"\n  Cookies policy page {page.pk} was edited, leaving its content as is.")
            continue
        page.content = replacement
        page.save(update_fields=["content"])

        revision_ids = {page.latest_revision_id, page.live_revision_id} - {None}
        for revision in Revision.objects.filter(pk__in=revision_ids):
            if _text(revision.content.get("content")) in replaceable:
                revision.content["content"] = replacement
                revision.save(update_fields=["content"])


def update_content(apps, schema_editor):
    _replace_content(apps, _OLD_CONTENT, _NEW_CONTENT, fill_empty=True)


def restore_content(apps, schema_editor):
    _replace_content(apps, _NEW_CONTENT, _OLD_CONTENT, fill_empty=False)


class Migration(migrations.Migration):
    dependencies = [
        ("legal", "0008_codeofconductconsent"),
        ("wagtailcore", "0096_referenceindex_referenceindex_source_object_and_more"),
    ]

    operations = [
        migrations.RunPython(update_content, restore_content),
    ]
