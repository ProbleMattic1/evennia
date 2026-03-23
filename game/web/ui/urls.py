from django.urls import path

from . import views

urlpatterns = [
    path("play", views.play_state, name="ui-play"),
    path("bank", views.bank_state, name="ui-bank"),
    path("shipyard", views.shipyard_state, name="ui-shipyard"),
    path("shop", views.shop_state, name="ui-shop"),
]
