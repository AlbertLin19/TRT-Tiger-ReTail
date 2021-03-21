from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import Account, Item, Transaction
from .forms import AccountForm, ItemForm
from utils import CASClient

import cloudinary
import cloudinary.uploader
import cloudinary.api

import datetime

from django.core.exceptions import PermissionDenied

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
            # send confirmation email
            send_mail('Item Post Confirmation', 'yeppers peppers', settings.EMAIL_HOST_USER, [account.email], fail_silently=False)
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

    # if item is frozen or complete, do not allow editing
    if item.status != item.AVAILABLE:
        messages.warning(request, "Cannot edit an item in the unavailable state.")
        return redirect("list_items")

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

    # if item is frozen or complete, do not allow deleting
    if item.status != item.AVAILABLE:
        messages.warning(request, "Cannot delete an item in the unavailable state.")
        return redirect("list_items")

    item.delete()
    messages.success(request, "Item deleted!")
    return redirect("list_items")


# ----------------------------------------------------------------------

# personal purchases page

@authentication_required
def listPurchases(request):
    account = Account.objects.get(username=request.session.get("username"))

    # get purchases for which user is the buyer
    purchases = Transaction.objects.filter(buyer=account)
    context = {'purchases': purchases}
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
        messages.warning(request, "Item unavailable for purchase.")
        return redirect("gallery")

    # buyer must not be the seller of this item
    if item.seller == account:
        # rejected
        messages.warning(request, "Cannot purchase an item you are selling.")
        return redirect("gallery")

    # freeze item
    item.status = Item.FROZEN
    item.save()

    purchase = Transaction(item=item, buyer=account, status=Transaction.INITIATED)
    purchase.save()

    return redirect("list_purchases")


# ----------------------------------------------------------------------

# confirm purchase
# buyer confirms purchase

@authentication_required
def confirmPurchase(request, pk):
    account = Account.objects.get(username=request.session.get("username"))

    purchase = Transaction.objects.get(pk=pk)

    # must be the buyer of this transaction
    if purchase.buyer != account:
        # rejected
        raise PermissionDenied

    # transaction cannot be INITIATED, S_PENDING, COMPLETE, or CANCELLED
    if purchase.status == Transaction.INITIATED:
        messages.warning(request, "Cannot confirm - awaiting seller acknowledgement.")
    elif purchase.status == Transaction.S_PENDING:
        messages.warning(request, "Already confirmed - awaiting seller confirmation.")
    elif purchase.status == Transaction.COMPLETE:
        messages.warning(request, "Already confirmed - purchase has already been completed.")
    elif purchase.status == Transaction.CANCELLED:
        messages.warning(request, "Cannot confirm - purchase has already been cancelled.")
    # elif ACKNOWLEDGED, move to S_PENDING
    elif purchase.status == Transaction.ACKNOWLEDGED:
        purchase.status = Transaction.S_PENDING
        purchase.save()
        messages.success(request, "Purchase confirmed, awaiting seller confirmation.")
    # elif B_PENDING, move to COMPLETE and move item to COMPLETE as well
    elif purchase.status == Transaction.B_PENDING:
        item = purchase.item
        item.status = Item.COMPLETE
        item.save()
        purchase.status = Transaction.COMPLETE
        purchase.save()
        messages.success(request, "Purchase confirmed by both parties and completed.")
    
    return redirect("list_purchases")


# ----------------------------------------------------------------------

# cancel purchase
# buyer cancels purchase

@authentication_required
def cancelPurchase(request, pk):
    account = Account.objects.get(username=request.session.get("username"))

    purchase = Transaction.objects.get(pk=pk)

    # must be the buyer of this transaction
    if purchase.buyer != account:
        # rejected
        raise PermissionDenied

    # transaction cannot be COMPLETE or CANCELLED
    if purchase.status == Transaction.COMPLETE:
        messages.warning(request, "Cannot cancel a purchase which has already been completed.")
    elif purchase.status == Transaction.CANCELLED:
        messages.warning(request, "Already cancelled.")
    # move to CANCELLED and move item to AVAILABLE
    else:
        item = purchase.item
        item.status = Item.AVAILABLE
        item.save()
        purchase.status = Transaction.CANCELLED
        purchase.save()
        messages.success(request, "Purchase cancelled.")
    
    return redirect("list_purchases")


# ----------------------------------------------------------------------

# seller accepts sale

@authentication_required
def acceptSale(request, pk):
    account = Account.objects.get(username=request.session.get("username"))

    sale = Transaction.objects.get(pk=pk)

    # must be the seller of this transaction
    if sale.item.seller != account:
        # rejected
        raise PermissionDenied

    # transaction must be INITIATED
    if sale.status == Transaction.INITIATED:
        sale.status = Transaction.ACKNOWLEDGED
        sale.save()
        messages.success(request, "Sale acknowledged.")
    else:
        messages.warning(request, "Cannot acknowledge - sale not in INITIATED state.")
    
    return redirect("list_items")


# ----------------------------------------------------------------------

# seller confirms sale

@authentication_required
def confirmSale(request, pk):
    account = Account.objects.get(username=request.session.get("username"))

    sale = Transaction.objects.get(pk=pk)

    # must be the seller of this transaction
    if sale.item.seller != account:
        # rejected
        raise PermissionDenied

    # transaction cannot be INITIATED, B_PENDING, COMPLETE, or CANCELLED
    if sale.status == Transaction.INITIATED:
        messages.warning(request, "Cannot confirm - acknowledge the sale first.")
    elif sale.status == Transaction.B_PENDING:
        messages.warning(request, "Already confirmed - awaiting buyer confirmation.")
    elif sale.status == Transaction.COMPLETE:
        messages.warning(request, "Already confirmed - sale has already been completed.")
    elif sale.status == Transaction.CANCELLED:
        messages.warning(request, "Cannot confirm - sale has already been cancelled.")
    # elif ACKNOWLEDGED, move to B_PENDING
    elif sale.status == Transaction.ACKNOWLEDGED:
        sale.status = Transaction.B_PENDING
        sale.save()
        messages.success(request, "Sale confirmed, awaiting buyer confirmation.")
    # elif S_PENDING, move to COMPLETE and move item to COMPLETE as well
    elif sale.status == Transaction.S_PENDING:
        item = sale.item
        item.status = Item.COMPLETE
        item.save()
        sale.status = Transaction.COMPLETE
        sale.save()
        messages.success(request, "Sale confirmed by both parties and completed.")
    
    return redirect("list_items")


# ----------------------------------------------------------------------

# seller cancels sale

@authentication_required
def cancelSale(request, pk):
    account = Account.objects.get(username=request.session.get("username"))

    sale = Transaction.objects.get(pk=pk)

    # must be the seller of this transaction
    if sale.item.seller != account:
        # rejected
        raise PermissionDenied

    # transaction cannot be COMPLETE or CANCELLED
    if sale.status == Transaction.COMPLETE:
        messages.warning(request, "Cannot cancel a sale which has already been completed.")
    elif sale.status == Transaction.CANCELLED:
        messages.warning(request, "Already cancelled.")
    # move to CANCELLED and move item to AVAILABLE
    else:
        item = sale.item
        item.status = Item.AVAILABLE
        item.save()
        sale.status = Transaction.CANCELLED
        sale.save()
        messages.success(request, "Sale cancelled.")
    
    return redirect("list_items")


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
