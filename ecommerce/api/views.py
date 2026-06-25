"""
Spiro API Views
Handles order creation, M-Pesa STK push, callbacks, and user authentication.
"""

import logging
from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth import authenticate

from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from vehicle.models import Vehicle
from api.serializers import VehicleSerializer
from user.models import User
from api.serializers import UserSerializer, LoginSerializer, RegisterSerializer
from cart.models import Cart
from api.serializers import CartSerializer
from cart_item.models import CartItem
from api.serializers import CartItemSerializer
from order.models import Order
from api.serializers import OrderSerializer
from order_item.models import OrderItem
from api.serializers import OrderItemSerializer
from payment.models import Payment
from api.serializers import PaymentSerializer, STKPushSerializer, STKPushCallbackSerializer
from payment.service.mpesa import stk_push

logger = logging.getLogger(__name__)


class LoginView(APIView):
    """
    User login with email and password.
    Returns JWT access and refresh tokens.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: dict}
    )
    def post(self, request):
        """
        Authenticate user and return tokens.
        
        Expected payload:
        {
            "email": "user@example.com",
            "password": "password123"
        }
        """
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)

        if user is None:
            try:
                user = User.objects.get(email=email)
                if not user.check_password(password):
                    raise User.DoesNotExist
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid email or password"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

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
        }, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    """
    User registration.
    Creates a new user account.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        serializer.save()


class OrderCreateView(APIView):
    """
    Create a new order with items.
    A Payment record is automatically created via Django signal.
    """
    permission_classes = [IsAuthenticated]  # TODO: Change to [IsAuthenticated] in production

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

            order = Order.objects.create(
                user=user,
                total_amount=total_amount,
                shipping_address=shipping_address,
                payment_status="pending",
                order_status="pending"
            )

            logger.info(f"Order created: {order.order_id} for user {user_id}")

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
            logger.error(f"Vehicle not found in items")
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
    permission_classes = [IsAuthenticated]

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
            
            if not payment:
                raise Payment.DoesNotExist

            payment.phone_number = phone_number
            payment.save(update_fields=["phone_number"])
            order.phone_number = phone_number
            order.save(update_fields=["phone_number"])

            logger.info(f"Initiating STK push for order {order_id} to {phone_number}")

            callback_url = "https://spiro-ecommerce.onrender.com/api/payments/callback/"

            mpesa_response = stk_push(
                phone_number=phone_number,
                amount=order.total_amount,
                account_reference=str(order.order_id),
                transaction_desc="Spiro Bike Order",
                callback_url=callback_url,
                payment=payment
            )

            logger.info(f"M-Pesa response: {mpesa_response}")

            if mpesa_response.get("ResponseCode") != "0":
                error_msg = mpesa_response.get("ResponseDescription", "M-Pesa error")
                logger.error(f"M-Pesa error: {error_msg}")
                payment.mark_as_failed(error_message=error_msg)
                return Response({
                    "success": False,
                    "error": error_msg
                }, status=status.HTTP_400_BAD_REQUEST)

            checkout_request_id = mpesa_response.get("CheckoutRequestID")
            merchant_request_id = mpesa_response.get("MerchantRequestID")

            if not checkout_request_id:
                error_msg = "No CheckoutRequestID from M-Pesa"
                logger.error(error_msg)
                return Response({
                    "success": False,
                    "error": error_msg
                }, status=status.HTTP_400_BAD_REQUEST)

            payment.mpesa_checkout_request_id = checkout_request_id
            payment.merchant_request_id = merchant_request_id
            payment.mark_as_waiting()

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

        except Payment.DoesNotExist:
            logger.error(f"Payment not found for order {order_id}")
            return Response(
                {"error": "Payment not found for this order"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in STK push: {str(e)}")
            if payment:
                payment.increment_retry()
                payment.mark_as_failed(error_message=str(e))
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class MpesaCallbackView(APIView):
    """
    Receive M-Pesa STK push callback.
    No authentication required (M-Pesa servers call this endpoint).
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=STKPushCallbackSerializer,
        responses={200: dict}
    )
    def post(self, request):
        """
        Process M-Pesa callback and update payment status.
        Handles both Safaricom standard format and flattened format.
        """
        logger.info(f"M-Pesa callback received: {request.data}")

        data = request.data

        try:
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

            else:
                checkout_id = data.get("CheckoutRequestID")
                result_code = data.get("ResultCode")
                result_desc = data.get("ResultDesc", "")
                receipt_number = data.get("MpesaReceiptNumber")

            if not checkout_id:
                logger.warning("Missing CheckoutRequestID in callback")
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
            payment = Payment.objects.get(mpesa_checkout_request_id=checkout_id)
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for checkout_id: {checkout_id}")
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
            logger.info(f"Payment successful for order {order.order_id}")
        else:
            payment.mark_as_failed(error_message=result_desc)
            order.payment_status = "failed"
            logger.warning(f"Payment failed for order {order.order_id}: {result_desc}")

        order.save()

        return Response(
            {"ResultCode": 0, "ResultDesc": "We have received the callback"},
            status=status.HTTP_200_OK
        )

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


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

def scalar_docs(request):
    """
    Serve API documentation with Scalar UI.
    """
    html = """
    <!doctype html>
    <html>
    <head>
      <title>Spiro API Docs</title>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
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