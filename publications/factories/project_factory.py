import factory
import factory.fuzzy

from core.tests.utils.blocks import mock_block_value
from core.tests.utils.factories import ImageFactory, BaseWagtailPageFactory
from publications.models import ProjectPage, ProjectCategory


class ProjectPageFactory(BaseWagtailPageFactory):
    class Meta:
        model = ProjectPage

    title = factory.Faker("sentence", nb_words=4, locale="fr_FR")
    description = factory.Faker("paragraph", nb_sentences=3, locale="fr_FR")
    content = factory.LazyFunction(
        lambda: [
            ("text", mock_block_value("text")),
            ("image", mock_block_value("image")),
            ("text", mock_block_value("text")),
            ("image_text", mock_block_value("image_text")),
            ("text", mock_block_value("text")),
        ]
    )
    hero_image = factory.SubFactory(ImageFactory)
    category = factory.fuzzy.FuzzyChoice([c[0] for c in ProjectCategory.choices])
