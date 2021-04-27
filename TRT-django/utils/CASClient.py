#!/usr/bin/env python

# -----------------------------------------------------------------------
# CASClient.py
# Lots taken from provided COS333 CASClient.py example written by
# Authors: Alex Halderman, Scott Karlin, Brian Kernighan, Bob Dondero

# utility functions related to CAS authentication
# -----------------------------------------------------------------------

from urllib.request import urlopen
from urllib.parse import quote
from re import sub, match
from sys import stderr
from django.conf import settings

# -----------------------------------------------------------------------

# Return url after stripping out "ticket" parameter added by CAS server


def stripTicket(url):
    if url is None:
        return ""
    url = sub(r"ticket=[^&]*&?", "", url)
    url = sub(r"\?&?$|&$", "", url)
    return url


# -----------------------------------------------------------------------

# Validate a login ticket in the url by contacting the CAS server. If
# valid, return the user's username; otherwise, return None.


def validate(url, ticket):
    val_url = (
        settings.CAS_URL
        + "validate"
        + "?service="
        + quote(stripTicket(url))
        + "&ticket="
        + quote(ticket)
    )
    r = urlopen(val_url).readlines()  # returns 2 lines
    if len(r) != 2:
        return None
    firstLine = r[0].decode("utf-8")
    secondLine = r[1].decode("utf-8")
    if not firstLine.startswith("yes"):
        return None
    return secondLine


# -----------------------------------------------------------------------

# Return the url for the CAS authentication login page


def getLoginUrl(url):
    return settings.CAS_URL + "login" + "?service=" + quote(stripTicket(url))


# -----------------------------------------------------------------------

# Return the url for the CAS authentication logout page


def getLogoutUrl(url):
    return settings.CAS_URL + "logout" + "?service=" + quote(stripTicket(url))


# -----------------------------------------------------------------------
