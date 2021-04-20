# custom context processors to include common template context data
from .models import Account, Item, Transaction


def account(request):
    account = None
    if "username" in request.session:
        account = Account.objects.get(username=request.session.get("username"))
    return {"account": account}


def item(request):
    return {"Item": Item}


def transaction(request):
    return {"Transaction": Transaction}