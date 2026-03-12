from core.tests.utils.factories import BaseWagtailPageFactory
import factory
from about.models import AboutIndexPage, AboutWebsitePage, AboutCommissionPage, AboutDevTeamPage


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
    content = factory.Faker("paragraph")
    show_in_menus = True


class AboutCommissionPageFactory(BaseWagtailPageFactory):
    class Meta:
        model = AboutCommissionPage

    title = "La commission urbanisme"
    slug = "commission-urbanisme"
    content = factory.Faker("paragraph")
    show_in_menus = True


class AboutDevTeamPageFactory(BaseWagtailPageFactory):
    class Meta:
        model = AboutDevTeamPage

    title = "L'équipe de développement"
    slug = "equipe-de-developpement"
    content = factory.Faker("paragraph")
    show_in_menus = True
