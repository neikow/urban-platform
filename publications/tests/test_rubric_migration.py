"""The rubric migration: the four rubrics exist, old categories map to one each.

Rolling the database back to the migration's start in a test clashes with the
other migration test's flush, so the data step is tested through its parts.
"""

from importlib import import_module

import pytest
from django.apps import apps

from publications.models import ProjectPage, PublicationIndexPage, Rubric, RubricCode

migration = import_module("publications.migrations.0022_project_rubrics")


def test_migration_seeds_the_codes_of_the_model():
    assert migration.RUBRIC_CODES == list(RubricCode.values)
    assert set(migration.CATEGORY_TO_RUBRIC.values()) <= set(RubricCode.values)


@pytest.mark.django_db
def test_rubrics_are_the_four_fixed_ones_in_order():
    assert list(Rubric.objects.values_list("code", flat=True)) == list(RubricCode.values)


@pytest.mark.django_db
def test_creating_rubrics_again_changes_nothing():
    migration.create_rubrics(apps, None)
    assert list(Rubric.objects.values_list("code", flat=True)) == list(RubricCode.values)


@pytest.mark.parametrize(
    ("category", "rubric"),
    [
        ("ENVIRONMENT", "PARKS_GARDENS"),
        ("LIVING_ENVIRONMENT", "PUBLIC_SPACE"),
        ("URBAN_FORMS", "HOUSING"),
        (None, "PUBLIC_SPACE"),
    ],
)
def test_revision_category_becomes_its_rubric(category, rubric):
    content = {"title": "Projet"} if category is None else {"title": "Projet", "category": category}

    def rubric_for(old):
        return migration.CATEGORY_TO_RUBRIC.get(old, migration.FALLBACK_RUBRIC)

    assert migration.rubrics_in_revision(content, rubric_for)
    assert content == {"title": "Projet", "rubrics": [rubric]}
    # Already converted: left as is.
    assert not migration.rubrics_in_revision(content, rubric_for)


@pytest.mark.django_db
def test_publishing_a_revision_with_rubric_ids_restores_them():
    index = PublicationIndexPage.objects.first()
    assert index is not None
    project = ProjectPage(title="Projet")
    index.add_child(instance=project)
    revision = project.save_revision()
    heritage = Rubric.objects.get(code=RubricCode.HERITAGE)
    revision.content["rubrics"] = [heritage.pk]
    revision.save(update_fields=["content"])

    revision.publish()

    assert list(ProjectPage.objects.get(pk=project.pk).rubrics.all()) == [heritage]
