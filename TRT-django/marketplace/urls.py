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
    path("purchases/<int:pk>/confirm/", views.confirmPurchase, name="confirm_purchase"),
    path("purchases/<int:pk>/cancel/", views.cancelPurchase, name="cancel_purchase"),
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
    path(
        "item_requests/<int:pk>/contact/",
        views.contactItemRequest,
        name="contact_item_request",
    ),
    path(
        "item_requests/browse/", views.browseItemRequests, name="browse_item_requests"
    ),
    path("inbox/", views.inbox, name="inbox"),
    path("inbox/<int:pk>/get/", views.getMessages, name="get_messages"),
    path("inbox/<int:pk>/get_relative/", views.getMessagesRelative, name="get_messages_relative"),
    path("inbox/send/", views.sendMessage, name="send_message"),
    path("notifications/list/", views.listNotifications, name="list_notifications"),
    path("notifications/get/", views.getNotifications, name="get_notifications"),
    path("notifications/count/", views.countNotifications, name="count_notifications"),
    path("notifications/see/", views.seeNotifications, name="see_notifications"),
    path("account/activity/", views.accountActivity, name="account_activity"),
    path("account/edit/", views.editAccount, name="edit_account"),
    path("account/login/", views.editAccount, name="login"),
    path("account/logout/", views.logout, name="logout"),
    path("account/email/verify/<str:token>/", views.verifyEmail, name="verify_email"),
    path("account/cycle/", views.cycleAccount, name="cycle_account"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
]
