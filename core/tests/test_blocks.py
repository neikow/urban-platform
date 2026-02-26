import pytest


@pytest.mark.django_db
def test_mock_block_value_handles_all_block_types() -> None:
    from core.blocks import CONTENT_BLOCK_TYPES
    from core.tests.utils.blocks import mock_block_value

    for [block_type, block] in CONTENT_BLOCK_TYPES:
        value = mock_block_value(block_type)
        assert value is not None
