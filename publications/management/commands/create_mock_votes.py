from typing import Any
import random

from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from publications.models import ProjectPage, FormResponse, VoteChoice


User = get_user_model()

# Prénoms français courants
FIRST_NAMES = [
    "Marie", "Jean", "Pierre", "Françoise", "Michel", "Monique", "André",
    "Catherine", "Philippe", "Isabelle", "Nicolas", "Sophie", "Laurent",
    "Nathalie", "Christophe", "Sandrine", "Julien", "Céline", "Thomas",
    "Aurélie", "Alexandre", "Émilie", "Mathieu", "Marine", "Sébastien",
    "Charlotte", "Antoine", "Camille", "Romain", "Julie", "Maxime",
    "Léa", "Guillaume", "Manon", "Florian", "Pauline", "Kevin", "Clara",
]

# Noms de famille français courants
LAST_NAMES = [
    "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit",
    "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel",
    "Garcia", "David", "Bertrand", "Roux", "Vincent", "Fournier", "Morel",
    "Girard", "André", "Lefèvre", "Mercier", "Dupont", "Lambert", "Bonnet",
    "François", "Martinez", "Legrand", "Garnier", "Faure", "Rousseau",
]

# Codes postaux de Marseille
POSTAL_CODES = [
    "13001", "13002", "13003", "13004", "13005", "13006", "13007", "13008",
    "13009", "13010", "13011", "13012", "13013", "13014", "13015", "13016",
]

# Commentaires positifs
POSITIVE_COMMENTS = [
    "Excellent projet, très bien pensé pour notre quartier !",
    "Je soutiens pleinement cette initiative. C'est exactement ce dont nous avions besoin.",
    "Enfin un projet qui répond aux attentes des habitants. Bravo !",
    "Belle initiative pour améliorer notre cadre de vie.",
    "Ce projet va vraiment transformer positivement notre environnement.",
    "Je suis enthousiaste à l'idée de voir ce projet se concrétiser.",
    "Un pas dans la bonne direction pour notre communauté.",
    "Très bonne idée, j'espère que le projet sera mené à bien rapidement.",
    "Ce genre d'initiatives devrait être plus fréquent !",
    "Je soutiens ce projet qui va améliorer la qualité de vie des résidents.",
]

# Commentaires négatifs
NEGATIVE_COMMENTS = [
    "Je ne suis pas convaincu par ce projet. Les priorités devraient être ailleurs.",
    "Le budget alloué me semble disproportionné par rapport aux bénéfices attendus.",
    "Je crains que ce projet ne crée plus de nuisances que d'améliorations.",
    "Il y a d'autres besoins plus urgents dans notre quartier.",
    "Ce projet ne répond pas vraiment aux attentes des habitants.",
    "Je suis sceptique quant à la faisabilité de ce projet.",
    "Les impacts environnementaux n'ont pas été suffisamment étudiés.",
    "Ce projet risque d'aggraver les problèmes de circulation.",
    "Je préférerais que les ressources soient investies différemment.",
    "Ce projet ne prend pas en compte les besoins des familles.",
]

# Commentaires neutres
NEUTRAL_COMMENTS = [
    "Intéressant, mais j'aimerais avoir plus d'informations avant de me prononcer définitivement.",
    "Le projet a du potentiel, mais certains aspects mériteraient d'être retravaillés.",
    "Je comprends l'intention, mais je reste prudent sur les résultats attendus.",
    "C'est un bon début, mais il faudrait peut-être aller plus loin.",
    "Je suis partagé. Il y a des aspects positifs et négatifs.",
    "Le projet est acceptable, sans plus.",
    "J'attends de voir les résultats concrets avant de juger.",
    "Certains points sont bien pensés, d'autres moins.",
]


class Command(BaseCommand):
    help = "Create mock users and vote responses for projects. Only works in DEBUG mode."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users",
            type=int,
            default=20,
            help="Number of users to create (default: 20)",
        )
        parser.add_argument(
            "--votes-per-project",
            type=int,
            default=10,
            help="Average number of votes per project (default: 10)",
        )
        parser.add_argument(
            "--comment-probability",
            type=float,
            default=0.5,
            help="Probability that a vote includes a comment (default: 0.5)",
        )
        parser.add_argument(
            "--delete-users",
            action="store_true",
            help="Delete all non-admin, non-staff users before creating new ones",
        )
        parser.add_argument(
            "--delete-votes",
            action="store_true",
            help="Delete all existing vote responses before creating new ones",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            self.stderr.write(self.style.ERROR("This command can only be run when DEBUG=True"))
            return

        # Delete existing data if requested
        if options["delete_votes"]:
            deleted_count = FormResponse.objects.all().delete()[0]
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} existing vote responses."))

        if options["delete_users"]:
            deleted_count = User.objects.filter(is_staff=False, is_superuser=False).delete()[0]
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} non-admin users."))

        users_count = options["users"]
        votes_per_project = options["votes_per_project"]
        comment_probability = options["comment_probability"]

        # Create users
        self.stdout.write(f"Creating {users_count} users...")
        created_users = []
        for i in range(users_count):
            try:
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"

                # Check if user already exists
                if User.objects.filter(email=email).exists():
                    self.stdout.write(f"  User {email} already exists, skipping...")
                    created_users.append(User.objects.get(email=email))
                    continue

                user = User.objects.create_user(
                    email=email,
                    password="testpassword123",
                    first_name=first_name,
                    last_name=last_name,
                    postal_code=random.choice(POSTAL_CODES),
                    is_verified=True,
                )
                created_users.append(user)
                self.stdout.write(f"  Created user: {user.get_full_name()} ({email})")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Failed to create user {i + 1}: {e}"))

        if not created_users:
            # Get existing non-admin users
            created_users = list(User.objects.filter(is_staff=False, is_superuser=False))
            if not created_users:
                self.stderr.write(self.style.ERROR("No users available to create votes."))
                return

        # Get projects with voting enabled
        projects_with_voting = ProjectPage.objects.filter(enable_voting=True)

        if not projects_with_voting.exists():
            self.stderr.write(
                self.style.ERROR(
                    "No projects with voting enabled found. "
                    "Please run 'python manage.py create_mock_publications' first."
                )
            )
            return

        # Create votes for each project
        self.stdout.write(f"Creating votes for {projects_with_voting.count()} projects...")
        total_votes_created = 0
        total_votes_with_comments = 0

        for project in projects_with_voting:
            # Randomly select users to vote on this project
            num_voters = min(
                random.randint(max(1, votes_per_project - 5), votes_per_project + 5),
                len(created_users)
            )
            voters = random.sample(created_users, num_voters)

            project_votes = 0
            for user in voters:
                # Check if user already voted on this project
                if FormResponse.objects.filter(user=user, project=project).exists():
                    continue

                try:
                    # Choose a vote based on weighted probability
                    # Slightly favor positive votes for realism
                    vote_weights = [0.15, 0.20, 0.30, 0.35]  # UNFAV, RATHER_UNFAV, RATHER_FAV, FAV
                    choice = random.choices(
                        list(VoteChoice.choices),
                        weights=vote_weights,
                        k=1
                    )[0][0]

                    # Decide if adding a comment
                    comment = ""
                    if random.random() < comment_probability:
                        if choice in [VoteChoice.FAVORABLE, VoteChoice.RATHER_FAVORABLE]:
                            comment = random.choice(POSITIVE_COMMENTS)
                        elif choice in [VoteChoice.UNFAVORABLE, VoteChoice.RATHER_UNFAVORABLE]:
                            comment = random.choice(NEGATIVE_COMMENTS)
                        else:
                            comment = random.choice(NEUTRAL_COMMENTS)

                    FormResponse.objects.create(
                        user=user,
                        project=project,
                        choice=choice,
                        comment=comment,
                        anonymize=random.random() < 0.3,  # 30% choose to be anonymous
                    )
                    project_votes += 1
                    total_votes_created += 1
                    if comment:
                        total_votes_with_comments += 1

                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f"  Failed to create vote for {user.email} on {project.title}: {e}")
                    )

            self.stdout.write(f"  Created {project_votes} votes for: {project.title}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created:\n"
                f"  - {len(created_users)} users\n"
                f"  - {total_votes_created} votes ({total_votes_with_comments} with comments)"
            )
        )
