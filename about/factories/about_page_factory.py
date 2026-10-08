from core.tests.utils.factories import BaseWagtailPageFactory
from core.tests.utils.faker_shortcuts import fake
import factory
from about.models import AboutIndexPage, AboutWebsitePage, AboutCommissionPage, AboutDevTeamPage


def text_content() -> list[tuple[str, str]]:
    return [("text", f"<p>{fake.paragraph()}</p>")]


class AboutIndexPageFactory(BaseWagtailPageFactory):
    class Meta:
        model = AboutIndexPage

    title = "À propos"
    slug = "a-propos"


class AboutWebsitePageFactory(BaseWagtailPageFactory):
    class Meta:
        model = AboutWebsitePage

    title = "La plateforme"
    slug = "la-plateforme"
    content = factory.LazyFunction(text_content)
    show_in_menus = True


class AboutCommissionPageFactory(BaseWagtailPageFactory):
    class Meta:
        model = AboutCommissionPage

    title = "L'association"
    slug = "association"
    content = factory.LazyFunction(text_content)
    show_in_menus = True


class AboutDevTeamPageFactory(BaseWagtailPageFactory):
    class Meta:
        model = AboutDevTeamPage

    title = "L'équipe de développement"
    slug = "equipe-de-developpement"
    content = factory.LazyFunction(text_content)
    show_in_menus = True
