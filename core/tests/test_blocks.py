import pytest

from core.blocks import DEPRECATED_BLOCK_TYPES, ALL_BLOCK_TYPES


@pytest.mark.django_db
def test_mock_block_value_handles_all_block_types() -> None:
    from core.tests.utils.blocks import mock_block_value

    for block_type in ALL_BLOCK_TYPES:
        if block_type in DEPRECATED_BLOCK_TYPES:
            continue

        value = mock_block_value(block_type)
        assert value is not None


@pytest.mark.django_db
def test_mock_block_value_raises_for_deprecated_block_types() -> None:
    from core.tests.utils.blocks import mock_block_value

    for block_type in DEPRECATED_BLOCK_TYPES:
        with pytest.raises(
            RuntimeError, match=f"{block_type} is deprecated and should not be used."
        ):
            mock_block_value(block_type)
