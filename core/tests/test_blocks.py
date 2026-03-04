import pytest

from core.blocks import ALL_BLOCKS


@pytest.mark.django_db
def test_mock_block_value_handles_all_block_types() -> None:
    from core.tests.utils.blocks import mock_block_value

    for block_type in ALL_BLOCKS:
        value = mock_block_value(block_type)
        assert value is not None

        block_definition = ALL_BLOCKS[block_type]
        # Check that the mock value is compliant with the block definition
        block_definition.clean(block_definition.normalize(value))
