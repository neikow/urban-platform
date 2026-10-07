"""Ready-made projects and events (see ``core.page_templates``).

Each section says what to write in it: editors replace these instructions
with their text, and delete the sections they do not need.
"""

from django.utils.translation import gettext_lazy as _

from core.page_templates import PageTemplate, faq, rich_text
from publications.models.project import ParticipationMode

# --- Projects --------------------------------------------------------------------

PROJECT_IN_BRIEF = rich_text(
    "<h2>Le projet en bref</h2>"
    "<p>Décrivez en deux ou trois phrases ce qui est prévu, où, et par qui. "
    "C'est ce que la plupart des visiteurs liront : allez à l'essentiel.</p>"
)

PROJECT_SCHEDULE = rich_text(
    "<h2>Calendrier</h2>"
    "<ul>"
    "<li><b>[Date]</b> : présentation du projet</li>"
    "<li><b>[Date]</b> : fin de la consultation</li>"
    "<li><b>[Date]</b> : début des travaux</li>"
    "</ul>"
)

PROJECT_WHO = rich_text(
    "<h2>Qui porte le projet ?</h2>"
    "<p>Indiquez le maître d'ouvrage (Ville, Métropole, promoteur…), les autres acteurs "
    "et la position de la commission urbanisme, si elle en a une.</p>"
)

VOTE_PROJECT = PageTemplate(
    slug="vote",
    name=_("Project put to the vote"),
    description=_(
        "Residents give their opinion on a defined project: what it is, why, what changes, "
        "when, and who decides."
    ),
    fields={"participation_mode": ParticipationMode.VOTING},
    blocks=(
        PROJECT_IN_BRIEF,
        rich_text(
            "<h2>Pourquoi ce projet ?</h2>"
            "<p>Le constat de départ, le besoin auquel le projet répond, et ce qui se passerait "
            "sans lui.</p>"
        ),
        rich_text(
            "<h2>Ce qui va changer pour vous</h2>"
            "<p>Circulation, stationnement, espaces verts, bruit pendant les travaux… Soyez "
            "concret : les habitants veulent savoir ce qui change dans leur rue.</p>"
        ),
        PROJECT_SCHEDULE,
        PROJECT_WHO,
        rich_text(
            "<h2>Comment votre avis est utilisé</h2>"
            "<p>Expliquez ce que deviendront les résultats du vote : à qui ils seront transmis, "
            "et quand vous en donnerez des nouvelles dans le suivi du projet.</p>"
        ),
        faq(
            (
                "Qui peut voter ?",
                "Toute personne inscrite sur la plateforme, une fois son adresse email confirmée.",
            ),
            ("Puis-je changer mon vote ?", "Oui, tant que le vote est ouvert."),
        ),
    ),
)

IDEAS_PROJECT = PageTemplate(
    slug="ideas",
    name=_("Project open to ideas"),
    description=_(
        "A project still taking shape: residents suggest ideas on what is not decided yet."
    ),
    fields={"participation_mode": ParticipationMode.IDEAS},
    blocks=(
        PROJECT_IN_BRIEF,
        rich_text(
            "<h2>Sur quoi vos idées sont attendues</h2>"
            "<p>Posez une ou deux questions précises, par exemple : « Quels usages "
            "imaginez-vous pour cette place ? ». Une question claire donne des idées utiles.</p>"
        ),
        rich_text(
            "<h2>Ce qui est déjà décidé</h2>"
            "<p>Le budget, l'emprise, les contraintes techniques ou réglementaires : ce qui "
            "n'est plus en discussion, pour que les idées restent réalistes.</p>"
        ),
        rich_text(
            "<h2>Et ensuite ?</h2>"
            "<p>Comment les idées seront lues, regroupées et transmises, et quand vous "
            "publierez une synthèse.</p>"
        ),
        PROJECT_WHO,
    ),
)

INFORMATION_PROJECT = PageTemplate(
    slug="information",
    name=_("Project to follow"),
    description=_(
        "Information on a project without a vote: what it is, its schedule and its documents."
    ),
    fields={"participation_mode": ParticipationMode.NONE},
    blocks=(
        PROJECT_IN_BRIEF,
        rich_text(
            "<h2>Ce qu'il faut savoir</h2>"
            "<p>Les points importants du projet et ses conséquences pour le quartier.</p>"
        ),
        PROJECT_SCHEDULE,
        PROJECT_WHO,
        rich_text(
            "<h2>Documents</h2>"
            "<p>Ajoutez ici des blocs « Document » : plans, permis, comptes rendus de "
            "réunion…</p>"
        ),
    ),
)

PROJECT_TEMPLATES = (VOTE_PROJECT, IDEAS_PROJECT, INFORMATION_PROJECT)


# --- Events ------------------------------------------------------------------------

PRACTICAL = rich_text(
    "<h2>Infos pratiques</h2>"
    "<ul>"
    "<li><b>Accès</b> : bus, métro, stationnement</li>"
    "<li><b>Accessibilité</b> : accès en fauteuil roulant, boucle magnétique…</li>"
    "<li><b>Contact</b> : une adresse email pour les questions</li>"
    "</ul>"
)

PUBLIC_MEETING = PageTemplate(
    slug="public-meeting",
    name=_("Public meeting"),
    description=_("A presentation followed by questions: agenda, speakers, practical information."),
    blocks=(
        rich_text(
            "<h2>Ordre du jour</h2>"
            "<ol>"
            "<li>Accueil et présentation de la soirée</li>"
            "<li>Présentation du projet</li>"
            "<li>Questions et échanges avec la salle</li>"
            "</ol>"
        ),
        rich_text(
            "<h2>Intervenants</h2>"
            "<p>Qui présentera, et à quel titre (élu, service de la Ville, architecte, "
            "membre de la commission…).</p>"
        ),
        PRACTICAL,
        rich_text(
            "<h2>Vous ne pouvez pas venir ?</h2>"
            "<p>Dites où le compte rendu sera publié, et comment poser une question à "
            "l'avance.</p>"
        ),
    ),
)

WORKSHOP = PageTemplate(
    slug="workshop",
    name=_("Participatory workshop"),
    description=_("A working session in small groups: goal, programme, what to bring."),
    blocks=(
        rich_text(
            "<h2>Objectif</h2>"
            "<p>Ce que l'atelier doit produire : une liste de propositions, une carte des "
            "usages, un avis sur plusieurs scénarios…</p>"
        ),
        rich_text(
            "<h2>Déroulé</h2>"
            "<ol>"
            "<li>Présentation du sujet (15 min)</li>"
            "<li>Travail en petits groupes (1 h)</li>"
            "<li>Mise en commun (30 min)</li>"
            "</ol>"
        ),
        rich_text(
            "<h2>Venir à l'atelier</h2>"
            "<p>Le nombre de places, s'il faut s'inscrire, et ce qu'il est utile "
            "d'apporter.</p>"
        ),
        PRACTICAL,
    ),
)

WALK = PageTemplate(
    slug="walk",
    name=_("Neighbourhood walk"),
    description=_("A guided walk through the area: route, stops, practical information."),
    blocks=(
        rich_text(
            "<h2>Le parcours</h2>"
            "<p>Le point de départ, l'arrivée, la distance et la durée. Précisez si le "
            "parcours comporte des escaliers ou des pentes.</p>"
        ),
        rich_text(
            "<h2>Les étapes</h2>"
            "<ol>"
            "<li><b>[Lieu]</b> : ce que l'on y observe</li>"
            "<li><b>[Lieu]</b> : ce que l'on y observe</li>"
            "<li><b>[Lieu]</b> : ce que l'on y observe</li>"
            "</ol>"
        ),
        PRACTICAL,
    ),
)

EVENT_TEMPLATES = (PUBLIC_MEETING, WORKSHOP, WALK)
