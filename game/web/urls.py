from django.urls import include, path

from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

urlpatterns = [
    path("ui/", include("web.ui.urls")),
    path("admin/", include("web.admin.urls")),
]

urlpatterns = urlpatterns + evennia_default_urlpatterns
