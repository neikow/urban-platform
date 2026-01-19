import pytest

from pedagogy.factories.pedagogy_card_factory import PedagogyCardPageFactory


@pytest.mark.django_db
def test_table_of_contents_generation():
    page = PedagogyCardPageFactory.build(
        content=[
            (
                "text",
                """
      <h2>a</h2>
      <p>b</p>
      <h3>c</h3>
      <h2>d</h2>
      <p>e</p>
      <h4>f</h4>
      <h3>g</h3>
      <p>h</p>
      """,
            ),
        ],
    )

    page.clean()

    toc = page.table_of_contents

    expected_toc = [
        {"title": "a", "id": "a", "level": 2},
        {"title": "c", "id": "c", "level": 3},
        {"title": "d", "id": "d", "level": 2},
        {"title": "f", "id": "f", "level": 4},
        {"title": "g", "id": "g", "level": 3},
    ]
    assert len(toc) == len(expected_toc)
    for toc_item, expected_item in zip(toc, expected_toc):
        assert toc_item.title == expected_item["title"]
        assert toc_item.id == expected_item["id"]
        assert toc_item.level == expected_item["level"]
