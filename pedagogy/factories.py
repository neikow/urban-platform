import factory
from wagtail.models import Page
from wagtail.images.models import Image

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
    body = factory.Faker("paragraph", nb_sentences=10)
    description = factory.Faker("paragraph", nb_sentences=3)
    hero_image = factory.SubFactory(ImageFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        parent: Page = kwargs.pop("parent", None)  # type: ignore
        instance = model_class(**kwargs)

        if parent:
            parent.add_child(instance=instance)
            return instance

        raise ValueError(
            "Headless page creation not supported by this factory. Please provide a 'parent' argument."
        )
