from django.contrib import admin
from .models import Account, Category, Item, Transaction, ItemLog, TransactionLog

# Register your models here.
# followed Django documentation
admin.site.register(Account)
admin.site.register(Category)
admin.site.register(Item)
admin.site.register(Transaction)
admin.site.register(ItemLog)
admin.site.register(TransactionLog)