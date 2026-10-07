"""Ready-made home pages, so editors do not start from a blank page.

Applied as described in ``core.page_templates``. The hero of the current
draft is kept, so its photo is not lost.

The texts are starting points written for Urba7Marseille, meant to be edited.
"""

from django.utils.translation import gettext_lazy as _

from core.blocks import BLOCK_TYPE_HERO, BLOCK_TYPE_RECENT_PUBLICATIONS
from core.page_templates import PageTemplate, RawBlock
from home.blocks import FigureMetric, SectionLayout, SectionTone


def section(
    *,
    label: str,
    title: str,
    content: list[RawBlock],
    introduction: str = "",
    tone: str = SectionTone.PLAIN,
    layout: str = SectionLayout.STACKED,
) -> RawBlock:
    return {
        "type": "section",
        "value": {
            "label": label,
            "title": title,
            "introduction": introduction,
            "tone": tone,
            "layout": layout,
            "content": content,
        },
    }


WHO_WE_ARE = section(
    label="Qui sommes-nous",
    title="Un urbanisme de proximité, à la portée de tous",
    layout=SectionLayout.SPLIT,
    content=[
        {
            "type": "text",
            "value": (
                "<p>Urba7Marseille est la plateforme de la commission urbanisme de la "
                "fédération des CIQ du 7<sup>e</sup> arrondissement de Marseille.</p>"
                "<p>Elle partage avec les habitants et les usagers du quartier les projets "
                "d'urbanisme à l'étude ou en cours : ce qui change, pourquoi, et comment "
                "donner son avis. Notre ambition n'est pas de nous opposer, mais d'être "
                "force de proposition.</p>"
            ),
        }
    ],
)

HOW_IT_WORKS = section(
    label="Comment ça marche",
    title="Quatre étapes pour peser sur les projets",
    tone=SectionTone.SAND,
    content=[
        {
            "type": "steps",
            "value": [
                {
                    "title": "Créez votre compte",
                    "text": "Une adresse email suffit. Elle nous permet de compter une voix par personne.",
                },
                {
                    "title": "Découvrez les projets",
                    "text": "Plans, calendrier et enjeux : chaque projet du quartier a sa page.",
                },
                {
                    "title": "Votez ou proposez",
                    "text": "Donnez votre avis pendant la consultation, ou déposez vos idées.",
                },
                {
                    "title": "Suivez la suite",
                    "text": "Résultats et nouvelles étapes vous sont envoyés par email si vous le souhaitez.",
                },
            ],
        }
    ],
)

KEY_FIGURES = section(
    label="En chiffres",
    title="La plateforme aujourd'hui",
    tone=SectionTone.NAVY,
    content=[
        {
            "type": "key_figures",
            "value": [
                {"metric": FigureMetric.PROJECTS, "value": "", "label": "Projets suivis"},
                {"metric": FigureMetric.PARTICIPANTS, "value": "", "label": "Habitants mobilisés"},
                {"metric": FigureMetric.VOTES, "value": "", "label": "Votes exprimés"},
                {"metric": FigureMetric.IDEAS, "value": "", "label": "Idées proposées"},
            ],
        }
    ],
)

JOIN_A_CIQ = section(
    label="Agir localement",
    title="Rejoignez le CIQ de votre quartier",
    layout=SectionLayout.SPLIT,
    content=[
        {
            "type": "text",
            "value": (
                "<p>Les comités d'intérêt de quartier (CIQ) portent la voix des habitants "
                "auprès des pouvoirs publics. Pour agir sur votre environnement au-delà "
                "de cette plateforme, devenez membre du CIQ de votre quartier.</p>"
                '<p>Contact : <a href="mailto:fedeciqmarseille7@hotmail.fr">'
                "fedeciqmarseille7@hotmail.fr</a></p>"
            ),
        }
    ],
)

FAQ = section(
    label="Questions fréquentes",
    title="Vos questions",
    content=[
        {
            "type": "faq",
            "value": [
                {
                    "question": "Comment connaître les projets en cours ?",
                    "answer": "Rendez-vous dans « Actualités » : les projets et événements y sont listés, du plus récent au plus ancien.",
                },
                {
                    "question": "Comment voter et donner mon avis ?",
                    "answer": "Créez un compte et confirmez votre adresse email, puis ouvrez la page du projet pendant la consultation.",
                },
                {
                    "question": "Comment aller plus loin dans mon implication ?",
                    "answer": "Rejoignez le CIQ de votre quartier : il porte les demandes des habitants auprès des pouvoirs publics.",
                },
                {
                    "question": "Puis-je suggérer un projet qui n'est pas encore sur le site ?",
                    "answer": "Oui, écrivez-nous à l'adresse de contact indiquée en bas de page.",
                },
            ],
        }
    ],
)

OPEN_PROJECTS = {
    "type": "open_projects",
    "value": {"label": "Participer", "title": "Consultations en cours", "limit": 3},
}
UPCOMING_EVENTS = {
    "type": "upcoming_events",
    "value": {"label": "Agenda", "title": "Prochains rendez-vous", "limit": 3},
}
PROJECTS_MAP = {
    "type": "projects_map",
    "value": {"label": "Autour de vous", "title": "Les projets du quartier", "introduction": ""},
}
RECENT_PUBLICATIONS = {
    "type": BLOCK_TYPE_RECENT_PUBLICATIONS,
    "value": {"number_of_publications": 6},
}
JOIN = {
    "type": "join",
    "value": {
        "title": "Votre avis compte",
        "text": "Inscrivez-vous pour voter sur les projets du quartier, proposer vos idées et être prévenu des résultats.",
        "button": "Créer mon compte",
        "member_button": "Choisir mes notifications",
    },
}


TEMPLATES = (
    PageTemplate(
        slug="participation",
        name=_("Participation"),
        description=_(
            "The full page: who you are, open consultations, how it works, key figures, "
            "events, the map, news, the CIQ and questions."
        ),
        blocks=(
            WHO_WE_ARE,
            OPEN_PROJECTS,
            HOW_IT_WORKS,
            KEY_FIGURES,
            UPCOMING_EVENTS,
            PROJECTS_MAP,
            RECENT_PUBLICATIONS,
            JOIN_A_CIQ,
            FAQ,
            JOIN,
        ),
        keep=(BLOCK_TYPE_HERO,),
    ),
    PageTemplate(
        slug="essentials",
        name=_("Essentials"),
        description=_(
            "A short page focused on what is happening now: consultations, news and events."
        ),
        blocks=(OPEN_PROJECTS, RECENT_PUBLICATIONS, UPCOMING_EVENTS, JOIN),
        keep=(BLOCK_TYPE_HERO,),
    ),
)
