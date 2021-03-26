from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import Account, Item, Transaction, ItemLog, TransactionLog
from .forms import AccountForm, ItemForm
from utils import CASClient

import cloudinary
import cloudinary.uploader
import cloudinary.api

from django.core.exceptions import PermissionDenied
import secrets

# ----------------------------------------------------------------------

# helper method to log an item action


def logItemAction(item, account, log):
    ItemLog(item=item, account=account, datetime=timezone.now(), log=log).save()


# ----------------------------------------------------------------------

# helper method to log a transaction action


def logTransactionAction(transaction, account, log):
    TransactionLog(
        transaction=transaction,
        account=account,
        datetime=timezone.now(),
        log=log,
    ).save()


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
            item.posted_date = timezone.now()
            item.status = Item.AVAILABLE
            item.save()
            # save the m2m fields, which did not yet bc of commit=False
            item_form.save_m2m()
            logItemAction(item, account, "created")

            messages.success(request, "New item posted.")
            # send confirmation email
            send_mail(
                "Item Posted",
                "You have posted a new item for sale!\n"
                + request.build_absolute_uri(reverse("list_items")),
                settings.EMAIL_HOST_USER,
                [account.email],
                fail_silently=False,
            )
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
            logItemAction(item, account, "edited")

            messages.success(request, "Item updated.")

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
    messages.success(request, "Item deleted.")
    # send confirmation email
    send_mail(
        "Item Deleted",
        "You have removed an item for sale.\n"
        + request.build_absolute_uri((reverse("list_items"))),
        settings.EMAIL_HOST_USER,
        [account.email],
        fail_silently=False,
    )
    return redirect("list_items")


# ----------------------------------------------------------------------

# personal purchases page


@authentication_required
def listPurchases(request):
    account = Account.objects.get(username=request.session.get("username"))

    # get purchases for which user is the buyer
    purchases = Transaction.objects.filter(buyer=account)
    context = {"purchases": purchases}
    return render(request, "marketplace/list_purchases.html", context)


# ----------------------------------------------------------------------

# buyer makes new purchase
# POST request with pk of item to purchase will create new transaction


@authentication_required
def newPurchase(request):
    account = Account.objects.get(username=request.session.get("username"))

    # item must be available for a transaction to associate with
    pk = request.POST["pk"]
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
    logItemAction(item, account, "froze")

    purchase = Transaction(item=item, buyer=account, status=Transaction.INITIATED)
    purchase.save()
    logTransactionAction(purchase, account, "created")

    # send confirmation email
    send_mail(
        "Purchase Requested",
        "You have requested to purchase an item.\n"
        + request.build_absolute_uri(reverse("list_purchases")),
        settings.EMAIL_HOST_USER,
        [account.email],
        fail_silently=False,
    )
    # send notification email to seller
    send_mail(
        "Sale Requested by a Buyer",
        "Your item has been requested for sale!\n"
        + request.build_absolute_uri(reverse("list_items")),
        settings.EMAIL_HOST_USER,
        [item.seller.email],
        fail_silently=False,
    )

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
        messages.warning(
            request, "Already confirmed - purchase has already been completed."
        )
    elif purchase.status == Transaction.CANCELLED:
        messages.warning(
            request, "Cannot confirm - purchase has already been cancelled."
        )
    # elif ACKNOWLEDGED, move to S_PENDING
    elif purchase.status == Transaction.ACKNOWLEDGED:
        purchase.status = Transaction.S_PENDING
        purchase.save()
        logTransactionAction(purchase, account, "confirmed")
        messages.success(request, "Purchase confirmed, awaiting seller confirmation.")
        # send confirmation emails
        send_mail(
            "Purchase Confirmed",
            "You have confirmed a purchase.\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_HOST_USER,
            [account.email],
            fail_silently=False,
        )
        send_mail(
            "Sale Awaiting Confirmation",
            "Your sale has been confirmed by the buyer and awaits your confirmation.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_HOST_USER,
            [purchase.item.seller.email],
            fail_silently=False,
        )
    # elif B_PENDING, move to COMPLETE and move item to COMPLETE as well
    elif purchase.status == Transaction.B_PENDING:
        item = purchase.item
        item.status = Item.COMPLETE
        item.save()
        logItemAction(item, account, "completed")
        purchase.status = Transaction.COMPLETE
        purchase.save()
        logTransactionAction(purchase, account, "confirmed and completed")
        messages.success(request, "Purchase confirmed by both parties and completed.")
        # send confirmation emails
        send_mail(
            "Purchase Completed",
            "Your purchase has been completed.\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_HOST_USER,
            [account.email],
            fail_silently=False,
        )
        send_mail(
            "Sale Completed",
            "Your sale has been confirmed by the buyer and is completed.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_HOST_USER,
            [item.seller.email],
            fail_silently=False,
        )

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
        messages.warning(
            request, "Cannot cancel a purchase which has already been completed."
        )
    elif purchase.status == Transaction.CANCELLED:
        messages.warning(request, "Already cancelled.")
    # move to CANCELLED and move item to AVAILABLE
    else:
        item = purchase.item
        item.status = Item.AVAILABLE
        item.save()
        logItemAction(item, account, "unfroze")
        purchase.status = Transaction.CANCELLED
        purchase.save()
        logTransactionAction(purchase, account, "cancelled")
        messages.success(request, "Purchase cancelled.")
        # send confirmation emails
        send_mail(
            "Purchase Cancelled",
            "You have cancelled a purchase.\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_HOST_USER,
            [account.email],
            fail_silently=False,
        )
        send_mail(
            "Sale Cancelled by Buyer",
            "Your sale has been cancelled by the buyer.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_HOST_USER,
            [item.seller.email],
            fail_silently=False,
        )

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
        logTransactionAction(sale, account, "acknowledged")
        messages.success(request, "Sale acknowledged.")
        # send confirmation email
        send_mail(
            "Sale Accepted",
            "You have accepted a sale request.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_HOST_USER,
            [account.email],
            fail_silently=False,
        )
        send_mail(
            "Purchase Request Accepted by Seller",
            "Your purchase request has been accepted by the seller.\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_HOST_USER,
            [sale.buyer.email],
            fail_silently=False,
        )
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
        messages.warning(
            request, "Already confirmed - sale has already been completed."
        )
    elif sale.status == Transaction.CANCELLED:
        messages.warning(request, "Cannot confirm - sale has already been cancelled.")
    # elif ACKNOWLEDGED, move to B_PENDING
    elif sale.status == Transaction.ACKNOWLEDGED:
        sale.status = Transaction.B_PENDING
        sale.save()
        logTransactionAction(sale, account, "confirmed")
        messages.success(request, "Sale confirmed, awaiting buyer confirmation.")
        # send confirmation email
        send_mail(
            "Sale Confirmed",
            "You have confirmed a sale.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_HOST_USER,
            [account.email],
            fail_silently=False,
        )
        send_mail(
            "Purchase Awaiting Confirmation",
            "Your purchase has been confirmed by the seller and awaits your confirmation\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_HOST_USER,
            [sale.buyer.email],
            fail_silently=False,
        )
    # elif S_PENDING, move to COMPLETE and move item to COMPLETE as well
    elif sale.status == Transaction.S_PENDING:
        item = sale.item
        item.status = Item.COMPLETE
        item.save()
        logItemAction(item, account, "completed")
        sale.status = Transaction.COMPLETE
        sale.save()
        logTransactionAction(sale, account, "confirmed and completed")
        messages.success(request, "Sale confirmed by both parties and completed.")
        # send confirmation email
        send_mail(
            "Sale Completed",
            "You have confirmed and completed your sale.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_HOST_USER,
            [account.email],
            fail_silently=False,
        )
        send_mail(
            "Purchase Completed",
            "Your purchase has been confirmed by the seller and is completed.\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_HOST_USER,
            [sale.buyer.email],
            fail_silently=False,
        )

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
        messages.warning(
            request, "Cannot cancel a sale which has already been completed."
        )
    elif sale.status == Transaction.CANCELLED:
        messages.warning(request, "Already cancelled.")
    # move to CANCELLED and move item to AVAILABLE
    else:
        item = sale.item
        item.status = Item.AVAILABLE
        item.save()
        logItemAction(item, account, "unfrozen")
        sale.status = Transaction.CANCELLED
        sale.save()
        logTransactionAction(sale, account, "cancelled")
        messages.success(request, "Sale cancelled.")
        # send confirmation email
        send_mail(
            "Sale Cancelled",
            "You have cancelled a sale.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_HOST_USER,
            [account.email],
            fail_silently=False,
        )
        send_mail(
            "Purchase Cancelled by Seller",
            "Your purchase has been cancelled by the seller.\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_HOST_USER,
            [sale.buyer.email],
            fail_silently=False,
        )

    return redirect("list_items")


# ----------------------------------------------------------------------

# account settings page


@authentication_required
def editAccount(request):
    account = Account.objects.get(username=request.session.get("username"))
    old_email = account.email

    # populate the Django model form and validate data
    if request.method == "POST":
        account_form = AccountForm(request.POST, instance=account)
        if account_form.is_valid():
            new_email = account_form.cleaned_data["email"]
            account_form.save()
            # do not save new email yet
            if new_email != old_email:
                account = Account.objects.get(username=request.session.get("username"))
                account.email = old_email
                account.save()

                # store new_email and random token into cache
                # for email verification
                token = secrets.token_hex(32)
                cache.set(token, [account.username, new_email], 900)

                # send verification email
                send_mail(
                    "Tiger ReTail Email Verification",
                    "Please visit the following link to verify your email.\n"
                    + "If you did not make this request, you can safely ignore this message.\n"
                    + request.build_absolute_uri(reverse("verify_email", args=[token])),
                    settings.EMAIL_HOST_USER,
                    [new_email],
                    fail_silently=False,
                )
                messages.info(request, "Verification email sent.")

            messages.success(request, "Account updated.")

    # did not receive form data via POST, so send stored account form
    else:
        account_form = AccountForm(instance=account)

    context = {"account_form": account_form}
    return render(request, "marketplace/edit_account.html", context)


# ----------------------------------------------------------------------


@authentication_required
def verifyEmail(request, token):
    account = Account.objects.get(username=request.session.get("username"))
    if cache.get(token):
        username, new_email = cache.get(token)
        if username != account.username:
            messages.warning(
                request,
                "Permission denied. Ensure you are logged in with the correct account.",
            )
        else:
            account.email = new_email
            account.save()
            messages.success(request, "Email verified.")
    else:
        messages.warning(request, "Verification link has expired.")
    return redirect("edit_account")


# ----------------------------------------------------------------------


def logout(request):
    request.session.pop("username")
    return redirect(CASClient.getLogoutUrl())
