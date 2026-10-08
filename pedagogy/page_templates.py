"""Ready-made "Informations utiles" cards and page (see ``core.page_templates``).

Each section says what to write in it: editors replace these instructions
with their text, and delete the sections they do not need.
"""

from django.utils.translation import gettext_lazy as _

from core.page_templates import PageTemplate, faq, rich_text
from home.blocks import SectionLayout, SectionTone
from home.page_templates import JOIN, OPEN_PROJECTS, section
from pedagogy.blocks import BLOCK_TYPE_CARD_LIST

CONCEPT = PageTemplate(
    slug="concept",
    name=_("Explain a notion"),
    description=_(
        "A notion of urban planning in plain words, e.g. the PLUi or a building permit: "
        "what it is, why it matters, how it works."
    ),
    blocks=(
        rich_text(
            "<h2>En une phrase</h2>"
            "<p>Définissez la notion simplement, sans sigle ni jargon, comme vous "
            "l'expliqueriez à un voisin.</p>"
        ),
        rich_text(
            "<h2>Pourquoi c'est important pour le quartier</h2>"
            "<p>Un exemple concret {area_in} aide à comprendre l'enjeu.</p>"
        ),
        rich_text(
            "<h2>Comment ça marche</h2>"
            "<p>Qui décide, selon quelles étapes, et où les habitants peuvent intervenir.</p>"
        ),
        rich_text(
            "<h2>À retenir</h2>"
            "<ul><li>Premier point clé</li><li>Deuxième point clé</li>"
            "<li>Troisième point clé</li></ul>"
        ),
        rich_text(
            "<h2>Pour aller plus loin</h2>"
            "<p>Liens vers les textes officiels, les sites de la Ville ou de la Métropole, "
            "et les autres fiches utiles.</p>"
        ),
    ),
)

GUIDE = PageTemplate(
    slug="guide",
    name=_("Step-by-step guide"),
    description=_(
        "How to do something, e.g. consult a building permit or contest a project: "
        "when, the steps, deadlines and contacts."
    ),
    blocks=(
        rich_text(
            "<h2>Dans quel cas ?</h2>"
            "<p>La situation dans laquelle cette démarche est utile, et ce qu'elle permet "
            "d'obtenir.</p>"
        ),
        rich_text(
            "<h2>Les étapes</h2>"
            "<ol>"
            "<li><b>[Étape]</b> : ce qu'il faut faire, et où</li>"
            "<li><b>[Étape]</b> : ce qu'il faut faire, et où</li>"
            "<li><b>[Étape]</b> : ce qu'il faut faire, et où</li>"
            "</ol>"
        ),
        rich_text(
            "<h2>Délais à connaître</h2>"
            "<p>Les dates limites, et ce qui se passe si elles sont dépassées.</p>"
        ),
        rich_text(
            "<h2>Contacts</h2>"
            "<p>Le service compétent, ses horaires, et l'association de votre quartier pour "
            "vous accompagner.</p>"
        ),
        faq(("[Une question fréquente]", "[Sa réponse, en une ou deux phrases.]")),
    ),
)

TEMPLATES = (CONCEPT, GUIDE)


# --- The "Informations utiles" page ------------------------------------------------
# Built from the home page parts around the list of cards.

CARD_LIST = {
    "type": BLOCK_TYPE_CARD_LIST,
    "value": {"label": "Ressources", "title": "Toutes les fiches"},
}

WHY_THESE_CARDS = section(
    label="Comprendre",
    title="L'urbanisme expliqué simplement",
    layout=SectionLayout.SPLIT,
    content=[
        {
            "type": "text",
            "value": (
                "<p>PLUi, permis de construire, enquête publique… Les projets du quartier "
                "s'accompagnent d'un vocabulaire et de démarches qui ne sont pas toujours "
                "évidents.</p>"
                "<p>Ces fiches les expliquent en quelques minutes, pour que chacun puisse "
                "suivre les projets et donner un avis éclairé.</p>"
            ),
        }
    ],
)

HOW_TO_USE = section(
    label="Mode d'emploi",
    title="De la fiche à l'action",
    tone=SectionTone.SAND,
    content=[
        {
            "type": "steps",
            "value": [
                {
                    "title": "Cherchez une notion",
                    "text": "Par mot-clé, dans le champ de recherche de la liste.",
                },
                {
                    "title": "Lisez la fiche",
                    "text": "L'essentiel en quelques paragraphes, avec des liens pour aller plus loin.",
                },
                {
                    "title": "Participez",
                    "text": "Donnez votre avis sur les projets en cours, en connaissance de cause.",
                },
            ],
        }
    ],
)

USEFUL_FAQ = section(
    label="Questions fréquentes",
    title="Vos questions",
    content=[
        {
            "type": "faq",
            "value": [
                {
                    "question": "Une notion manque ?",
                    "answer": "Écrivez-nous à l'adresse de contact indiquée en bas de page : nous en ferons une fiche.",
                },
                {
                    "question": "Qui écrit ces fiches ?",
                    "answer": "Indiquez qui rédige les fiches et à partir de quelles sources.",
                },
            ],
        }
    ],
)

INDEX_TEMPLATES = (
    PageTemplate(
        slug="complete",
        name=_("Complete"),
        description=_(
            "Why these cards, the cards, how to use them, open consultations and questions."
        ),
        blocks=(WHY_THESE_CARDS, CARD_LIST, HOW_TO_USE, OPEN_PROJECTS, USEFUL_FAQ, JOIN),
    ),
    PageTemplate(
        slug="simple",
        name=_("Simple"),
        description=_("The cards alone."),
        blocks=(CARD_LIST,),
    ),
)
