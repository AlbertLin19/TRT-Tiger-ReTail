# custom context processors to include common template context data
from .models import Account


def account(request):
    account = None
    if "username" in request.session:
        account = Account.objects.get(username=request.session.get("username"))
    return {"account": account}


def unseenNotifications(request):
    if "username" in request.session:
        account = Account.objects.get(username=request.session.get("username"))
    else:
        return {"unseen_notifications": []}

    return {"unseen_notifications": account.notifications.filter(seen=False)}