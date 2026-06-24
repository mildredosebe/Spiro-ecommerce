from django.db import models

# Create your models here.

import uuid
from django.db import models
from user.models import User  

class Cart(models.Model):
    cart_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Spiro_cart'

    def __str__(self):
        return str(self.cart_id)