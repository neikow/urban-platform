"""Ready-made "À propos" pages (see ``core.page_templates``).

Built from the home page parts. Where only the association knows the facts,
the text says what to write: editors replace these instructions with their
text, and delete the parts they do not need. The members of the association
and of the development team are shown after the content, so their templates
end on a part that introduces them.
"""

from django.utils.translation import gettext_lazy as _

from core.page_templates import PageTemplate, RawBlock
from home.blocks import FigureMetric, SectionLayout, SectionTone
from home.page_templates import FAQ, JOIN, JOIN_AN_ASSOCIATION, KEY_FIGURES, section


def text(html: str) -> RawBlock:
    return {"type": "text", "value": html}


def paragraph_section(label: str, title: str, html: str, **kwargs: str) -> RawBlock:
    return section(label=label, title=title, content=[{"type": "text", "value": html}], **kwargs)


SIMPLE = PageTemplate(
    slug="simple",
    name=_("Text only"),
    description=_("Headings and paragraphs, in the reading width."),
    blocks=(
        text(
            "<h2>Premier titre</h2>"
            "<p>Écrivez ici le texte de la page. Ajoutez des intertitres pour aider les "
            "visiteurs à trouver ce qu'ils cherchent.</p>"
            "<h2>Deuxième titre</h2>"
            "<p>Un paragraphe court se lit mieux qu'un long : allez à l'essentiel.</p>"
        ),
    ),
)

# --- La plateforme -----------------------------------------------------------------

WEBSITE = PageTemplate(
    slug="presentation",
    name=_("Presentation"),
    description=_(
        "Why the platform exists, what visitors can do on it, key figures, questions and "
        "an invitation to join."
    ),
    blocks=(
        paragraph_section(
            "Pourquoi cette plateforme",
            "Rendre les projets du quartier lisibles par tous",
            "<p>Expliquez le constat de départ : des projets d'urbanisme difficiles à suivre, "
            "des informations dispersées, peu d'occasions de donner son avis.</p>"
            "<p>Puis ce que la plateforme change : un seul endroit pour comprendre les "
            "projets, et un moyen simple de se faire entendre.</p>",
            layout=SectionLayout.SPLIT,
        ),
        section(
            label="Ce que vous pouvez faire",
            title="La plateforme en pratique",
            tone=SectionTone.SAND,
            content=[
                {
                    "type": "steps",
                    "value": [
                        {
                            "title": "Suivre les projets",
                            "text": "Plans, calendrier et enjeux de chaque projet du quartier.",
                        },
                        {
                            "title": "Donner votre avis",
                            "text": "Votez ou proposez vos idées pendant les consultations.",
                        },
                        {
                            "title": "Venir aux rendez-vous",
                            "text": "Réunions publiques, ateliers et balades urbaines.",
                        },
                        {
                            "title": "Comprendre l'urbanisme",
                            "text": "Les informations utiles expliquent les notions clés.",
                        },
                    ],
                }
            ],
        ),
        KEY_FIGURES,
        FAQ,
        JOIN,
    ),
)

# --- L'association --------------------------------------------------------------

COMMISSION = PageTemplate(
    slug="presentation",
    name=_("Presentation"),
    description=_(
        "Who you are, your missions, what residents say, the neighborhood associations, "
        "then its members."
    ),
    blocks=(
        paragraph_section(
            "Qui sommes-nous",
            "Notre association",
            "<p>Présentez l'association en quelques phrases : qui la compose, depuis "
            "quand elle existe, quel territoire elle couvre.</p>"
            "<p>Dites ce qui la guide, par exemple être force de proposition plutôt que "
            "d'opposition.</p>",
            layout=SectionLayout.SPLIT,
        ),
        section(
            label="Nos missions",
            title="Ce que fait l'association",
            tone=SectionTone.SAND,
            content=[
                {
                    "type": "steps",
                    "value": [
                        {
                            "title": "Informer",
                            "text": "Remplacez par une mission, en une phrase.",
                        },
                        {
                            "title": "Consulter",
                            "text": "Remplacez par une mission, en une phrase.",
                        },
                        {
                            "title": "Porter la voix des habitants",
                            "text": "Remplacez par une mission, en une phrase.",
                        },
                    ],
                }
            ],
        ),
        section(
            label="Ils en parlent",
            title="La parole aux habitants",
            content=[
                {
                    "type": "quotes",
                    "value": [
                        {
                            "quote": "Citez un habitant ou un membre, avec son accord.",
                            "author": "Prénom N.",
                            "role": "Quartier",
                        }
                    ],
                }
            ],
        ),
        JOIN_AN_ASSOCIATION,
        section(
            label="L'équipe",
            title="Les membres de l'association",
            introduction="Les membres sont présentés ci-dessous.",
            content=[],
        ),
    ),
)

# --- L'équipe de développement -------------------------------------------------

DEV_TEAM = PageTemplate(
    slug="presentation",
    name=_("Presentation"),
    description=_(
        "The project, how it is built, how to contribute and the platform in figures, "
        "then the team members."
    ),
    blocks=(
        paragraph_section(
            "Le projet",
            "Une plateforme construite par des bénévoles",
            "<p>Racontez comment le projet est né, et qui y contribue.</p>",
            layout=SectionLayout.SPLIT,
        ),
        text(
            "<h2>Comment la plateforme est faite</h2>"
            "<p>Décrivez en termes simples les choix techniques : logiciels libres, "
            "hébergement, respect de la vie privée.</p>"
            "<h2>Contribuer</h2>"
            "<p>Indiquez où trouver le code source et comment signaler un problème ou "
            "proposer une amélioration.</p>"
        ),
        section(
            label="En chiffres",
            title="La plateforme aujourd'hui",
            tone=SectionTone.NAVY,
            content=[
                {
                    "type": "key_figures",
                    "value": [
                        {"metric": FigureMetric.PROJECTS, "value": "", "label": "Projets suivis"},
                        {"metric": FigureMetric.MEMBERS, "value": "", "label": "Membres inscrits"},
                        {"metric": FigureMetric.VOTES, "value": "", "label": "Votes exprimés"},
                    ],
                }
            ],
        ),
        section(
            label="L'équipe",
            title="Les développeurs",
            introduction="Les membres de l'équipe sont présentés ci-dessous.",
            content=[],
        ),
    ),
)

WEBSITE_TEMPLATES = (WEBSITE, SIMPLE)
COMMISSION_TEMPLATES = (COMMISSION, SIMPLE)
DEV_TEAM_TEMPLATES = (DEV_TEAM, SIMPLE)
