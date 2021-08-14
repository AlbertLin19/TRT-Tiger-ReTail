from django.contrib import admin
from .models import (
    Account,
    Category,
    Item,
    Transaction,
    ItemLog,
    TransactionLog,
    AlbumImage,
    ItemRequest,
    Message,
    Notification,
    ItemFlag,
    ItemRequestFlag,
)

# Register your models here.
# followed Django documentation
admin.site.register(Account)
admin.site.register(Category)
admin.site.register(Item)
admin.site.register(Transaction)
admin.site.register(ItemLog)
admin.site.register(TransactionLog)
admin.site.register(AlbumImage)
admin.site.register(ItemRequest)
admin.site.register(Message)
admin.site.register(Notification)
admin.site.register(ItemFlag)
admin.site.register(ItemRequestFlag)