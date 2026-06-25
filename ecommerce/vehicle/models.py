from django.db import models
import uuid
from django.db import models
class Vehicle(models.Model):
    vehicle_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    vehicle_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    range_km = models.IntegerField()
    stock_quantity = models.IntegerField(default=0)
    image_url = models.ImageField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
  
    class Meta:
        db_table = 'vehicle'
        managed = True

    def __str__(self):
        return self.vehicle_name