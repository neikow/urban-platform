from typing import Any

import factory
from wagtail.models import Page
from wagtail.images.models import Image
from core.tests.utils.blocks import mock_block_value
from .models import PedagogyCardPage


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    title = factory.Faker("sentence", nb_words=3)
    file = factory.django.ImageField(color=factory.Faker("safe_color_name"))


class PedagogyCardPageFactory(factory.django.DjangoModelFactory):
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

    @classmethod
    def _create(
        cls, model_class: type[PedagogyCardPage], *args: Any, **kwargs: Any
    ) -> PedagogyCardPage:
        parent: Page = kwargs.pop("parent", None)  # type: ignore
        instance = model_class(**kwargs)

        if parent:
            parent.add_child(instance=instance)
            return instance

        raise ValueError(
            "Headless page creation not supported by this factory. Please provide a 'parent' argument."
        )


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "wagtaildocs.Document"

    title = factory.Faker("sentence", nb_words=3)
    file = factory.django.FileField()
