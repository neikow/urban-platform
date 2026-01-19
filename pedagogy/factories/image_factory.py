import factory
from wagtail.images.models import Image


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    title = factory.Faker("sentence", nb_words=3)
    file = factory.django.ImageField(color=factory.Faker("safe_color_name"))
