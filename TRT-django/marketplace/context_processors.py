# custom context processors to include common template context data
from .models import Account


def account(request):
    account = None
    if "username" in request.session:
        account = Account.objects.get(username=request.session.get("username"))
    return {"account": account}
