"""Ready-made "Informations utiles" cards (see ``core.page_templates``).

Each section says what to write in it: editors replace these instructions
with their text, and delete the sections they do not need.
"""

from django.utils.translation import gettext_lazy as _

from core.page_templates import PageTemplate, faq, rich_text

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
            "<p>Un exemple concret dans le 7<sup>e</sup> arrondissement aide à comprendre "
            "l'enjeu.</p>"
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
            "<p>Le service compétent, ses horaires, et le CIQ de votre quartier pour vous "
            "accompagner.</p>"
        ),
        faq(("[Une question fréquente]", "[Sa réponse, en une ou deux phrases.]")),
    ),
)

TEMPLATES = (CONCEPT, GUIDE)
