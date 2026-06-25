"""
Spiro API Serializers
Serializes models to/from JSON for API endpoints.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

from vehicle.models import Vehicle
from user.models import User
from cart.models import Cart
from cart_item.models import CartItem
from order.models import Order
from order_item.models import OrderItem
from payment.models import Payment

class LoginSerializer(TokenObtainPairSerializer):
    """
    Custom login serializer that authenticates using email.
    Returns JWT tokens and user info.
    """
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


class RegisterSerializer(serializers.ModelSerializer):
    """
    User registration serializer.
    Accepts email, password, and user details.
    """
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("id", "full_name", "email", "phone_number", "address", "password")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class VehicleSerializer(serializers.ModelSerializer):
    """
    Serializer for Vehicle model.
    Represents bikes/vehicles available for order.
    """
    class Meta:
        model = Vehicle
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    Includes user profile information.
    """
    class Meta:
        model = User
        fields = '__all__'

class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for Cart model.
    Represents a user's shopping cart.
    """
    class Meta:
        model = Cart
        fields = '__all__'
        read_only_fields = ('user', 'cart_id')


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for CartItem model.
    Represents individual items in a cart.
    """
    class Meta:
        model = CartItem
        fields = '__all__'



class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order model.
    Represents a completed order.
    """
    class Meta:
        model = Order
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderItem model.
    Represents individual items in an order.
    """
    class Meta:
        model = OrderItem
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Payment model.
    Represents payment records for orders.
    """
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


class STKPushSerializer(serializers.Serializer):
    """
    Serializer for STK Push request.
    Initiates M-Pesa payment prompt on user's phone.
    """
    order_id = serializers.UUIDField()
    phone_number = serializers.CharField(max_length=15)


class STKPushCallbackSerializer(serializers.Serializer):
    """
    Serializer for M-Pesa STK Push callback response.
    Handles payment result data from Safaricom.
    """
    MerchantRequestID = serializers.CharField(max_length=100)
    CheckoutRequestID = serializers.CharField(max_length=100)
    ResultCode = serializers.IntegerField()
    ResultDesc = serializers.CharField(max_length=255)
    Amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    MpesaReceiptNumber = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True
    )
    Balance = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    TransactionDate = serializers.DateTimeField(
        required=False,
        allow_null=True
    )
    PhoneNumber = serializers.CharField(
        max_length=15,
        required=False,
        allow_null=True,
        allow_blank=True
    )