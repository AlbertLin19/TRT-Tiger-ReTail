from django.shortcuts import render, redirect
from utils import CASClient

# ----------------------------------------------------------------------

# custom authentication_required decorator for protected views

# if user can be authenticated, call view as normal
# otherwise, redirect to CAS login page


def authentication_required(view_function):

    def wrapper(request, *args, **kwargs):

        # if username in session, can call view as normal
        if 'username' in request.session:
            return view_function(request, *args, **kwargs)

        # if request contains a ticket, try validating it
        if 'ticket' in request.GET:
            username = CASClient.validate(
                request.build_absolute_uri(), request.GET['ticket'])

            if username is not None:
                # store authenticated username and call view as normal
                request.session['username'] = username
                return view_function(request, *args, **kwargs)

        # user could NOT be authenticated, so redirect to CAS login
        return redirect(CASClient.getLoginUrl(request.build_absolute_uri()))

    return wrapper

# ----------------------------------------------------------------------

# image gallery


def gallery(request):
    context = {}
    return render(request, 'marketplace/gallery.html', context)

# ----------------------------------------------------------------------

# account settings page


@authentication_required
def account(request):
    context = {}
    return render(request, 'marketplace/gallery.html', context)

# ----------------------------------------------------------------------


def login(request):
    context = {}
    return render(request, 'marketplace/gallery.html', context)


def logout(request):
    context = {}
    return render(request, 'marketplace/gallery.html', context)
