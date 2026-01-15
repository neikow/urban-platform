from wagtail.admin.viewsets.model import ModelViewSet
from wagtail import hooks
from .models import NeighborhoodAssociation


class NeighborhoodAssociationViewSet(ModelViewSet):
    model = NeighborhoodAssociation
    menu_icon = "group"
    add_to_settings_menu = True
    exclude_from_explorer = False
    list_display = ["neighborhood", "contact_email", "contact_phone", "website"]
    search_fields = ["neighborhood__name", "contact_email", "website"]
    form_fields = ["neighborhood", "contact_email", "contact_phone", "website"]


@hooks.register("register_admin_viewset")
def register_neighborhood_association_viewset():
    return NeighborhoodAssociationViewSet("neighborhood_association")
