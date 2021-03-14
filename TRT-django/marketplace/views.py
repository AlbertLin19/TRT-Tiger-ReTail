from django.shortcuts import render, redirect
from django.contrib import messages
from utils import CASClient

import cloudinary
import cloudinary.uploader
import cloudinary.api

# ----------------------------------------------------------------------

# custom authentication_required decorator for protected views

# if user can be authenticated, call view as normal
# otherwise, redirect to CAS login page


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
                # store authenticated username and call view as normal
                request.session["username"] = username
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
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# personal items page


def listItems(request):
    messages.success(
        request, "This is a demonstration of the messages system via the base template!"
    )
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------

# new item form
# GET requests given a blank form
# POST requests given a form with error feedback, else new item created


def newItem(request):
    messages.success(
        request, "This is a demonstration of the messages system via the base template!"
    )
    context = {}
    return render(request, "marketplace/gallery.html", context)


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
def account(request):
    context = {}
    return render(request, "marketplace/gallery.html", context)


# ----------------------------------------------------------------------


def logout(request):
    request.session.pop("username")
    return redirect(CASClient.getLogoutUrl())
