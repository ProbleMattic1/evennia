from django.urls import path

from . import views

urlpatterns = [
    path("play", views.play_state, name="ui-play"),
    path("bank", views.bank_state, name="ui-bank"),
    path("shipyard", views.shipyard_state, name="ui-shipyard"),
    path("shop", views.shop_state, name="ui-shop"),
    path("shipyard/inspect", views.shipyard_inspect, name="ui-shipyard-inspect"),
    path("shipyard/buy", views.shipyard_buy, name="ui-shipyard-buy"),
    path("shop/inspect", views.shop_inspect, name="ui-shop-inspect"),
    path("shop/buy", views.shop_buy, name="ui-shop-buy"),
]
