import factory

from core.blocks import BLOCK_TYPE_RICH_TEXT, BLOCK_TYPE_TWO_COLUMN, BLOCK_TYPE_IMAGE
from core.tests.utils.blocks import mock_block_value
from core.tests.utils.factories import ImageFactory, BaseWagtailPageFactory
from pedagogy.models import PedagogyCardPage


class PedagogyCardPageFactory(BaseWagtailPageFactory):
    class Meta:
        model = PedagogyCardPage

    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("paragraph", nb_sentences=3)
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
