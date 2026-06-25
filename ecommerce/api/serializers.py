from rest_framework import serializers
from vehicle.models import Vehicle
from django.contrib.auth.models import User
from user.models import User
from cart.models import Cart
from cart_item.models import CartItem
from order.models import Order
from order_item.models import OrderItem
from payment.models import Payment
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


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
    from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers


class LoginSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password
        )

        if not user:
            raise serializers.ValidationError(
                "Invalid email or password"
            )

        refresh = self.get_token(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type,
            }
        }