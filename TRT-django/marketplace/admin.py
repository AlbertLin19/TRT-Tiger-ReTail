from django.contrib import admin
from .models import UserProfile, Category, Item, Transaction

# Register your models here.
# followed Django documentation
admin.site.register(UserProfile)
admin.site.register(Category)
admin.site.register(Item)
admin.site.register(Transaction)