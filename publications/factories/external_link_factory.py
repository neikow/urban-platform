import factory

from publications.models import ProjectExternalLink


class ProjectExternalLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectExternalLink

    title = factory.Faker("sentence", nb_words=3, locale="fr_FR")
    url = factory.Faker("url")
    tooltip = factory.Faker("sentence", nb_sentences=1, locale="fr_FR")
