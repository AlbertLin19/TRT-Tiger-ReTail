from django.urls import path
from . import views

urlpatterns = [
    path("", views.gallery, name="gallery"),
    path("items/list/", views.listItems, name="list_items"),
    path("items/new/", views.newItem, name="new_item"),
    path("items/<int:pk>/edit/", views.editItem, name="edit_item"),
    path("items/<int:pk>/delete/", views.deleteItem, name="delete_item"),
    path("purchases/list/", views.listPurchases, name="list_purchases"),
    path("purchases/new/", views.newPurchase, name="new_purchase"),
    path(
        "purchases/<int:pk>/accept/",
        views.acceptPurchase,
        name="accept_purchase",
    ),
    path(
        "purchases/<int:pk>/confirm/",
        views.confirmPurchase,
        name="confirm_purchase",
    ),
    path(
        "purchases/<int:pk>/cancel/",
        views.cancelPurchase,
        name="cancel_purchase",
    ),
    path("account/edit/", views.editAccount, name="edit_account"),
    path("account/login/", views.editAccount, name="login"),
    path("account/logout/", views.logout, name="logout"),
]
