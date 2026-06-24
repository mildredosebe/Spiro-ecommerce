from django.db import models

# Create your models here.
import uuid
from django.db import models
 # adjust if your app name differs
from vehicle.models import Vehicle  # adjust if your app name differs
from django.core.validators import MinValueValidator
from order.models import Order  # adjust if your app name differs
class OrderItem(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        db_column='order_id'
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        db_column='vehicle_id'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    class Meta:
        db_table = 'spiro_order_items'

    def __str__(self):
        return f"{self.id}"