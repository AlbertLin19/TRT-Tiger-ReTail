from django import forms
from django.forms.widgets import NumberInput
from .models import Account, Item
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "name",
            "description",
            "price",
            "deadline",
            "condition",
            "categories",
            "image",
        ]
        widgets = {
            'description': forms.Textarea(attrs={'cols': 80, 'rows': 3})
        }

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "name",
            "email",
        ]