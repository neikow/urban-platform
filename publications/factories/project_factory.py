from typing import Any

import factory
from wagtail.models import Page

from core.tests.utils.blocks import mock_block_value
from publications.factories.image_factory import ImageFactory
from publications.models import ProjectPage, ProjectCategory


class PublicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "wagtaildocs.Document"

    title = factory.Faker("sentence", nb_words=3)
    file = factory.django.FileField()


class ProjectPageFactory(factory.django.DjangoModelFactory):
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
    category = factory.Faker(
        "random_element", elements=[choice[0] for choice in ProjectCategory.choices]
    )

    @classmethod
    def _create(cls, model_class: type[ProjectPage], *args: Any, **kwargs: Any) -> ProjectPage:
        parent: Page = kwargs.pop("parent", None)
        instance = model_class(**kwargs)

        if parent:
            parent.add_child(instance=instance)
            return instance

        raise ValueError(
            "Headless page creation not supported by this factory. Please provide a 'parent' argument."
        )
