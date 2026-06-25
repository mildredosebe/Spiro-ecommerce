from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView
from rest_framework.authtoken.views import obtain_auth_token
from django.urls import path
from .views import LoginView
from .views import RegisterView



from api.views import (
    VehicleViewSet,
    UserViewSet,
    CartViewSet,
    CartItemViewSet,
    OrderViewSet,
    OrderItemViewSet,
    PaymentViewSet,
    OrderCreateView,
    STKPushView,
    MpesaCallbackView,
    scalar_docs
)


router = DefaultRouter()
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'users', UserViewSet, basename='user')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'cart-items', CartItemViewSet, basename='cart-item')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-items', OrderItemViewSet, basename='order-item')
router.register(r'payments', PaymentViewSet, basename='payment')



urlpatterns = [

    path('payments/stk-push/', STKPushView.as_view(), name='stk_push'),
    path('payments/callback/', MpesaCallbackView.as_view(), name='mpesa_callback'),
    path('', include(router.urls)),
    path('orders/create/', OrderCreateView.as_view(), name='order_create'),
    path('docs/', scalar_docs, name='api_docs'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path("token/", obtain_auth_token),
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),

]