from django.db import models

class UserProfile(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()

class Category(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()

class Item(models.Model):
    AVAILABLE = 0
    FROZEN = 1
    COMPLETE = 2

    seller = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    posted_date = models.DateTimeField()
    deadline = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quality = models.DecimalField(max_digits=1, decimal_places=0)
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
    seller = models.ForeignKey(UserProfile, related_name='sale_transaction', on_delete=models.CASCADE)
    buyer = models.ForeignKey(UserProfile, related_name='purchase_transaction', on_delete=models.CASCADE)
    status = models.DecimalField(max_digits=1, decimal_places=0,
        choices = [
            (INITIATED, 'initiated'),
            (ACKNOWLEDGED, 'acknowledged'),
            (S_PENDING, 's_pending'),
            (B_PENDING, 'b_pending'),
            (COMPLETE, 'complete'),
        ]
    )
