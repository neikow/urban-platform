import factory

from core.blocks import BLOCK_TYPE_RICH_TEXT, BLOCK_TYPE_IMAGE, BLOCK_TYPE_TWO_COLUMN
from core.tests.utils.blocks import mock_block_value
from core.tests.utils.factories import ImageFactory, BaseWagtailPageFactory
from publications.models import ProjectPage, Rubric


class ProjectPageFactory(BaseWagtailPageFactory):
    class Meta:
        model = ProjectPage
        skip_postgeneration_save = True

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

    @factory.post_generation
    def rubrics(  # type: ignore[misc]  # factory_boy passes the page, not the factory
        page: ProjectPage, create: bool, extracted: list[Rubric] | None, **kwargs: object
    ) -> None:
        if not create:
            return
        # Rubrics are seeded by a migration; a parental M2M is kept on save.
        page.rubrics.set(extracted if extracted is not None else [Rubric.objects.order_by("?")[0]])
        page.save()
