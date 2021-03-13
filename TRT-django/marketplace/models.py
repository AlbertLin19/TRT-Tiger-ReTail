from django.db import models

# followed Django documentation on Model fields for the following

class Account(models.Model):
    # username is matched by what is returned from CAS authentication
    username = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=50)
    email = models.EmailField()

class Category(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()

class Item(models.Model):
    AVAILABLE = 0
    FROZEN = 1
    COMPLETE = 2

    NEW = 0
    LIKE_NEW = 1
    GOOD = 2
    FAIR = 3
    POOR = 4

    seller = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    posted_date = models.DateTimeField()
    deadline = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    condition = models.DecimalField(max_digits=1, decimal_places=0,
        choices = [
            (NEW, 'new'),
            (LIKE_NEW, 'like_new'),
            (GOOD, 'good'),
            (FAIR, 'fair'),
            (POOR, 'poor')
        ])
    categories = models.ManyToManyField(Category)
    description = models.TextField()
    image = models.ImageField()
    status = models.DecimalField(max_digits=1, decimal_places=0, 
        choices = [
            (AVAILABLE, 'available'),
            (FROZEN, 'frozen'),
            (COMPLETE, 'complete'),
        ])

class Transaction(models.Model):
    INITIATED = 0
    ACKNOWLEDGED = 1
    S_PENDING = 2
    B_PENDING = 3
    COMPLETE = 4

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    buyer = models.ForeignKey(Account, on_delete=models.CASCADE)
    status = models.DecimalField(max_digits=1, decimal_places=0,
        choices = [
            (INITIATED, 'initiated'),
            (ACKNOWLEDGED, 'acknowledged'),
            (S_PENDING, 's_pending'),
            (B_PENDING, 'b_pending'),
            (COMPLETE, 'complete'),
        ]
    )
