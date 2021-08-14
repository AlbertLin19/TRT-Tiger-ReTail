from django import forms
from django.forms.widgets import NumberInput
from .models import Account, Item, ItemRequest, ItemFlag, ItemRequestFlag
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "name",
            "description",
            "price",
            "negotiable",
            "deadline",
            "condition",
            "categories",
            "image",
        ]
        labels = {
            "name": "",
            "deadline": "",
            "price": "",
            "negotiable": "",
            "image": "",
        }
        widgets = {
            "description": forms.Textarea(attrs={"cols": 80, "rows": 3}),
            "name": forms.TextInput(attrs={"class": "only-round-right"}),
            "price": forms.TextInput(attrs={"class": "only-round-right"}),
            "deadline": forms.NumberInput(
                attrs={"type": "date", "class": "only-round-right"}
            ),
        }


class ItemRequestForm(forms.ModelForm):
    class Meta:
        model = ItemRequest
        fields = [
            "name",
            "description",
            "price",
            "negotiable",
            "deadline",
            "condition",
            "categories",
            "image",
        ]
        labels = {
            "name": "",
            "deadline": "",
            "price": "",
            "negotiable": "",
            "image": "",
        }
        widgets = {
            "description": forms.Textarea(attrs={"cols": 80, "rows": 3}),
            "name": forms.TextInput(attrs={"class": "only-round-right"}),
            "price": forms.TextInput(attrs={"class": "only-round-right"}),
            "deadline": forms.NumberInput(
                attrs={"type": "date", "class": "only-round-right"}
            ),
        }


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = [
            "name",
            "email",
            "contact",
        ]
        labels = {
            "name": "",
            "email": "",
            "contact": "",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "only-round-right"}),
            "email": forms.TextInput(attrs={"class": "only-round-right"}),
            "contact": forms.Textarea(attrs={"cols": 80, "rows": 3}),
        }


class ItemFlagForm(forms.ModelForm):
    class Meta:
        model = ItemFlag 
        fields = [
            "text",
        ]
        labels = {
            "text": "Explanation (optional)",
        }

class ItemRequestFlagForm(forms.ModelForm):
    class Meta:
        model = ItemRequestFlag 
        fields = [
            "text",
        ]
        labels = {
            "text": "Explanation (optional)",
        }