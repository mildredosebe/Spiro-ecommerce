from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView

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


# DRF Router for ViewSets
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
    path('', include(router.urls)),
    
    path('orders/create/', OrderCreateView.as_view(), name='order_create'),
    
    
    
    path('payments/callback/', MpesaCallbackView.as_view(), name='mpesa_callback'),
    
    path('docs/', scalar_docs, name='api_docs'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]