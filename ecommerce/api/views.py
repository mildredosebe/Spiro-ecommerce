from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action

from vehicle.models import Vehicle
from api.serializers import VehicleSerializer

from user.models import User
from api.serializers import UserSerializer
from cart.models import Cart
from api.serializers import CartSerializer
from cart_item.models import CartItem
from api.serializers import CartItemSerializer
from order.models import Order
from api.serializers import OrderSerializer

from order_item.models import OrderItem
from api.serializers import OrderItemSerializer

from payment.models import Payment
from api.serializers import PaymentSerializer

from api.serializers import STKPushSerializer
from drf_spectacular.utils import extend_schema

from api.serializers import STKPushCallbackSerializer

from payment.service.mpesa import stk_push
from django.utils import timezone
from django.http import HttpResponse
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import LoginSerializer
import logging
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from user.models import User

logger = logging.getLogger(__name__)


class OrderCreateView(APIView):
    """
    Create an order. A Payment record will be automatically created via signal.
    Authentication is optional for now (testing).
    """
    permission_classes = [AllowAny]  

    def post(self, request):
        """
        Create an order with items.
        
        Expected payload:
        {
            "user_id": "uuid",
            "shipping_address": "123 Main St",
            "items": [
                {
                    "vehicle_id": "uuid",
                    "quantity": 2,
                    "price": "15000.00"
                }
            ]
        }
        """
        try:
            user_id = request.data.get("user_id")
            shipping_address = request.data.get("shipping_address")
            items = request.data.get("items", [])

            if not user_id or not shipping_address or not items:
                return Response(
                    {"error": "user_id, shipping_address, and items are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.get(id=user_id)

            # Calculate total amount
            total_amount = sum(
                float(item.get("price", 0)) * item.get("quantity", 1)
                for item in items
            )

            # Create order
            order = Order.objects.create(
                user=user,
                total_amount=total_amount,
                shipping_address=shipping_address,
                payment_status="pending",
                order_status="pending"
            )

            logger.info(f"Order created: {order.order_id} for user {user_id}")

            # Create order items
            for item_data in items:
                vehicle_id = item_data.get("vehicle_id")
                quantity = item_data.get("quantity")
                price = item_data.get("price")

                vehicle = Vehicle.objects.get(id=vehicle_id)

                OrderItem.objects.create(
                    order=order,
                    vehicle=vehicle,
                    quantity=quantity,
                    price=price
                )

            # Payment is automatically created via signal in order.models
            payment = Payment.objects.get(order=order)

            logger.info(f"Payment auto-created: {payment.id} for order {order.order_id}")

            return Response({
                "success": True,
                "message": "Order created successfully",
                "order_id": str(order.order_id),
                "payment_id": payment.id,
                "total_amount": str(order.total_amount),
                "payment_status": payment.status
            }, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            logger.error(f"User not found: {user_id}")
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Vehicle.DoesNotExist:
            logger.error(f"Vehicle not found in items: {items}")
            return Response(
                {"error": "Vehicle not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )




class STKPushView(APIView):
    """
    Initiate M-Pesa STK push for an existing order.
    Requires: order_id and phone_number
    """
    permission_classes = [AllowAny]  # TODO: Change to [IsAuthenticated] in production

    @extend_schema(
        request=STKPushSerializer,
        responses={200: dict}
    )

    def post(self, request):
        """
        Initiate STK push payment.
        
        Expected payload:
        {
            "order_id": "uuid",
            "phone_number": "254712345678"
        }
        """
        order_id = request.data.get("order_id")
        phone_number = request.data.get("phone_number")

        if not order_id or not phone_number:
            return Response(
                {"error": "order_id and phone_number are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order not found: {order_id}")
            return Response(
                {"error": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            payment = Payment.objects.filter(order=order).order_by("-id").first()
            payment.phone_number = phone_number
            payment.save(update_fields=["phone_number"])
            order.phone_number = phone_number
            order.save(update_fields=["phone_number"])

            logger.info(f"Initiating STK push for order {order_id} to {phone_number}")

            # Call M-Pesa STK push
            callback_url = "https://spiro-ecommerce.onrender.com/api/payments/callback/"

            try:
                mpesa_response = stk_push(
                    phone_number=phone_number,
                    amount=order.total_amount,
                    account_reference=str(order.order_id),
                    transaction_desc="Spiro Bike Order",
                    callback_url=callback_url,
                    payment=payment
                )

                logger.info(f"M-Pesa response: {mpesa_response}")

                # Check for errors in response
                if mpesa_response.get("ResponseCode") != "0":
                    error_msg = mpesa_response.get("ResponseDescription", "M-Pesa error")
                    logger.error(f"M-Pesa error: {error_msg}")
                    payment.mark_as_failed(error_message=error_msg)
                    return Response({
                        "success": False,
                        "error": error_msg
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Extract M-Pesa response details
                checkout_request_id = mpesa_response.get("CheckoutRequestID")
                merchant_request_id = mpesa_response.get("MerchantRequestID")

                if not checkout_request_id:
                    error_msg = "No CheckoutRequestID from M-Pesa"
                    logger.error(error_msg)
                    return Response({
                        "success": False,
                        "error": error_msg
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Update payment record
                payment.mpesa_checkout_request_id = checkout_request_id
                payment.merchant_request_id = merchant_request_id
                payment.mark_as_waiting()  # Sets status to waiting_for_payment and timestamp

                # Update order record
                order.checkout_request_id = checkout_request_id
                order.merchant_request_id = merchant_request_id
                order.save(update_fields=["checkout_request_id", "merchant_request_id"])

                logger.info(f"STK push sent successfully for order {order_id}")

                return Response({
                    "success": True,
                    "message": "STK Push sent successfully",
                    "order_id": str(order.order_id),
                    "payment_id": payment.id,
                    "mpesa_response": mpesa_response
                }, status=status.HTTP_200_OK)

            except Exception as e:
                error_msg = f"M-Pesa API error: {str(e)}"
                logger.error(error_msg)
                payment.increment_retry()
                payment.mark_as_failed(error_message=error_msg)
                return Response({
                    "success": False,
                    "error": error_msg
                }, status=status.HTTP_400_BAD_REQUEST)

        except Payment.DoesNotExist:
            logger.error(f"Payment not found for order {order_id}")
            return Response(
                {"error": "Payment not found for this order"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Unexpected error in STK push: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )




class MpesaCallbackView(APIView):
    """
    Receive M-Pesa STK push callback.
    No authentication required (M-Pesa servers call this).
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=STKPushCallbackSerializer,
        responses={200: dict}
    )

    def post(self, request):
        logger.info(f"M-Pesa callback received: {request.data}")

        data = request.data

        try:
            # CASE 1: Safaricom standard format
            if "Body" in data:
                callback = data["Body"]["stkCallback"]
                checkout_id = callback["CheckoutRequestID"]
                result_code = callback["ResultCode"]
                result_desc = callback.get("ResultDesc", "")
                metadata_items = callback.get("CallbackMetadata", {}).get("Item", [])

                receipt_number = None
                for item in metadata_items:
                    if item.get("Name") == "MpesaReceiptNumber":
                        receipt_number = item.get("Value")

            # CASE 2: Your flattened format (what you're receiving)
            else:
                checkout_id = data.get("CheckoutRequestID")
                result_code = data.get("ResultCode")
                result_desc = data.get("ResultDesc", "")
                receipt_number = data.get("MpesaReceiptNumber")

            if not checkout_id:
                return Response(
                    {"error": "Missing CheckoutRequestID"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Callback parse error: {str(e)}")
            return Response(
                {"error": "Invalid callback format"},
                status=status.HTTP_400_BAD_REQUEST
            )



        try:
            payment = Payment.objects.get(
                mpesa_checkout_request_id=checkout_id
            )
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        order = payment.order

        if str(result_code) == "0":
            payment.mark_as_paid(receipt_number=receipt_number)

            order.payment_status = "paid"
            order.order_status = "processing"
            order.mpesa_receipt_number = receipt_number
            order.paid_at = timezone.now()
            order.transaction_date = timezone.now()
            order.save()

        else:
            payment.mark_as_failed(error_message=result_desc)

            order.payment_status = "failed"
            order.save()

        return Response({"ResultCode": 0, "ResultDesc": "We have received the callback"}, status=status.HTTP_200_OK)




class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer


class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


# ============================================================================
# DOCUMENTATION
# ============================================================================

def scalar_docs(request):
    html = """
    <!doctype html>
    <html>
    <head>
      <title>API Docs</title>
      <meta charset="utf-8">
    </head>
    <body>
      <script
        id="api-reference"
        data-url="/api/schema/"
      ></script>

      <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    </body>
    </html>
    """
    return HttpResponse(html)
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import LoginSerializer
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from user.models import User


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: dict}
    )

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

      
        user = authenticate(request, username=email, password=password)

        # fallback if backend doesn't map email properly
        if user is None:
            try:
                user_obj = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid email or password"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not user_obj.check_password(password):
                return Response(
                    {"error": "Invalid email or password"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            user = user_obj

        if not user.is_active:
            return Response(
                {"error": "User account is disabled"},
                status=status.HTTP_403_FORBIDDEN
            )

       
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "user_type": user.user_type,
            }
        })

from rest_framework import generics
from rest_framework.permissions import AllowAny
from user.models import User
from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

def perform_create(self, serializer):
    serializer.save(user=self.request.user)