from unittest.mock import MagicMock, patch

from django.test import TestCase

from publications.services import (
    PublicationFilters,
    filter_publications_by_category,
    filter_publications_by_type,
    paginate_publications,
    search_publications,
)


class PublicationFiltersTest(TestCase):
    def test_default_values(self) -> None:
        filters = PublicationFilters()

        self.assertEqual(filters.publication_type, "all")
        self.assertIsNone(filters.category)
        self.assertEqual(filters.search_query, "")
        self.assertIsNone(filters.page_number)

    def test_from_request_extracts_all_params(self) -> None:
        request = MagicMock()
        get_data = {
            "type": "projects",
            "category": "URBAN_PLANNING",
            "search": "test query",
            "page": "2",
        }
        request.GET.get = lambda key, default=None: get_data.get(key, default)

        filters = PublicationFilters.from_request(request)

        self.assertEqual(filters.publication_type, "projects")
        self.assertEqual(filters.category, "URBAN_PLANNING")
        self.assertEqual(filters.search_query, "test query")
        self.assertEqual(filters.page_number, 2)

    def test_from_request_with_missing_params_uses_defaults(self) -> None:
        request = MagicMock()
        request.GET.get = lambda key, default=None: default

        filters = PublicationFilters.from_request(request)

        self.assertEqual(filters.publication_type, "all")
        self.assertIsNone(filters.category)
        self.assertEqual(filters.search_query, "")
        self.assertIsNone(filters.page_number)


class FilterPublicationsByTypeTest(TestCase):
    @patch("django.contrib.contenttypes.models.ContentType.objects.get_for_model")
    def test_filter_by_projects(self, mock_get_for_model: MagicMock) -> None:
        mock_queryset = MagicMock()
        mock_filtered = MagicMock()
        mock_ordered = MagicMock()

        mock_queryset.filter.return_value = mock_filtered
        mock_filtered.order_by.return_value = mock_ordered

        mock_ct = MagicMock()
        mock_get_for_model.return_value = mock_ct

        result = filter_publications_by_type(mock_queryset, "projects")

        mock_queryset.filter.assert_called_once_with(real_type=mock_ct)
        mock_filtered.order_by.assert_called_once_with("-first_published_at")
        self.assertEqual(result, mock_ordered)

    @patch("django.contrib.contenttypes.models.ContentType.objects.get_for_model")
    def test_filter_by_events(self, mock_get_for_model: MagicMock) -> None:
        mock_queryset = MagicMock()
        mock_filtered = MagicMock()
        mock_ordered = MagicMock()

        mock_queryset.filter.return_value = mock_filtered
        mock_filtered.order_by.return_value = mock_ordered

        mock_ct = MagicMock()
        mock_get_for_model.return_value = mock_ct

        result = filter_publications_by_type(mock_queryset, "events")

        mock_queryset.filter.assert_called_once_with(real_type=mock_ct)
        mock_filtered.order_by.assert_called_once_with("-eventpage__event_date")
        self.assertEqual(result, mock_ordered)

    def test_filter_by_all_returns_ordered(self) -> None:
        mock_queryset = MagicMock()
        mock_ordered = MagicMock()
        mock_queryset.order_by.return_value = mock_ordered

        result = filter_publications_by_type(mock_queryset, "all")

        mock_queryset.order_by.assert_called_once_with("-first_published_at")
        self.assertEqual(result, mock_ordered)

    def test_filter_by_unknown_type_returns_all(self) -> None:
        mock_queryset = MagicMock()
        mock_ordered = MagicMock()
        mock_queryset.order_by.return_value = mock_ordered

        result = filter_publications_by_type(mock_queryset, "unknown")

        mock_queryset.order_by.assert_called_once_with("-first_published_at")
        self.assertEqual(result, mock_ordered)


class FilterPublicationsByCategoryTest(TestCase):
    def test_filter_with_valid_category(self) -> None:
        mock_queryset = MagicMock()
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered

        result = filter_publications_by_category(mock_queryset, "URBAN_PLANNING")

        mock_queryset.filter.assert_called_once_with(projectpage__category="URBAN_PLANNING")
        self.assertEqual(result, mock_filtered)

    def test_filter_with_invalid_category_returns_unchanged(self) -> None:
        mock_queryset = MagicMock()

        result = filter_publications_by_category(mock_queryset, "INVALID_CATEGORY")

        mock_queryset.filter.assert_not_called()
        self.assertEqual(result, mock_queryset)

    def test_filter_with_none_category_returns_unchanged(self) -> None:
        mock_queryset = MagicMock()

        result = filter_publications_by_category(mock_queryset, None)

        mock_queryset.filter.assert_not_called()
        self.assertEqual(result, mock_queryset)

    def test_filter_with_empty_category_returns_unchanged(self) -> None:
        mock_queryset = MagicMock()

        result = filter_publications_by_category(mock_queryset, "")

        mock_queryset.filter.assert_not_called()
        self.assertEqual(result, mock_queryset)


class SearchPublicationsTest(TestCase):
    def test_search_filters_by_title_and_description(self) -> None:
        mock_queryset = MagicMock()
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered

        result = search_publications(mock_queryset, "test query")

        mock_queryset.filter.assert_called_once()
        self.assertEqual(result, mock_filtered)

    def test_empty_search_returns_unchanged(self) -> None:
        mock_queryset = MagicMock()

        result = search_publications(mock_queryset, "")

        mock_queryset.filter.assert_not_called()
        self.assertEqual(result, mock_queryset)


class PaginatePublicationsTest(TestCase):
    def test_paginate_returns_page_object(self) -> None:
        items = list(range(30))

        result = paginate_publications(items, page_number=1, per_page=12)

        self.assertEqual(len(result), 12)
        self.assertEqual(result.number, 1)
        self.assertTrue(result.has_next())

    def test_paginate_second_page(self) -> None:
        items = list(range(30))

        result = paginate_publications(items, page_number=2, per_page=12)

        self.assertEqual(len(result), 12)
        self.assertEqual(result.number, 2)
        self.assertTrue(result.has_previous())

    def test_paginate_last_page(self) -> None:
        items = list(range(30))

        result = paginate_publications(items, page_number=3, per_page=12)

        self.assertEqual(len(result), 6)
        self.assertEqual(result.number, 3)
        self.assertFalse(result.has_next())

    def test_paginate_with_none_page_returns_first(self) -> None:
        items = list(range(30))

        result = paginate_publications(items, page_number=None, per_page=12)

        self.assertEqual(result.number, 1)

    def test_paginate_with_invalid_page_returns_last(self) -> None:
        items = list(range(30))

        result = paginate_publications(items, page_number=999, per_page=12)

        self.assertEqual(result.number, 3)  # Last page

    def test_paginate_with_custom_per_page(self) -> None:
        items = list(range(20))

        result = paginate_publications(items, page_number=1, per_page=5)

        self.assertEqual(len(result), 5)
        self.assertEqual(result.paginator.num_pages, 4)
