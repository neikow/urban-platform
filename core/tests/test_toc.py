import pytest
from unittest.mock import MagicMock

from wagtail.rich_text import RichText

from core.toc import (
    TableOfContentsItem,
    generate_header_ids,
    get_table_of_contents,
)


class TestGenerateHeaderIds:
    """Tests for the generate_header_ids function."""

    def test_generate_header_ids_with_text_block(self) -> None:
        """Test that generate_header_ids works with deprecated text block type."""
        block = MagicMock()
        block.block_type = "text"
        block.value = RichText("<h2>Introduction</h2><p>Content</p><h3>Details</h3>")

        generate_header_ids(block)

        assert 'id="introduction"' in block.value.source
        assert 'id="details"' in block.value.source

    def test_generate_header_ids_with_rich_text_block(self) -> None:
        """Test that generate_header_ids works with AugmentedRichTextBlock (rich_text)."""
        block = MagicMock()
        block.block_type = "rich_text"
        block.value = {
            "text": RichText("<h2>Section Title</h2><p>Paragraph</p><h3>Subsection</h3>")
        }

        generate_header_ids(block)

        assert 'id="section-title"' in block.value["text"].source
        assert 'id="subsection"' in block.value["text"].source

    def test_generate_header_ids_with_rich_text_block_all_header_levels(self) -> None:
        """Test that generate_header_ids handles h2, h3, and h4 in rich_text blocks."""
        block = MagicMock()
        block.block_type = "rich_text"
        block.value = {
            "text": RichText(
                "<h2>Level 2</h2><h3>Level 3</h3><h4>Level 4</h4><p>Regular paragraph</p>"
            )
        }

        generate_header_ids(block)

        assert 'id="level-2"' in block.value["text"].source
        assert 'id="level-3"' in block.value["text"].source
        assert 'id="level-4"' in block.value["text"].source

    def test_generate_header_ids_with_rich_text_block_special_characters(self) -> None:
        """Test that generate_header_ids slugifies headers with special characters."""
        block = MagicMock()
        block.block_type = "rich_text"
        block.value = {"text": RichText("<h2>L'introduction à la France</h2>")}

        generate_header_ids(block)

        assert 'id="l-introduction-a-la-france"' in block.value["text"].source

    def test_generate_header_ids_ignores_other_block_types(self) -> None:
        """Test that generate_header_ids does nothing for non-text/rich_text blocks."""
        block = MagicMock()
        block.block_type = "image"
        block.value = {"image": "some_image"}

        # Should not raise an error
        generate_header_ids(block)

        # Value should remain unchanged
        assert block.value == {"image": "some_image"}


class TestGetTableOfContents:
    """Tests for the get_table_of_contents function."""

    def test_get_table_of_contents_with_text_block(self) -> None:
        """Test that get_table_of_contents extracts headers from text blocks."""
        block = MagicMock()
        block.block_type = "text"
        block.value = RichText(
            '<h2 id="intro">Introduction</h2><p>Some content</p><h3 id="details">Details</h3>'
        )

        content = [block]

        toc = get_table_of_contents(content)

        assert len(toc) == 2
        assert toc[0] == TableOfContentsItem(title="Introduction", id="intro", level=2)
        assert toc[1] == TableOfContentsItem(title="Details", id="details", level=3)

    def test_get_table_of_contents_with_rich_text_block(self) -> None:
        """Test that get_table_of_contents extracts headers from rich_text blocks."""
        block = MagicMock()
        block.block_type = "rich_text"
        block.value = {
            "text": RichText(
                '<h2 id="overview">Overview</h2>'
                "<p>Some content</p>"
                '<h3 id="background">Background</h3>'
                '<h4 id="history">History</h4>'
            )
        }

        content = [block]

        toc = get_table_of_contents(content)

        assert len(toc) == 3
        assert toc[0] == TableOfContentsItem(title="Overview", id="overview", level=2)
        assert toc[1] == TableOfContentsItem(title="Background", id="background", level=3)
        assert toc[2] == TableOfContentsItem(title="History", id="history", level=4)

    def test_get_table_of_contents_with_mixed_blocks(self) -> None:
        """Test that get_table_of_contents works with mixed text and rich_text blocks."""
        text_block = MagicMock()
        text_block.block_type = "text"
        text_block.value = RichText('<h2 id="section-1">Section 1</h2>')

        rich_text_block = MagicMock()
        rich_text_block.block_type = "rich_text"
        rich_text_block.value = {"text": RichText('<h2 id="section-2">Section 2</h2>')}

        image_block = MagicMock()
        image_block.block_type = "image"
        image_block.value = {"image": "some_image"}

        content = [text_block, image_block, rich_text_block]

        toc = get_table_of_contents(content)

        assert len(toc) == 2
        assert toc[0] == TableOfContentsItem(title="Section 1", id="section-1", level=2)
        assert toc[1] == TableOfContentsItem(title="Section 2", id="section-2", level=2)

    def test_get_table_of_contents_generates_id_if_missing(self) -> None:
        """Test that get_table_of_contents generates an id from title if not present."""
        block = MagicMock()
        block.block_type = "rich_text"
        block.value = {"text": RichText("<h2>Auto Generated ID</h2>")}

        content = [block]

        toc = get_table_of_contents(content)

        assert len(toc) == 1
        assert toc[0].title == "Auto Generated ID"
        assert toc[0].id == "auto-generated-id"
        assert toc[0].level == 2

    def test_get_table_of_contents_empty_content(self) -> None:
        """Test that get_table_of_contents returns empty list for empty content."""
        content: list = []

        toc = get_table_of_contents(content)

        assert toc == []

    def test_get_table_of_contents_no_headers(self) -> None:
        """Test that get_table_of_contents returns empty list when no headers present."""
        block = MagicMock()
        block.block_type = "rich_text"
        block.value = {"text": RichText("<p>Just a paragraph</p><p>Another paragraph</p>")}

        content = [block]

        toc = get_table_of_contents(content)

        assert toc == []

    def test_get_table_of_contents_with_rich_text_block_preserves_order(self) -> None:
        """Test that get_table_of_contents preserves header order across multiple rich_text blocks."""
        block1 = MagicMock()
        block1.block_type = "rich_text"
        block1.value = {"text": RichText('<h2 id="first">First</h2><h3 id="second">Second</h3>')}

        block2 = MagicMock()
        block2.block_type = "rich_text"
        block2.value = {"text": RichText('<h2 id="third">Third</h2><h4 id="fourth">Fourth</h4>')}

        content = [block1, block2]

        toc = get_table_of_contents(content)

        assert len(toc) == 4
        assert [item.title for item in toc] == ["First", "Second", "Third", "Fourth"]
        assert [item.level for item in toc] == [2, 3, 2, 4]
