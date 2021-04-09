from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import (
    Account,
    Item,
    Transaction,
    ItemLog,
    TransactionLog,
    AlbumImage,
    ItemRequest,
    ItemRequestLog,
    Message,
)
from .forms import AccountForm, ItemForm, ItemRequestForm
from utils import CASClient

import cloudinary
import cloudinary.uploader
import cloudinary.api

from django.core.exceptions import PermissionDenied
import secrets
from django.http import HttpResponse, JsonResponse
import json

from sys import stderr

# ----------------------------------------------------------------------

# helper method to log an error to server stderr


def logError(account, exception):
    print(
        "[" + str(timezone.now()) + "] " + account.username + ": " + str(exception),
        file=stderr,
    )


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

# helper method to log an item_request action


def logItemRequestAction(item_request, account, log):
    ItemRequestLog(
        item_request=item_request,
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
            ).strip()

            if username is not None:
                # store authenticated username,
                # check that associated Account exists, else create one,
                # call view as normal
                request.session["username"] = username
                if not Account.objects.filter(username=username).exists():
                    # note this assumes use of princeton email
                    Account(
                        username=username,
                        name=username,
                        email=username + "@princeton.edu",
                    ).save()
                return view_function(request, *args, **kwargs)

        # user could NOT be authenticated, so redirect to CAS login
        # before redirection, store POST details for use once redirected back
        if request.method == "POST":
            request.session[request.path] = request.POST
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
            try:
                item.save()
                # save the m2m fields, which did not yet bc of commit=False
                item_form.save_m2m()
                logItemAction(item, account, "created")

                # create linked album images from uploaded files
                album = request.FILES.getlist("album")
                for i in range(len(album)):
                    if i >= settings.ALBUM_LIMIT:
                        break
                    try:
                        AlbumImage(image=album[i], item=item).save()
                    except Exception as e:
                        messages.error(
                            request,
                            "Could not save album image. Check that your album images are each < 10MB and proper image files.",
                        )
                        logError(account, e)

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
            except Exception as e:
                messages.error(
                    request,
                    "Could not post item. Check that your lead image is < 10MB and a proper image file.",
                )
                logError(account, e)

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
            try:
                # save changes to item
                item_form.save()
                logItemAction(item, account, "edited")

                # overwrite the album images
                item.album.all().delete()
                album = request.FILES.getlist("album")
                for i in range(len(album)):
                    if i >= settings.ALBUM_LIMIT:
                        break
                    try:
                        AlbumImage(image=album[i], item=item).save()
                    except Exception as e:
                        messages.error(
                            request,
                            "Could not save album image. Check that your album images are each < 10MB and proper image files.",
                        )
                        logError(account, e)

                messages.success(request, "Item updated.")
            except Exception as e:
                messages.error(
                    request,
                    "Could not edit item. Check that your lead image is < 10MB and a proper image file.",
                )
                logError(account, e)

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

    # check for possible GET instead of POST, caused by CAS redirect for login upon trying to purchase an item
    if request.method == "GET":
        if request.path in request.session:
            request.POST = request.session.pop(request.path)
        else:
            # GET request with no prev POST data in session is an error
            return HttpResponse(status=400)

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
    messages.success(request, "Purchase started!")

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
        # open contact between buyer and seller
        account.contacts.add(sale.buyer)  # (m2m goes both ways)
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

# personal item_requests page


@authentication_required
def listItemRequests(request):
    account = Account.objects.get(username=request.session.get("username"))
    item_requests = account.itemrequest_set.all()
    context = {"item_requests": item_requests}
    return render(request, "marketplace/list_item_requests.html", context)


# ----------------------------------------------------------------------

# new item_request form
# GET requests get a blank form
# POST requests get a form with error feedback, else new item_request created
# and redirected to list item_requests page


@authentication_required
def newItemRequest(request):
    account = Account.objects.get(username=request.session.get("username"))

    # populate the Django model form and validate data
    if request.method == "POST":
        item_request_form = ItemRequestForm(request.POST, request.FILES)
        if item_request_form.is_valid():
            # create new item_request, but do not save yet until changes made
            item_request = item_request_form.save(commit=False)
            item_request.requester = account
            item_request.posted_date = timezone.now()
            try:
                item_request.save()
                # save the m2m fields, which did not yet bc of commit=False
                item_request_form.save_m2m()

                logItemRequestAction(item_request, account, "created")
                messages.success(request, "New item request posted.")
                # send confirmation email
                send_mail(
                    "Item Request Posted",
                    "You have posted a new item request!\n"
                    + request.build_absolute_uri(reverse("list_item_requests")),
                    settings.EMAIL_HOST_USER,
                    [account.email],
                    fail_silently=False,
                )
                return redirect("list_item_requests")
            except Exception as e:
                messages.error(
                    request,
                    "Could not post item request. Check that your reference image is < 10MB and a proper image file.",
                )
                logError(account, e)

    # did not receive form data via POST, so send a blank form
    else:
        item_request_form = ItemRequestForm()

    context = {"item_request_form": item_request_form}
    return render(request, "marketplace/new_item_request.html", context)


# ----------------------------------------------------------------------

# edit item_request form
# GET requests given pre-populated item_request form
# POST requests given form with error feedback, else item_request edited


@authentication_required
def editItemRequest(request, pk):
    account = Account.objects.get(username=request.session.get("username"))

    # if the item_request does not belong to this account, permission denied
    item_request = ItemRequest.objects.get(pk=pk)
    if item_request.requester != account:
        raise PermissionDenied

    # populate the Django model form and validate data
    if request.method == "POST":
        item_request_form = ItemRequestForm(
            request.POST, request.FILES, instance=item_request
        )
        if item_request_form.is_valid():
            try:
                # save changes to item_request
                item_request_form.save()

                logItemRequestAction(item_request, account, "edited")
                messages.success(request, "Item request updated.")
            except Exception as e:
                messages.error(
                    request,
                    "Could not edit item request. Check that your reference image is < 10MB and a proper image file.",
                )
                logError(account, e)

    # did not receive form data via POST, so send stored item_request form
    else:
        item_request_form = ItemRequestForm(instance=item_request)
    context = {"item_request": item_request, "item_request_form": item_request_form}
    return render(request, "marketplace/edit_item_request.html", context)


# ----------------------------------------------------------------------

# delete item_request


@authentication_required
def deleteItemRequest(request, pk):
    account = Account.objects.get(username=request.session.get("username"))

    # if the item_request does not belong to this account, permission denied
    item_request = ItemRequest.objects.get(pk=pk)
    if item_request.requester != account:
        raise PermissionDenied

    item_request.delete()
    messages.success(request, "Item request deleted.")
    # send confirmation email
    send_mail(
        "Item Request Deleted",
        "You have removed an item request.\n"
        + request.build_absolute_uri((reverse("list_item_requests"))),
        settings.EMAIL_HOST_USER,
        [account.email],
        fail_silently=False,
    )
    return redirect("list_item_requests")


# ----------------------------------------------------------------------

# messaging system page


@authentication_required
def inbox(request):
    account = Account.objects.get(username=request.session.get("username"))
    contacts = account.contacts.all()
    context = {"contacts": contacts}
    return render(request, "marketplace/inbox.html", context)


# ----------------------------------------------------------------------

# get messages sent to and received from account pk


@authentication_required
def getMessages(request, pk):
    account = Account.objects.get(username=request.session.get("username"))
    try:
        contact = Account.objects.get(pk=pk)
    except:
        return HttpResponse(status=400)
    sent = account.sent_messages.filter(receiver=contact).order_by("datetime")
    received = account.received_messages.filter(sender=contact).order_by("datetime")
    return JsonResponse(
        {
            "sent": list(sent.values_list("datetime", "text")),
            "received": list(received.values_list("datetime", "text")),
        }
    )


# ----------------------------------------------------------------------

# send message to account pk


@authentication_required
def sendMessage(request):
    account = Account.objects.get(username=request.session.get("username"))
    # NOTE: using request.body instead of request.POST bc of frontend fetch() API
    body = json.loads(request.body)

    try:
        contact = Account.objects.get(pk=body["pk"])
        text = body["text"]
    except:
        return HttpResponse(status=400)

    Message(sender=account, receiver=contact, datetime=timezone.now(), text=text).save()
    return HttpResponse(status=200)


# ----------------------------------------------------------------------

# account activity page


@authentication_required
def accountActivity(request):
    account = Account.objects.get(username=request.session.get("username"))

    own_activity_item = account.item_logs.order_by("datetime")
    own_activity_transaction = account.transaction_logs.order_by("datetime")
    own_activity_item_request = account.item_request_logs.order_by("datetime")

    item_activity = ItemLog.objects.filter(item__seller=account).order_by("datetime")
    transaction_activity = TransactionLog.objects.filter(
        transaction__buyer=account
    ).order_by("datetime")
    item_request_activity = ItemRequestLog.objects.filter(
        item_request__requester=account
    ).order_by("datetime")

    context = {
        "own_activity_transaction": own_activity_transaction,
        "own_activity_item": own_activity_item,
        "own_activity_item_request": own_activity_item_request,
        "item_activity": item_activity,
        "transaction_activity": transaction_activity,
        "item_request_activity": item_request_activity,
    }
    return render(request, "marketplace/account_activity.html", context)


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

# faq page
def faq(request):
    return render(request, "marketplace/faq.html", {})


# ----------------------------------------------------------------------

# contact us page


def contact(request):
    return render(request, "marketplace/contact.html", {})


# ----------------------------------------------------------------------


def logout(request):
    request.session.pop("username")
    return redirect(CASClient.getLogoutUrl())
