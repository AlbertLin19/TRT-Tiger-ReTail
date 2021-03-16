from django.urls import path
from . import views

urlpatterns = [
    path("", views.gallery, name="gallery"),
    path("items/list/", views.listItems, name="list_items"),
    path("items/new/", views.newItem, name="new_item"),
    path("items/<int:pk>/edit/", views.editItem, name="edit_item"),
    path("items/<int:pk>/delete/", views.deleteItem, name="delete_item"),
    path("transactions/list/", views.listTransactions, name="list_transactions"),
    path("transactions/new/", views.newTransaction, name="new_transaction"),
    path(
        "transactions/<int:pk>/accept/",
        views.acceptTransaction,
        name="accept_transaction",
    ),
    path(
        "transactions/<int:pk>/confirm/",
        views.confirmTransaction,
        name="confirm_transaction",
    ),
    path(
        "transactions/<int:pk>/cancel/",
        views.cancelTransaction,
        name="cancel_transaction",
    ),
    path("account/edit/", views.editAccount, name="edit_account"),
    path("account/login/", views.editAccount, name="login"),
    path("account/logout/", views.logout, name="logout"),
]
