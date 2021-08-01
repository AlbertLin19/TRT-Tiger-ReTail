from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Window, F
from django.db.models.functions import RowNumber
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
    Notification,
)
from .forms import AccountForm, ItemForm, ItemRequestForm
from utils import CASClient
from datetime import timedelta

import cloudinary
import cloudinary.uploader
import cloudinary.api

from django.core.exceptions import PermissionDenied
import secrets
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
import json

from sys import stderr

from background_task import background
from datetime import date, datetime

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

# helper method to send new notification email delayed and sparsely
# namely, if the notification is seen by the time to send, will not send


@background(schedule=300)
def notifyEmailSparsely(pk, email, url):
    notification = Notification.objects.get(pk=pk)
    if not notification.seen:
        send_mail(
            "Unread Notification(s) on Tiger ReTail",
            "You have new notification(s) waiting to be read.\n" + url,
            settings.EMAIL_NAME,
            [email],
            fail_silently=True,
        )


# ----------------------------------------------------------------------

# helper method to send notification


def notify(account, text, url, sparse=False, timeout=timedelta(minutes=5)):
    if not sparse:
        Notification(
            account=account,
            datetime=timezone.now(),
            text=text,
            seen=False,
            url=url,
        ).save()
        return
    else:
        if Notification.objects.filter(account=account, text=text, seen=False).exists():
            duplicates = Notification.objects.filter(
                account=account, text=text, seen=False
            )
            recent = duplicates.order_by("-datetime").first()
            if timezone.now() < recent.datetime + timeout:
                return

        should_email = False
        if not Notification.objects.filter(
            account=account, text=text, seen=False
        ).exists():
            should_email = True
        notification = Notification(
            account=account,
            datetime=timezone.now(),
            text=text,
            seen=False,
            url=url,
        )
        notification.save()

        # if the oldest unseen notification is the one just created,
        # then delay-sparse send an email (delayed to allow user to see notification and prevent the email)
        if should_email:
            notifyEmailSparsely(
                pk=notification.pk,
                email=account.email,
                url=url,
            )


# ----------------------------------------------------------------------
# notify and email a notice about item expiration being passed
@background
def expiredItemNotice(pk):
    # check if the item still exists
    if not Item.objects.filter(pk=pk).exists():
        return

    # check if the item has expired
    item = Item.objects.filter(pk=pk).first()
    if item.deadline >= timezone.now().date():
        return

    # send notices
    send_mail(
        "Your Posted Item has Expired",
        "Your posted item "
        + item.name
        + " has expired.\nPlease edit your item deadline if you would like to prevent your item from being removed.\nItems are removed "
        + str(settings.EXPIRATION_BUFFER)
        + " after their deadlines.",
        settings.EMAIL_NAME,
        [item.seller.email],
        fail_silently=True,
    )
    notify(
        item.seller,
        "Your item "
        + item.name
        + " has expired. Please edit its deadline if you do not want it removed.",
        reverse("list_items"),
    )


# ----------------------------------------------------------------------
# notify and email a notice about item request expiration being passed
@background
def expiredItemRequestNotice(pk):
    # check if the item request still exists
    if not ItemRequest.objects.filter(pk=pk).exists():
        return

    # check if the item request has expired
    item_request = ItemRequest.objects.filter(pk=pk).first()
    if item_request.deadline >= timezone.now().date():
        return

    # send notices
    send_mail(
        "Your Posted Item Request has Expired",
        "Your posted item request for "
        + item_request.name
        + " has expired.\nPlease edit your item request deadline if you would like to prevent your item request from being removed.\nItem requests are removed "
        + str(settings.EXPIRATION_BUFFER)
        + " after their deadlines.",
        settings.EMAIL_NAME,
        [item_request.requester.email],
        fail_silently=True,
    )
    notify(
        item_request.requester,
        "Your item request "
        + item_request.name
        + " has expired. Please edit its deadline if you do not want it removed.",
        reverse("list_item_requests"),
    )


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
                # SPECIAL CASE: if the netid is an ADMIN_NETID
                if username in settings.ADMIN_NETIDS:
                    # create all the alternate accounts
                    # and assign the first one as active
                    for suffix in settings.ALT_ACCOUNT_SUFFIXES:
                        if not Account.objects.filter(
                            username=username + suffix
                        ).exists():
                            Account(
                                username=username + suffix,
                                name=username + suffix,
                                email=username + "@princeton.edu",
                            ).save()
                    request.session["username"] = (
                        username + settings.ALT_ACCOUNT_SUFFIXES[0]
                    )

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

# get AVAILABLE items for image gallery with the following relative GET options:
# [REQUIRED] count >= 1 (if n < count items fit the criteria, then only those n items returned)      
# [REQUIRED] direction (forward/backward)
# [REQUIRED] base_item_pk (if -1, then will collect items from beginning/end based on direction)
# [OPTIONAL] search_string (used to index the items by name and description prior to retrieval)
# [OPTIONAL] conditions ("condition,condition,...")
# [OPTIONAL] category_pks ("category_pk,category_pk,...")

# if base_item_pk == -1 and no items yet exist, then returns empty list

# returns:
# {
#    "items": [
#        {
#           "pk",
#           "name",
#           "deadline",
#           "price",
#           "negotiable",
#           "condition",
#           "description",
#           "image", (url)
#           "album", (list of urls)
#        },
#        {
#           "pk",
#           "name",
#           "deadline",
#           "price",
#           "negotiable",
#           "condition",
#           "description",
#           "image", (url)
#           "album", (list of urls)
#        },
#        ...
#    ]
# }


def getItemsRelative(request):
    try:
        count = int(request.GET['count'])
        direction = request.GET['direction']
        base_item_pk = int(request.GET['base_item_pk'])
    except:
        return HttpResponse(status=400)

    if count < 1 or base_item_pk < -1 or direction not in ['forward', 'backward']:
        return HttpResponse(status=400)

    search_string = ""
    conditions = []
    categories = []

    if "search_string" in request.GET:
        search_string = request.GET["search_string"]

    if "conditions" in request.GET:
        try:
            conditions = [int(pk) for pk in request.GET["conditions"].split(",") if pk]
        except:
            return HttpResponse(status=400)

    if "category_pks" in request.GET:
        try:
            categories = list(Category.objects.filter(pk__in=[int(pk) for pk in request.GET["category_pks"].split(",") if pk]))
        except:
            return HttpResponse(status=400)

    # filter items that meet conditions and categories criteria
    items = Item.objects.filter(status=Item.AVAILABLE)

    if conditions:
        items = items.filter(condition__in=conditions)

    if categories:
        items = items.filter(categories__in=categories)

    # annotate items by search string rank
    items = items.annotate(rank=SearchRank(SearchVector("name", "description"), SearchQuery(search_string), cover_density=True))

    # annotate items by row number after sorting by search string rank (so no comparison issues with equal ranks)
    items = items.annotate(
        row=Window(
            expression=RowNumber(),
            order_by=[F("rank").asc(), F("pk").asc()], # also order by unique pk to make tie-breaks consistent
        )
    )

    # get the correct slice of items
    if base_item_pk == -1:
        items = items.order_by('row' if direction == 'forward' else '-row')[:count]
    else:
        try:
            base_item_row = items.get(pk=base_item_pk).row
        except:
            return HttpResponse(status=400)

        if direction == 'forward':
            items = items.filter(row__gt=base_item_row).order_by('row')[:count]
        else:
            items = items.filter(row__lt=base_item_row).order_by('-row')[:count]

    return JsonResponse(
        {
            "items": [
                {
                    "pk": item.pk,
                    "name": item.name,
                    "deadline": item.deadline,
                    "price": item.price,
                    "negotiable": item.negotiable,
                    "condition": item.condition,
                    "description": item.description,
                    "image": item.image.url,
                    "album": [albumimage.image.url for albumimage in item.album.all()],
                } for item in list(items.prefetch_related("album"))
            ]
        }
    )


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
                    settings.EMAIL_NAME,
                    [account.email],
                    fail_silently=True,
                )
                # schedule expiration notice
                expiredItemNotice(
                    item.pk,
                    schedule=timezone.make_aware(
                        datetime(
                            item.deadline.year, item.deadline.month, item.deadline.day
                        )
                    )
                    + timedelta(days=1),
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
        old_image = item.image
        old_deadline = item.deadline
        item_form = ItemForm(request.POST, request.FILES, instance=item)
        if item_form.is_valid():
            try:
                # save changes to item
                item_form.save()

                # remove the old image from storage (if different)
                if item_form.cleaned_data["image"] != old_image:
                    cloudinary.uploader.destroy(str(old_image))

                logItemAction(item, account, "edited")

                if "replace" in request.POST:
                    # delete old album images
                    item.album.all().delete()

                if request.FILES.getlist("album"):
                    # insert album images (up to the count limit)
                    num_already = len(item.album.all())
                    album = request.FILES.getlist("album")
                    for i in range(len(album)):
                        if i + num_already >= settings.ALBUM_LIMIT:
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

                if item.deadline != old_deadline:
                    # schedule expiration notice
                    expiredItemNotice(
                        item.pk,
                        schedule=timezone.make_aware(
                            datetime(
                                item.deadline.year,
                                item.deadline.month,
                                item.deadline.day,
                            )
                        )
                        + timedelta(days=1),
                    )

            except Exception as e:
                messages.error(
                    request,
                    "Could not edit item. Check that your lead image is < 10MB and a proper image file.",
                )
                logError(account, e)
                return redirect("edit_item", pk)

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
        settings.EMAIL_NAME,
        [account.email],
        fail_silently=True,
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
        settings.EMAIL_NAME,
        [account.email],
        fail_silently=True,
    )
    # send notification email to seller
    send_mail(
        "Sale Requested by a Buyer",
        "Your item has been requested for sale!\n"
        + request.build_absolute_uri(reverse("list_items")),
        settings.EMAIL_NAME,
        [item.seller.email],
        fail_silently=True,
    )
    # notify the seller
    notify(
        item.seller,
        account.name + " has requested to purchase " + item.name,
        request.build_absolute_uri(reverse("list_items")),
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
            settings.EMAIL_NAME,
            [account.email],
            fail_silently=True,
        )
        send_mail(
            "Sale Awaiting Confirmation",
            "Your sale has been confirmed by the buyer and awaits your confirmation.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_NAME,
            [purchase.item.seller.email],
            fail_silently=True,
        )
        # notify the seller
        notify(
            purchase.item.seller,
            account.name
            + " has confirmed the purchase of "
            + purchase.item.name
            + " and awaits your confirmation",
            request.build_absolute_uri(reverse("list_items")),
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
            settings.EMAIL_NAME,
            [account.email],
            fail_silently=True,
        )
        send_mail(
            "Sale Completed",
            "Your sale has been confirmed by the buyer and is completed.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_NAME,
            [item.seller.email],
            fail_silently=True,
        )
        # notify the seller
        notify(
            item.seller,
            account.name + " has confirmed and completed the purchase of " + item.name,
            request.build_absolute_uri(reverse("list_items")),
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
            settings.EMAIL_NAME,
            [account.email],
            fail_silently=True,
        )
        send_mail(
            "Sale Cancelled by Buyer",
            "Your sale has been cancelled by the buyer.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_NAME,
            [item.seller.email],
            fail_silently=True,
        )
        # notify the seller
        notify(
            item.seller,
            account.name + " has cancelled the purchase of " + item.name,
            request.build_absolute_uri(reverse("list_items")),
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
        # notify the buyer
        notify(
            sale.buyer,
            account.name
            + " has connected with you. You can now send direct messages to the seller through the inbox regarding "
            + sale.item.name,
            request.build_absolute_uri(reverse("inbox")),
        )
        # notify the seller
        notify(
            account,
            sale.buyer.name
            + " has been added as a contact. You can now send direct messages to the buyer through the inbox regarding "
            + sale.item.name,
            request.build_absolute_uri(reverse("inbox")),
        )
        # send confirmation email
        send_mail(
            "Sale Accepted",
            "You have accepted a sale request.\n"
            + request.build_absolute_uri(reverse("list_items")),
            settings.EMAIL_NAME,
            [account.email],
            fail_silently=True,
        )
        send_mail(
            "Purchase Request Accepted by Seller",
            "Your purchase request has been accepted by the seller.\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_NAME,
            [sale.buyer.email],
            fail_silently=True,
        )
        # notify the buyer
        notify(
            sale.buyer,
            account.name + " has accepted your purchase request for " + sale.item.name,
            request.build_absolute_uri(reverse("list_purchases")),
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
            settings.EMAIL_NAME,
            [account.email],
            fail_silently=True,
        )
        send_mail(
            "Purchase Awaiting Confirmation",
            "Your purchase has been confirmed by the seller and awaits your confirmation\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_NAME,
            [sale.buyer.email],
            fail_silently=True,
        )
        # notify the buyer
        notify(
            sale.buyer,
            account.name
            + " has confirmed your purchase of "
            + sale.item.name
            + " and awaits your confirmation",
            request.build_absolute_uri(reverse("list_purchases")),
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
            settings.EMAIL_NAME,
            [account.email],
            fail_silently=True,
        )
        send_mail(
            "Purchase Completed",
            "Your purchase has been confirmed by the seller and is completed.\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_NAME,
            [sale.buyer.email],
            fail_silently=True,
        )
        # notify the buyer
        notify(
            sale.buyer,
            account.name
            + " has confirmed and completed your purchase of "
            + sale.item.name,
            request.build_absolute_uri(reverse("list_purchases")),
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
            settings.EMAIL_NAME,
            [account.email],
            fail_silently=True,
        )
        send_mail(
            "Purchase Cancelled by Seller",
            "Your purchase has been cancelled by the seller.\n"
            + request.build_absolute_uri(reverse("list_purchases")),
            settings.EMAIL_NAME,
            [sale.buyer.email],
            fail_silently=True,
        )
        # notify the buyer
        notify(
            sale.buyer,
            account.name + " has cancelled your purchase of " + sale.item.name,
            request.build_absolute_uri(reverse("list_purchases")),
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
                    settings.EMAIL_NAME,
                    [account.email],
                    fail_silently=True,
                )
                # schedule expiration notice
                expiredItemRequestNotice(
                    item_request.pk,
                    schedule=timezone.make_aware(
                        datetime(
                            item_request.deadline.year,
                            item_request.deadline.month,
                            item_request.deadline.day,
                        )
                    )
                    + timedelta(days=1),
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
        old_image = item_request.image
        old_deadline = item_request.deadline
        item_request_form = ItemRequestForm(
            request.POST, request.FILES, instance=item_request
        )
        if item_request_form.is_valid():
            try:
                # save changes to item_request
                item_request_form.save()

                # remove the old image from storage (if different)
                if item_request_form.cleaned_data["image"] != old_image:
                    cloudinary.uploader.destroy(str(old_image))

                logItemRequestAction(item_request, account, "edited")
                messages.success(request, "Item request updated.")
                if item_request.deadline != old_deadline:
                    # schedule expiration notice
                    expiredItemRequestNotice(
                        item_request.pk,
                        schedule=timezone.make_aware(
                            datetime(
                                item_request.deadline.year,
                                item_request.deadline.month,
                                item_request.deadline.day,
                            )
                        )
                        + timedelta(days=1),
                    )
            except Exception as e:
                messages.error(
                    request,
                    "Could not edit item request. Check that your reference image is < 10MB and a proper image file.",
                )
                logError(account, e)
                return redirect("edit_item_request", pk)

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
        settings.EMAIL_NAME,
        [account.email],
        fail_silently=True,
    )
    return redirect("list_item_requests")


# ----------------------------------------------------------------------

# contact the requester of an item_request


@authentication_required
def contactItemRequest(request, pk):
    account = Account.objects.get(username=request.session.get("username"))
    item_request = ItemRequest.objects.get(pk=pk)

    # cannot contact your own item_request
    if item_request.requester == account:
        # rejected
        messages.warning(
            request, "Cannot respond to an item request you posted yourself."
        )
        return redirect("browse_item_requests")

    # create a contact and set log
    account.contacts.add(item_request.requester)  # (m2m goes both ways)
    # notify the requester
    notify(
        item_request.requester,
        account.name
        + " has connected with you regarding your item request. You can now send direct messages through the inbox regarding your request for "
        + item_request.name,
        request.build_absolute_uri(reverse("inbox")),
    )
    # notify the contacter
    notify(
        account,
        item_request.requester.name
        + " has been added as a contact. You can now send direct messages through the inbox regarding the request for "
        + item_request.name,
        request.build_absolute_uri(reverse("inbox")),
    )
    send_mail(
        "Received Response to Your Item Request",
        "Your item request has been responded to by a potential seller.\n"
        + request.build_absolute_uri(reverse("list_item_requests")),
        settings.EMAIL_NAME,
        [item_request.requester.email],
        fail_silently=True,
    )
    # create an item request log, which will be used to list the item request history for the requester
    logItemRequestAction(item_request, account, "contact")
    messages.success(
        request,
        "You can directly message "
        + item_request.requester.name
        + " about the request for "
        + item_request.name
        + " through the inbox!",
    )

    return redirect("browse_item_requests")


# ----------------------------------------------------------------------

# item request gallery


def browseItemRequests(request):
    item_requests = ItemRequest.objects.all()
    context = {"item_requests": item_requests}
    return render(request, "marketplace/browse_item_requests.html", context)


# ----------------------------------------------------------------------

# get item requests for image gallery with the following relative GET options:
# [REQUIRED] count >= 1 (if n < count item requests fit the criteria, then only those n item requests returned)      
# [REQUIRED] direction (forward/backward)
# [REQUIRED] base_item_request_pk (if -1, then will collect item requests from beginning/end based on direction)
# [OPTIONAL] search_string (used to index the item requests by name and description prior to retrieval)
# [OPTIONAL] conditions ("condition,condition,...")
# [OPTIONAL] category_pks ("category_pk,category_pk,...")

# if base_item_request_pk == -1 and no item requests yet exist, then returns empty list

# returns:
# {
#    "item_requests": [
#        {
#           "pk",
#           "name",
#           "deadline",
#           "price",
#           "negotiable",
#           "condition",
#           "description",
#           "image", (url)
#        },
#        {
#           "pk",
#           "name",
#           "deadline",
#           "price",
#           "negotiable",
#           "condition",
#           "description",
#           "image", (url)
#        },
#        ...
#    ]
# }


def getItemRequestsRelative(request):
    try:
        count = int(request.GET['count'])
        direction = request.GET['direction']
        base_item_request_pk = int(request.GET['base_item_request_pk'])
    except:
        return HttpResponse(status=400)

    if count < 1 or base_item_request_pk < -1 or direction not in ['forward', 'backward']:
        return HttpResponse(status=400)

    search_string = ""
    conditions = []
    categories = []

    if "search_string" in request.GET:
        search_string = request.GET["search_string"]

    if "conditions" in request.GET:
        try:
            conditions = [int(pk) for pk in request.GET["conditions"].split(",") if pk]
        except:
            return HttpResponse(status=400)

    if "category_pks" in request.GET:
        try:
            categories = list(Category.objects.filter(pk__in=[int(pk) for pk in request.GET["category_pks"].split(",") if pk]))
        except:
            return HttpResponse(status=400)

    # filter item requests that meet conditions and categories criteria
    item_requests = ItemRequest.objects.all()

    if conditions:
        item_requests = item_requests.filter(condition__in=conditions)

    if categories:
        item_requests = item_requests.filter(categories__in=categories)

    # annotate item requests by search string rank
    item_requests = item_requests.annotate(rank=SearchRank(SearchVector("name", "description"), SearchQuery(search_string), cover_density=True))

    # annotate item requests by row number after sorting by search string rank (so no comparison issues with equal ranks)
    item_requests = item_requests.annotate(
        row=Window(
            expression=RowNumber(),
            order_by=[F("rank").asc(), F("pk").asc()], # also order by unique pk to make tie-breaks consistent
        )
    )

    # get the correct slice of item requests
    if base_item_requests_pk == -1:
        item_requests = item_requests.order_by('row' if direction == 'forward' else '-row')[:count]
    else:
        try:
            base_item_requests_row = item_requests.get(pk=base_item_requests_pk).row
        except:
            return HttpResponse(status=400)

        if direction == 'forward':
            item_requests = item_requests.filter(row__gt=base_item_requests_row).order_by('row')[:count]
        else:
            item_requests = item_requests.filter(row__lt=base_item_requests_row).order_by('-row')[:count]

    return JsonResponse(
        {
            "item_requests": [
                {
                    "pk": item_request.pk,
                    "name": item_request.name,
                    "deadline": item_request.deadline,
                    "price": item_request.price,
                    "negotiable": item_request.negotiable,
                    "condition": item_request.condition,
                    "description": item_request.description,
                    "image": item_request.image.url,
                } for item_request in list(item_requests)
            ]
        }
    )


# ----------------------------------------------------------------------

# notifications page


@authentication_required
def listNotifications(request):
    account = Account.objects.get(username=request.session.get("username"))
    notifications = account.notifications.all().order_by("-datetime")
    context = {"notifications": notifications}
    return render(request, "marketplace/list_notifications.html", context)


# ----------------------------------------------------------------------

# count unseen notifications


@authentication_required
def countNotifications(request):
    account = Account.objects.get(username=request.session.get("username"))
    count = account.notifications.filter(seen=False).count()
    return JsonResponse({"count": count})


# ----------------------------------------------------------------------

# see all notifications


@authentication_required
def seeNotifications(request):
    account = Account.objects.get(username=request.session.get("username"))
    notifications = account.notifications.all()
    notifications.update(seen=True)
    return HttpResponse(status=200)


# ----------------------------------------------------------------------

# get all notifications


@authentication_required
def getNotifications(request):
    account = Account.objects.get(username=request.session.get("username"))
    notifications = account.notifications.all().order_by("-datetime")
    return JsonResponse(
        {
            "notifications": list(
                notifications.values_list("datetime", "text", "seen", "url")
            )
        }
    )


# ----------------------------------------------------------------------

# get notifications with the following relative GET options:
# count >= 1 (if n < count notifications fit the criteria, then only those n notifications returned)      
# direction (forward/backward)
# base_notification_pk (if -1, then will collect notifications from beginning/end based on direction)

# if base_notification_pk == -1 and no notifications yet exist, then returns empty list

# returns:
# {
#    "notifications": [["pk", "datetime", "text", "seen", "url"], ["pk", "datetime", "text", "seen", "url"], ]
# }


@authentication_required
def getNotificationsRelative(request):
    account = Account.objects.get(username=request.session.get("username"))
    try:
        count = int(request.GET['count'])
        direction = request.GET['direction']
        base_notification_pk = int(request.GET['base_notification_pk'])
    except:
        return HttpResponse(status=400)

    if count < 1 or base_notification_pk < -1 or direction not in ['forward', 'backward']:
        return HttpResponse(status=400)

    # annotate notifications by row number after sorting by datetime (so no comparison issues with equal datetimes)
    notifications = account.notifications.annotate(
        row=Window(
            expression=RowNumber(),
            order_by=[F("datetime").asc(), F("pk").asc()], # also order by unique pk to make tie-breaks consistent
        )
    )
    # retrieve the notifications to return
    if base_notification_pk == -1:
        notifications = notifications.order_by('row' if direction == 'forward' else '-row')[:count]
    else:
        try:
            base_notification_row = notifications.get(pk=base_notification_pk).row
        except:
            return HttpResponse(status=400)

        if direction == 'forward':
            notifications = notifications.filter(row__gt=base_notification_row).order_by('row')[:count]
        else:
            notifications = notifications.filter(row__lt=base_notification_row).order_by('-row')[:count]

    return JsonResponse(
        {
            "notifications": list(notifications.values_list("pk", "datetime", "text", "seen", "url"))
        }
    )


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

# get messages sent to and received from account pk with the following relative GET options:
# count >= 1 (if n < count messages fit the criteria, then only those n messages returned)      
# direction (forward/backward)
# base_message_pk (if -1, then will collect messages from beginning/end based on direction)

# if base_message_pk == -1 and no messages yet exist, then returns empty list

# returns:
# {
#    "sent":     [["pk", "datetime", "text"], ["pk", "datetime", "text"], ]
#    "received": [["pk", "datetime", "text"], ["pk", "datetime", "text"], ]
# }


@authentication_required
def getMessagesRelative(request, pk):
    account = Account.objects.get(username=request.session.get("username"))
    try:
        contact = Account.objects.get(pk=pk)
        count = int(request.GET['count'])
        direction = request.GET['direction']
        base_message_pk = int(request.GET['base_message_pk'])
    except:
        return HttpResponse(status=400)

    if count < 1 or base_message_pk < -1 or direction not in ['forward', 'backward']:
        return HttpResponse(status=400)

    # filter only messages between account and contact
    sent_messages = account.sent_messages.filter(receiver=contact)
    received_messages = account.received_messages.filter(sender=contact)
    pk_list = list(sent_messages.values_list("pk", flat=True))
    pk_list.extend(list(received_messages.values_list("pk", flat=True)))
    messages = Message.objects.filter(pk__in=pk_list)

    # annotate messages by row number after sorting by datetime (so no comparison issues with equal datetimes)
    messages = messages.annotate(
        row=Window(
            expression=RowNumber(),
            order_by=[F("datetime").asc(), F("pk").asc()], # also order by unique pk to make tie-breaks consistent
        )
    )

    # get the correct slice of messages
    if base_message_pk == -1:
        messages = messages.order_by('row' if direction == 'forward' else '-row')[:count]
    else:
        try:
            base_message_row = messages.get(pk=base_message_pk).row
        except:
            return HttpResponse(status=400)

        if direction == 'forward':
            messages = messages.filter(row__gt=base_message_row).order_by('row')[:count]
        else:
            messages = messages.filter(row__lt=base_message_row).order_by('-row')[:count]
    
    # separate into sent and received lists
    messages_details = messages.values_list("pk", "datetime", "text", "sender__pk", "receiver__pk")
    sent = [message_details[:3] for message_details in messages_details if message_details[3] == account.pk]
    received = [message_details[:3] for message_details in messages_details if message_details[4] == account.pk]
    return JsonResponse(
        {
            "sent": sent,
            "received": received,
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
    # sparse notify the receiver
    text = account.name + " has sent a message to your inbox"
    notify(
        account=contact,
        text=text,
        url=request.build_absolute_uri(reverse("inbox")),
        sparse=True,
    )
    return HttpResponse(status=200)


# ----------------------------------------------------------------------

# account activity page


@authentication_required
def accountActivity(request):
    account = Account.objects.get(username=request.session.get("username"))

    own_activity_item = account.item_logs.order_by("-datetime")
    own_activity_transaction = account.transaction_logs.order_by("-datetime")
    own_activity_item_request = account.item_request_logs.order_by("-datetime")

    item_activity = ItemLog.objects.filter(item__seller=account).order_by("-datetime")
    transaction_activity = TransactionLog.objects.filter(
        transaction__buyer=account
    ).order_by("-datetime")
    item_request_activity = ItemRequestLog.objects.filter(
        item_request__requester=account
    ).order_by("-datetime")

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
                    settings.EMAIL_NAME,
                    [new_email],
                    fail_silently=True,
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


@authentication_required
def cycleAccount(request):
    username = request.session.get("username")

    netids = settings.ADMIN_NETIDS
    suffixes = settings.ALT_ACCOUNT_SUFFIXES

    # must be an admin netid + suffix
    if username not in [netid + suffix for netid in netids for suffix in suffixes]:
        messages.warning(request, "Forbidden, need permission.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    # set the session username to the next netid+suffix
    done = False
    for i in range(len(netids)):
        if done:
            break
        for j in range(len(suffixes)):
            if username == netids[i] + suffixes[j]:
                request.session["username"] = (
                    netids[i] + suffixes[(j + 1) % len(suffixes)]
                )
                done = True
                break

    messages.success(request, "Cycled to alternate account.")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


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
    request.session.pop("username", default=None)
    return redirect(
        CASClient.getLogoutUrl(request.build_absolute_uri(reverse("gallery")))
    )


# ----------------------------------------------------------------------
# repeated server maintenance
# delete expired items/item_requests past timedelta specified in settings
# (and no ongoing transaction)
@background()
def deleteExpired():
    expired_items = Item.objects.filter(
        deadline__lt=timezone.now() - settings.EXPIRATION_BUFFER
    )
    for item in expired_items:
        if item.status == Item.AVAILABLE:
            # send email notice
            send_mail(
                "Expired Item Removed",
                "Your expired item "
                + item.name
                + " has been removed.\nIf you would still like to sell your item, please feel free to relist it.",
                settings.EMAIL_NAME,
                [item.seller.email],
                fail_silently=True,
            )
            # notify the seller
            notify(
                item.seller,
                "Your expired item " + item.name + " has been removed",
                reverse("list_items"),
            )
            # delete the item
            item.delete()

    expired_item_requests = ItemRequest.objects.filter(
        deadline__lt=timezone.now() - settings.EXPIRATION_BUFFER
    )
    for item_request in expired_item_requests:
        # send email notice
        send_mail(
            "Expired Item Request Removed",
            "Your expired item request "
            + item_request.name
            + " has been removed.\nIf you would still like to request the item, please feel free to make another request.",
            settings.EMAIL_NAME,
            [item_request.requester.email],
            fail_silently=True,
        )
        # notify the requester
        notify(
            item_request.requester,
            "Your expired item request " + item_request.name + " has been removed",
            reverse("list_item_requests"),
        )
        # delete the item request
        item_request.delete()
