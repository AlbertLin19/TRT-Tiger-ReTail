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
    path("purchases/<int:pk>/confirm/",
         views.confirmPurchase, name="confirm_purchase"),
    path("purchases/<int:pk>/cancel/",
         views.cancelPurchase, name="cancel_purchase"),
    path("sales/<int:pk>/accept/", views.acceptSale, name="accept_sale"),
    path("sales/<int:pk>/confirm/", views.confirmSale, name="confirm_sale"),
    path("sales/<int:pk>/cancel/", views.cancelSale, name="cancel_sale"),
    path("item_requests/list/", views.listItemRequests, name="list_item_requests"),
    path("item_requests/new/", views.newItemRequest, name="new_item_request"),
    path(
        "item_requests/<int:pk>/edit/",
        views.editItemRequest,
        name="edit_item_request",
    ),
    path(
        "item_requests/<int:pk>/delete/",
        views.deleteItemRequest,
        name="delete_item_request",
    ),
    path("account/edit/", views.editAccount, name="edit_account"),
    path("account/login/", views.editAccount, name="login"),
    path("account/logout/", views.logout, name="logout"),
    path("account/email/verify/<str:token>/",
         views.verifyEmail, name="verify_email"),

    path("faq", views.faq, name="faq"),
]
