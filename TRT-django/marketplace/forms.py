from django import forms
from .models import Account, Item


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "name",
            "deadline",
            "price",
            "condition",
            "categories",
            "description",
            "image",
        ]


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "name",
            "email",
        ]