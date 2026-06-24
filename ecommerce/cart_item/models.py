from django.db import models

# Create your models here.
import uuid
from django.db import models
from cart.models import Cart  # adjust if your app name differs
from vehicle.models import Vehicle  # adjust if your app name differs

class CartItem(models.Model):
    cart_items_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        db_column='cart_id'
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        db_column='vehicle_id'
    )
    quantity = models.IntegerField(default=1)

    class Meta:
        db_table = 'Spiro_cart_items'

    def __str__(self):
        return f"{self.cart_items_id}"