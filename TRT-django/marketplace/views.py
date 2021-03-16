from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Account, Item
from .forms import AccountForm, ItemForm
from utils import CASClient

import cloudinary
import cloudinary.uploader
import cloudinary.api

import datetime

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


def editItem(request):
    messages.success(
        request, "This is a demonstration of the messages system via the base template!"
    )
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# delete item


def deleteItem(request):
    messages.success(
        request, "This is a demonstration of the messages system via the base template!"
    )
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# personal transactions page


def listTransactions(request):
    messages.success(
        request, "This is a demonstration of the messages system via the base template!"
    )
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# new transaction
# POST request with pk of item to purchase will create new transaction


def newTransaction(request):
    messages.success(
        request, "This is a demonstration of the messages system via the base template!"
    )
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# accept transaction
# seller accepts transaction


def acceptTransaction(request):
    messages.success(
        request, "This is a demonstration of the messages system via the base template!"
    )
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# confirm transaction
# seller/buyer confirms transaction


def confirmTransaction(request):
    messages.success(
        request, "This is a demonstration of the messages system via the base template!"
    )
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# cancel transaction
# seller/buyer cancels transaction


def cancelTransaction(request):
    messages.success(
        request, "This is a demonstration of the messages system via the base template!"
    )
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

            messages.success(request, "Account edited!")

    # did not receive form data via POST, so send stored account form
    else:
        account_form = AccountForm(instance=account)

    context = {"account_form": account_form}
    return render(request, "marketplace/edit_account.html", context)


# ----------------------------------------------------------------------


def logout(request):
    request.session.pop("username")
    return redirect(CASClient.getLogoutUrl())
