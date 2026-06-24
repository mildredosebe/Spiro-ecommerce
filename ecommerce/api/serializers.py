from rest_framework import serializers
from vehicle.models import Vehicle
from django.contrib.auth.models import User
from user.models import User
from cart.models import Cart
from cart_item.models import CartItem
from order.models import Order
from order_item.models import OrderItem
from payment.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = (
            'payment_id',
            'status',
            'mpesa_checkout_request_id',
            'mpesa_merchant_request_id',
            'mpesa_receipt_number',
            'paid_at',
        )


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'
class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'
class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

class STKPushSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    phone_number = serializers.CharField(max_length=15)

class STKPushCallbackSerializer(serializers.Serializer):
    MerchantRequestID = serializers.CharField(max_length=100)
    CheckoutRequestID = serializers.CharField(max_length=100)
    ResultCode = serializers.IntegerField()
    ResultDesc = serializers.CharField(max_length=255)
    Amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    MpesaReceiptNumber = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    Balance = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    TransactionDate = serializers.DateTimeField(required=False, allow_null=True)
    PhoneNumber = serializers.CharField(max_length=15, required=False, allow_null=True, allow_blank=True)