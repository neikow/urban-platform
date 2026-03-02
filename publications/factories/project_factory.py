import factory
import factory.fuzzy

from core.blocks import BLOCK_TYPE_RICH_TEXT, BLOCK_TYPE_IMAGE, BLOCK_TYPE_TWO_COLUMN
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
            (BLOCK_TYPE_RICH_TEXT, mock_block_value(BLOCK_TYPE_RICH_TEXT)),
            (BLOCK_TYPE_IMAGE, mock_block_value(BLOCK_TYPE_IMAGE)),
            (BLOCK_TYPE_RICH_TEXT, mock_block_value(BLOCK_TYPE_RICH_TEXT)),
            (BLOCK_TYPE_TWO_COLUMN, mock_block_value(BLOCK_TYPE_TWO_COLUMN)),
            (BLOCK_TYPE_RICH_TEXT, mock_block_value(BLOCK_TYPE_RICH_TEXT)),
        ]
    )
    hero_image = factory.SubFactory(ImageFactory)
    category = factory.fuzzy.FuzzyChoice([c[0] for c in ProjectCategory.choices])
