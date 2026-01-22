from typing import Any
from datetime import timedelta

import factory
from django.utils import timezone
from wagtail.models import Page

from core.tests.utils.blocks import mock_block_value
from publications.factories.image_factory import ImageFactory
from publications.models import EventPage


class EventPageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventPage

    title = factory.Faker("sentence", nb_words=4, locale="fr_FR")
    description = factory.Faker("paragraph", nb_sentences=3, locale="fr_FR")
    content = factory.LazyFunction(
        lambda: [
            ("text", mock_block_value("text")),
            ("image", mock_block_value("image")),
            ("text", mock_block_value("text")),
        ]
    )
    hero_image = factory.SubFactory(ImageFactory)

    event_date = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=factory.Faker._get_faker().random_int(min=1, max=60))
    )
    end_date = factory.LazyAttribute(
        lambda obj: obj.event_date + timedelta(hours=factory.Faker._get_faker().random_int(min=1, max=4))
    )
    location = factory.Faker("company", locale="fr_FR")
    address = factory.Faker("address", locale="fr_FR")
    is_online = factory.Faker("boolean", chance_of_getting_true=20)
    online_link = factory.LazyAttribute(
        lambda obj: factory.Faker._get_faker().url() if obj.is_online else ""
    )
    max_participants = factory.LazyFunction(
        lambda: factory.Faker._get_faker().random_element([None, 20, 50, 100, 200])
    )

    @classmethod
    def _create(
        cls, model_class: type[EventPage], *args: Any, **kwargs: Any
    ) -> EventPage:
        parent: Page = kwargs.pop("parent", None)
        instance = model_class(**kwargs)

        if parent:
            parent.add_child(instance=instance)
            return instance

        raise ValueError(
            "Headless page creation not supported by this factory. Please provide a 'parent' argument."
        )
