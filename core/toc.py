from dataclasses import dataclass

from bs4 import BeautifulSoup
from slugify import slugify
from wagtail.blocks import StreamValue


@dataclass
class TableOfContentsItem:
    title: str
    id: str
    level: int


def generate_header_ids(block: StreamValue.StreamChild) -> None:
    html = block.value.source

    soup = BeautifulSoup(html, "html.parser")
    for header in soup.find_all(["h2", "h3", "h4"]):
        header_id = slugify(header.get_text())
        header["id"] = header_id
    block.value.source = str(soup)


def get_table_of_contents(content: StreamValue) -> list[TableOfContentsItem]:
    toc: list[TableOfContentsItem] = []

    for block in content:
        if block.block_type == "text":
            html = block.value.source

            soup = BeautifulSoup(html, "html.parser")
            for header in soup.find_all(["h2", "h3", "h4"]):
                level = int(header.name[1])
                title = header.get_text()
                id_attr = header.get("id", "")
                if not id_attr:
                    id_attr = slugify(title)

                if not id_attr or not isinstance(id_attr, str):
                    continue

                toc.append(TableOfContentsItem(title=title, id=id_attr, level=level))

    return toc
