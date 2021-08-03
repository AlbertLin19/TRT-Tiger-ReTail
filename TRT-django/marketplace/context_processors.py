# custom context processors to include common template context data
from .models import Account, Item, Transaction, Category
from django.conf import settings


def account(request):
    account = None
    if "username" in request.session:
        account = Account.objects.get(username=request.session.get("username"))
    return {"account": account}


def item(request):
    return {"Item": Item}


def transaction(request):
    return {"Transaction": Transaction}


def admin(request):
    return {
        "admin": "username" in request.session
        and request.session.get("username")
        in [
            netid + suffix
            for netid in settings.ADMIN_NETIDS
            for suffix in settings.ALT_ACCOUNT_SUFFIXES
        ]
    }

def categories(request):
    return {"categories": Category.objects.all()}