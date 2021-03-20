from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Account, Item, Transaction
from .forms import AccountForm, ItemForm
from utils import CASClient

import cloudinary
import cloudinary.uploader
import cloudinary.api

import datetime

from django.core.exceptions import PermissionDenied, ValidationError

# ----------------------------------------------------------------------

# custom authentication_required decorator for protected views

# if user can be authenticated, call view as normal
# otherwise, redirect to CAS login page

# will ensure that an account with associated username exists


def authentication_required(view_function):
    def wrapper(request, *args, **kwargs):

        # if username in session, can call view as normal
        if "username" in request.session:
            return view_function(request, *args, **kwargs)

        # if request contains a ticket, try validating it
        if "ticket" in request.GET:
            username = CASClient.validate(
                request.build_absolute_uri(), request.GET["ticket"]
            )

            if username is not None:
                # store authenticated username,
                # check that associated Account exists, else create one,
                # call view as normal
                request.session["username"] = username
                if not Account.objects.filter(username=username).exists():
                    Account(username=username).save()
                return view_function(request, *args, **kwargs)

        # user could NOT be authenticated, so redirect to CAS login
        return redirect(CASClient.getLoginUrl(request.build_absolute_uri()))

    return wrapper


# ----------------------------------------------------------------------

# image gallery


def gallery(request):
    messages.success(
        request,
        "This is a demonstration of the common messages system via the base template!",
    )
    items = Item.objects.all()
    context = {"items": items}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# personal items page


@authentication_required
def listItems(request):
    account = Account.objects.get(username=request.session.get("username"))
    items = account.item_set.all()
    context = {"items": items}
    return render(request, "marketplace/list_items.html", context)


# ----------------------------------------------------------------------

# new item form
# GET requests get a blank form
# POST requests get a form with error feedback, else new item created
# and redirected to list items page


@authentication_required
def newItem(request):
    account = Account.objects.get(username=request.session.get("username"))

    # populate the Django model form and validate data
    if request.method == "POST":
        item_form = ItemForm(request.POST, request.FILES)
        if item_form.is_valid():
            # create new item, but do not save yet until changes made
            item = item_form.save(commit=False)
            item.seller = account
            item.posted_date = datetime.datetime.now()
            item.status = Item.AVAILABLE
            item.save()

            messages.success(request, "New item posted!")
            return redirect("list_items")

    # did not receive form data via POST, so send a blank form
    else:
        item_form = ItemForm()

    context = {"item_form": item_form}
    return render(request, "marketplace/new_item.html", context)


# ----------------------------------------------------------------------

# edit item form
# GET requests given pre-populated item form
# POST requests given form with error feedback, else item edited


@authentication_required
def editItem(request, pk):
    account = Account.objects.get(username=request.session.get("username"))

    # if the item does not belong to this account, permission denied
    item = Item.objects.get(pk=pk)
    if item.seller != account:
        raise PermissionDenied

    # populate the Django model form and validate data
    if request.method == "POST":
        item_form = ItemForm(request.POST, request.FILES, instance=item)
        if item_form.is_valid():
            # save changes to item
            item_form.save()

            messages.success(request, "Item updated!")

    # did not receive form data via POST, so send stored item form
    else:
        item_form = ItemForm(instance=item)
    context = {"item": item, "item_form": item_form}
    return render(request, "marketplace/edit_item.html", context)


# ----------------------------------------------------------------------

# delete item


@authentication_required
def deleteItem(request, pk):
    account = Account.objects.get(username=request.session.get("username"))

    # if the item does not belong to this account, permission denied
    item = Item.objects.get(pk=pk)
    if item.seller != account:
        raise PermissionDenied

    item.delete()
    messages.success(request, "Item deleted!")
    return redirect("list_items")


# ----------------------------------------------------------------------

# personal purchases page

@authentication_required
def listPurchases(request):
    account = Account.objects.get(username=request.session.get("username"))

    # get transactions for which user is the buyer
    transactions = Transaction.objects.filter(buyer=account)
    context = {'transactions': transactions}
    return render(request, "marketplace/list_purchases.html", context)


# ----------------------------------------------------------------------

# buyer makes new purchase
# POST request with pk of item to purchase will create new transaction

@authentication_required
def newPurchase(request):
    account = Account.objects.get(username=request.session.get("username"))

    # item must be available for a transaction to associate with
    pk = request.POST['pk']
    item = Item.objects.get(pk=pk)
    if item.status != Item.AVAILABLE:
        # rejected
        raise ValidationError

    transaction = Transaction(item=item, buyer=account, status=Transaction.INITIATED)
    transaction.save()
    return redirect("list_purchases")


# ----------------------------------------------------------------------

# confirm purchase
# buyer confirms purchase


def confirmPurchase(request, pk):
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# cancel purchase
# buyer cancels purchase


def cancelPurchase(request, pk):
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# seller accepts sale


def acceptSale(request, pk):
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# seller confirms sale


def confirmSale(request, pk):
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# seller cancels sale


def cancelSale(request, pk):
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# account settings page


@authentication_required
def editAccount(request):
    account = Account.objects.get(username=request.session.get("username"))

    # populate the Django model form and validate data
    if request.method == "POST":
        account_form = AccountForm(request.POST, instance=account)
        if account_form.is_valid():
            # save changes to the account
            account_form.save()

            messages.success(request, "Account updated!")

    # did not receive form data via POST, so send stored account form
    else:
        account_form = AccountForm(instance=account)

    context = {"account_form": account_form}
    return render(request, "marketplace/edit_account.html", context)


# ----------------------------------------------------------------------


def logout(request):
    request.session.pop("username")
    return redirect(CASClient.getLogoutUrl())
