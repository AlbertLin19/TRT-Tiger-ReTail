from django.db import models
from django.forms.widgets import NumberInput
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from cloudinary.models import CloudinaryField
from datetime import timedelta


# above as in sample https://github.com/cloudinary/cloudinary-django-sample/blob/master/photo_album/models.py

# followed Django documentation on Model fields for the following


class Account(models.Model):
    # username is matched by what is returned from CAS authentication
    username = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=50)
    email = models.EmailField()

    def __str__(self):
        return self.username


class Category(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return self.name


class Item(models.Model):
    AVAILABLE = 0
    FROZEN = 1
    COMPLETE = 2

    NEW = 0
    LIKE_NEW = 1
    GENTLY_LOVED = 2
    WELL_LOVED = 3
    POOR = 4

    MAX_TIME_DELTA = timedelta(days=365)

    seller = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, verbose_name="")
    posted_date = models.DateTimeField()
    deadline = models.DateField(
        help_text="Latest allowed is " + str((timezone.now() + MAX_TIME_DELTA).date()),
        verbose_name="Deadline to Sell",
        validators=[
            MinValueValidator(timezone.now().date()),
            MaxValueValidator((timezone.now() + MAX_TIME_DELTA).date()),
        ],
    )
    price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    condition = models.DecimalField(
        max_digits=1,
        decimal_places=0,
        choices=[
            (NEW, "New"),
            (LIKE_NEW, "Like new"),
            (GENTLY_LOVED, "Gently-loved"),
            (WELL_LOVED, "Well-loved"),
            (POOR, "Poor"),
        ],
    )
    categories = models.ManyToManyField(Category)
    description = models.TextField()
    image = CloudinaryField("image")
    status = models.DecimalField(
        max_digits=1,
        decimal_places=0,
        choices=[
            (AVAILABLE, "available"),
            (FROZEN, "frozen"),
            (COMPLETE, "complete"),
        ],
    )

    def __str__(self):
        return self.name + " by " + str(self.seller)


class Transaction(models.Model):
    INITIATED = 0
    ACKNOWLEDGED = 1
    S_PENDING = 2
    B_PENDING = 3
    COMPLETE = 4
    CANCELLED = 5

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    buyer = models.ForeignKey(Account, on_delete=models.CASCADE)
    status = models.DecimalField(
        max_digits=1,
        decimal_places=0,
        choices=[
            (INITIATED, "initiated"),
            (ACKNOWLEDGED, "acknowledged"),
            (S_PENDING, "s_pending"),
            (B_PENDING, "b_pending"),
            (COMPLETE, "complete"),
            (CANCELLED, "cancelled"),
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