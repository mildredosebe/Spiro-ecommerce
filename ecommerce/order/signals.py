from django.db.models.signals import post_save
from django.dispatch import receiver
from order.models import Order
from payment.models import Payment


@receiver(post_save, sender=Order)
def create_payment_on_order_creation(sender, instance, created, **kwargs):
    if created:
        if not Payment.objects.filter(order=instance).exists():
            Payment.objects.create(
                user=instance.user,
                order=instance,
                amount=instance.total_amount,
                status="pending",
                phone_number=None,
                mpesa_checkout_request_id=None,
            )

