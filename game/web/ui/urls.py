from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("play", views.play_state, name="ui-play"),
    path("nav", views.nav_state, name="ui-nav"),
    path("dashboard", views.dashboard_state, name="ui-dashboard"),
    path("bank", views.bank_state, name="ui-bank"),
    path("processing", views.processing_state, name="ui-processing"),
    path(
        "shipyard",
        RedirectView.as_view(
            url="shop?room=Meridian%20Civil%20Shipyard",
            permanent=False,
        ),
        name="ui-shipyard-redirect",
    ),
    path("shop", views.shop_state, name="ui-shop"),
    path("shop/inspect", views.shop_inspect, name="ui-shop-inspect"),
    path("shop/buy", views.shop_buy, name="ui-shop-buy"),
    path("market", views.market_state, name="ui-market"),
    path("claims-market", views.claims_market_state, name="ui-claims-market"),
    path("resources", views.resources_state, name="ui-resources"),
    path("mine/claims", views.mine_claims, name="ui-mine-claims"),
    path("mine/deploy", views.mine_deploy, name="ui-mine-deploy"),
    path("mine/undeploy", views.mine_undeploy, name="ui-mine-undeploy"),
]
