import factory

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
            ("text", mock_block_value("text")),
            ("image", mock_block_value("image")),
            ("text", mock_block_value("text")),
            ("image_text", mock_block_value("image_text")),
            ("text", mock_block_value("text")),
        ]
    )
    hero_image = factory.SubFactory(ImageFactory)
