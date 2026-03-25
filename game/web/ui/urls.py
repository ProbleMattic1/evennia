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
    path("claims-market/purchase", views.claims_market_purchase, name="ui-claims-market-purchase"),
    path("claims-market/list-property", views.claims_market_list_property, name="ui-claims-market-list-property"),
    path("claims-market/list-claim", views.claims_market_list_claim, name="ui-claims-market-list-claim"),
    path(
        "claims-market/purchase-listed-claim",
        views.claims_market_purchase_listed_claim,
        name="ui-claims-market-purchase-listed-claim",
    ),
    path("claim/detail", views.claim_detail_state, name="ui-claim-detail"),
    path("resources", views.resources_state, name="ui-resources"),
    path("mine/claims", views.mine_claims, name="ui-mine-claims"),
    path("mine/deploy", views.mine_deploy, name="ui-mine-deploy"),
    path("mine/undeploy", views.mine_undeploy, name="ui-mine-undeploy"),
    path("mine/reactivate", views.mine_reactivate, name="ui-mine-reactivate"),
    path("package/list", views.package_list_for_sale, name="ui-package-list"),
    path("package/listings", views.package_listings_state, name="ui-package-listings"),
    path("package/buy", views.package_buy_listed, name="ui-package-buy"),
]
