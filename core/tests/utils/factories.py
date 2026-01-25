from typing import Any

import factory
from wagtail.images.models import Image
from wagtail.models import Page


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    title = factory.Faker("sentence", nb_words=3)
    file = factory.django.ImageField(color=factory.Faker("safe_color_name"))


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "wagtaildocs.Document"

    title = factory.Faker("sentence", nb_words=3)
    file = factory.django.FileField()


class WagtailPageFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    @classmethod
    def _create(cls, model_class: type[Page], *args: Any, **kwargs: Any) -> Page:
        parent: Page | None = kwargs.pop("parent", None)
        instance = model_class(**kwargs)

        if parent:
            parent.add_child(instance=instance)
            return instance

        raise ValueError(
            "Headless page creation not supported by this factory. "
            "Please provide a 'parent' argument."
        )
