from django.db import models
from django.forms.widgets import NumberInput
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_delete
from decimal import Decimal
from cloudinary.models import CloudinaryField
import cloudinary.uploader
from datetime import timedelta


# above as in sample https://github.com/cloudinary/cloudinary-django-sample/blob/master/photo_album/models.py

# followed Django documentation on Model fields for the following


class Account(models.Model):
    # username is matched by what is returned from CAS authentication
    username = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=50)
    email = models.EmailField()
    contact = models.CharField(max_length=200)
    contacts = models.ManyToManyField("self")

    def __str__(self):
        return self.username


class Category(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Item(models.Model):
    AVAILABLE = 0
    FROZEN = 1
    COMPLETE = 2
    STATUSES = [
        {
            "index": AVAILABLE,
            "name": "available",
        },
        {
            "index": FROZEN,
            "name": "frozen",
        },
        {
            "index": COMPLETE,
            "name": "complete",
        },
    ]

    NEW = 0
    LIKE_NEW = 1
    GENTLY_LOVED = 2
    WELL_LOVED = 3
    POOR = 4
    CONDITIONS = [
        {
            "index": NEW,
            "name": "new",
        },
        {
            "index": LIKE_NEW,
            "name": "like new",
        },
        {
            "index": GENTLY_LOVED,
            "name": "gently loved",
        },
        {
            "index": WELL_LOVED,
            "name": "well loved",
        },
        {
            "index": POOR,
            "name": "poor",
        },
    ]

    MAX_TIME_DELTA = timedelta(days=365)

    seller = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    posted_date = models.DateTimeField()
    deadline = models.DateField(
        help_text="Latest allowed is " + str((timezone.now() + MAX_TIME_DELTA).date()),
        validators=[
            MinValueValidator(timezone.now().date()),
            MaxValueValidator((timezone.now() + MAX_TIME_DELTA).date()),
        ],
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    negotiable = models.BooleanField()
    condition = models.DecimalField(
        max_digits=1,
        decimal_places=0,
        choices=[
            (CONDITION['index'], CONDITION['name']) for CONDITION in CONDITIONS
        ],
    )
    categories = models.ManyToManyField(Category)
    description = models.CharField(max_length=1000)
    image = CloudinaryField(
        "image",
        format="jpeg",
        transformation=[{"width": 1500, "height": 1500, "crop": "limit"}],
    )
    status = models.DecimalField(
        max_digits=1,
        decimal_places=0,
        choices=[
            (STATUS['index'], STATUS['name']) for STATUS in STATUSES
        ],
    )

    def __str__(self):
        return self.name + " by " + str(self.seller)


# wrapper for CloudinaryField, used for item albums
class AlbumImage(models.Model):
    image = CloudinaryField(
        "image",
        format="jpeg",
        transformation=[{"width": 1500, "height": 1500, "crop": "limit"}],
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="album")

    def __str__(self):
        return str(self.item)


class Transaction(models.Model):
    INITIATED = 0
    ACKNOWLEDGED = 1
    S_PENDING = 2
    B_PENDING = 3
    COMPLETE = 4
    CANCELLED = 5
    STATUSES = [
        {
            "index": INITIATED,
            "name": "initiated",
        },
        {
            "index": ACKNOWLEDGED,
            "name": "acknowledged",
        },
        {
            "index": S_PENDING,
            "name": "seller pending",
        },
        {
            "index": B_PENDING,
            "name": "buyer pending",
        },
        {
            "index": COMPLETE,
            "name": "complete",
        },
        {
            "index": CANCELLED,
            "name": "cancelled",
        },
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    buyer = models.ForeignKey(Account, on_delete=models.CASCADE)
    status = models.DecimalField(
        max_digits=1,
        decimal_places=0,
        choices=[
            (STATUS["index"], STATUS["name"]) for STATUS in STATUSES
        ],
    )

    def __str__(self):
        return str(self.item) + " - status: " + str(self.status)


class ItemLog(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="logs")
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="item_logs"
    )
    datetime = models.DateTimeField()
    log = models.CharField(max_length=100)

    def __str__(self):
        return str(self.item) + " at " + str(self.datetime)


class TransactionLog(models.Model):
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="logs"
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="transaction_logs"
    )
    datetime = models.DateTimeField()
    log = models.CharField(max_length=100)

    def __str__(self):
        return str(self.transaction) + " at " + str(self.datetime)


class ItemRequest(models.Model):

    MAX_TIME_DELTA = timedelta(days=365)

    requester = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    posted_date = models.DateTimeField()
    deadline = models.DateField(
        help_text="Latest allowed is " + str((timezone.now() + MAX_TIME_DELTA).date()),
        validators=[
            MinValueValidator(timezone.now().date()),
            MaxValueValidator((timezone.now() + MAX_TIME_DELTA).date()),
        ],
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    negotiable = models.BooleanField()
    condition = models.DecimalField(
        max_digits=1,
        decimal_places=0,
        choices=[
            (CONDITION['index'], CONDITION['name']) for CONDITION in Item.CONDITIONS
        ],
    )
    categories = models.ManyToManyField(Category)
    description = models.CharField(max_length=1000)
    image = CloudinaryField(
        "image",
        format="jpeg",
        transformation=[{"width": 1500, "height": 1500, "crop": "limit"}],
    )

    def __str__(self):
        return self.name + " by " + str(self.requester)


class ItemRequestLog(models.Model):
    item_request = models.ForeignKey(
        ItemRequest, on_delete=models.CASCADE, related_name="logs"
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="item_request_logs"
    )
    datetime = models.DateTimeField()
    log = models.CharField(max_length=100)

    def __str__(self):
        return str(self.item_request) + " at " + str(self.datetime)


class Message(models.Model):
    sender = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="received_messages"
    )
    datetime = models.DateTimeField()
    text = models.CharField(max_length=2000)


class Notification(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="notifications"
    )
    datetime = models.DateTimeField()
    text = models.CharField(max_length=500)
    seen = models.BooleanField(default=False)
    url = models.URLField()

class ItemFlag(models.Model):
    reporter = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="item_flags", null=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="flags")
    text = models.CharField(max_length=500, blank=True)

class ItemRequestFlag(models.Model):
    reporter = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="item_request_flags", null=True)
    item_request = models.ForeignKey(ItemRequest, on_delete=models.CASCADE, related_name="flags")
    text = models.CharField(max_length=500, blank=True)

############## DELETE CLOUDINARY IMAGES POST_DELETE ###################
@receiver(post_delete, sender=Item)
def deleteItemImage(sender, instance, **kwargs):
    cloudinary.uploader.destroy(str(instance.image))


@receiver(post_delete, sender=AlbumImage)
def deleteAlbumImage(sender, instance, **kwargs):
    cloudinary.uploader.destroy(str(instance.image))


@receiver(post_delete, sender=ItemRequest)
def deleteItemRequestImage(sender, instance, **kwargs):
    cloudinary.uploader.destroy(str(instance.image))
