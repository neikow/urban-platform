import pytest


@pytest.mark.django_db
def test_mock_block_value_handles_all_block_types():
    from core.blocks import BlockTypes
    from core.tests.utils.blocks import mock_block_value

    for [block_type, block] in BlockTypes:
        value = mock_block_value(block_type)
        assert value is not None
