from importlib import import_module

from django.apps import apps
from django.test import TestCase

from publications.models import ProjectCategory, ProjectPage, PublicationIndexPage

migration = import_module("publications.migrations.0018_project_categories")


class RemapCategoriesMigrationTest(TestCase):
    def setUp(self) -> None:
        index = PublicationIndexPage.objects.first()
        assert index is not None
        self.projects: dict[str, ProjectPage] = {}
        for old_category in ("ENVIRONMENT", "URBAN_PLANNING", "HOUSING", "OTHER"):
            project = ProjectPage(title=f"Project {old_category}")
            index.add_child(instance=project)
            project.save_revision()
            # Bypass the choices to put back a category from before the migration.
            ProjectPage.objects.filter(pk=project.pk).update(category=old_category)
            revision = project.latest_revision
            assert revision is not None
            revision.content["category"] = old_category
            revision.save(update_fields=["content"])
            self.projects[old_category] = project

    def test_environment_is_kept_and_everything_else_becomes_living_environment(self) -> None:
        migration.remap_categories(apps, None)

        expected = {
            "ENVIRONMENT": ProjectCategory.ENVIRONMENT,
            "URBAN_PLANNING": ProjectCategory.LIVING_ENVIRONMENT,
            "HOUSING": ProjectCategory.LIVING_ENVIRONMENT,
            "OTHER": ProjectCategory.LIVING_ENVIRONMENT,
        }
        for old_category, new_category in expected.items():
            project = ProjectPage.objects.get(pk=self.projects[old_category].pk)
            self.assertEqual(project.category, new_category)
            revision = project.latest_revision
            assert revision is not None
            self.assertEqual(revision.content["category"], new_category)
