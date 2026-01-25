from datetime import timedelta

import factory
import factory.fuzzy
from django.utils import timezone

from core.tests.utils.blocks import mock_block_value
from core.tests.utils.factories import ImageFactory, BaseWagtailPageFactory
from publications.models import EventPage


class EventPageFactory(BaseWagtailPageFactory):
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

    event_date = factory.LazyAttribute(
        lambda _: timezone.now() + timedelta(days=factory.fuzzy.FuzzyInteger(1, 60).fuzz())
    )
    end_date = factory.LazyAttribute(
        lambda obj: obj.event_date + timedelta(hours=factory.fuzzy.FuzzyInteger(1, 4).fuzz())
    )
    location = factory.Faker("company", locale="fr_FR")
    address = factory.Faker("address", locale="fr_FR")
    is_online = factory.Faker("boolean", chance_of_getting_true=20)
    online_link = factory.LazyAttribute(
        lambda obj: f"https://example.com/event/{factory.fuzzy.FuzzyInteger(1000, 9999).fuzz()}"
        if obj.is_online
        else ""
    )
    max_participants = factory.fuzzy.FuzzyChoice([None, 20, 50, 100, 200])
