"""Ready-made page content, so editors do not start from a blank page.

A page model offers templates through a ``page_templates`` attribute: the
dotted path of a tuple of :class:`PageTemplate` (a path, so that models and
template modules do not import each other).

Templates are used in two places (see ``core.views.page_templates`` and the
hooks in ``core.wagtail_hooks``):

- **Creating a page**: a chooser comes before the editor. The chosen template
  fills the new page through the ``init_new_page`` signal, so nothing is saved
  until the editor saves.
- **"Start from a template"** on an existing page: the template replaces the
  content in a new *draft*. The live page changes only when an editor
  publishes, and the previous version stays in the page history.

Templates only fill the ``content`` StreamField (and, at creation, a few
other fields): titles, summaries and images stay the editor's.
"""

import json
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from django.utils.html import strip_tags
from django.utils.module_loading import import_string
from django_stubs_ext import StrOrPromise
from wagtail.models import Page

RawBlock = dict[str, Any]


# --- Building blocks for template content --------------------------------------


def rich_text(html: str) -> RawBlock:
    """A text block of the publication pages (``AugmentedRichTextBlock``)."""
    return {
        "type": "rich_text",
        "value": {"justification": "left", "text": html, "max_width": None},
    }


def faq(*questions: tuple[str, str]) -> RawBlock:
    return {
        "type": "faq",
        "value": [{"question": question, "answer": answer} for question, answer in questions],
    }


def outline_entry(block: RawBlock, page_class: type[Page]) -> str:
    """How a block shows in a template's outline: its title, else its block label."""
    value = block["value"]
    if isinstance(value, dict):
        if value.get("title"):
            return str(value["title"])
        heading = re.search(r"<h2[^>]*>(.*?)</h2>", str(value.get("text", "")), re.S)
        if heading:
            return strip_tags(heading.group(1)).strip()
    child = page_class._meta.get_field("content").stream_block.child_blocks.get(block["type"])  # type: ignore[union-attr]
    return str(child.label) if child else block["type"]


# --- Templates -------------------------------------------------------------------


@dataclass(frozen=True)
class PageTemplate:
    slug: str
    name: StrOrPromise
    description: StrOrPromise
    blocks: tuple[RawBlock, ...]
    # Other fields set when a page is created from the template.
    fields: dict[str, Any] = field(default_factory=dict)
    # Block types of the current content kept, at the top, when the template
    # replaces it (the home page keeps its hero and its photo).
    keep: tuple[str, ...] = ()

    def outline(self, page_class: type[Page]) -> list[str]:
        return [outline_entry(block, page_class) for block in self.blocks]

    def content(self, current: list[RawBlock] | None = None) -> list[RawBlock]:
        """The new stream data, with the ``keep`` blocks of ``current`` (raw data)."""
        kept = [block for block in current or [] if block["type"] in self.keep][:1]
        return kept + [dict(block) for block in self.blocks]

    def fill(self, page: Page) -> None:
        """Fill a page being created."""
        page.content = json.dumps(self.content())  # type: ignore[attr-defined]
        for name, value in self.fields.items():
            setattr(page, name, value)


def templates_for(page_class: type[Page]) -> tuple[PageTemplate, ...]:
    path = getattr(page_class, "page_templates", None)
    return import_string(path) if path else ()


def get_template(page_class: type[Page], slug: str) -> PageTemplate | None:
    return next((template for template in templates_for(page_class) if template.slug == slug), None)


# The template chosen for the page being created in this request: set by the
# ``before_create_page`` hook, read by the ``init_new_page`` receiver.
pending_template: ContextVar[tuple[type[Page], PageTemplate] | None] = ContextVar(
    "pending_template", default=None
)


def fill_new_page(sender: Any, page: Page, parent: Page, **kwargs: Any) -> None:
    """``init_new_page`` receiver: fill the page being created with the chosen template."""
    pending = pending_template.get()
    pending_template.set(None)
    if pending is not None and isinstance(page, pending[0]):
        pending[1].fill(page)
