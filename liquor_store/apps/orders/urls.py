from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/shipping/', views.checkout_shipping, name='checkout_shipping'),
    path('checkout/payment/', views.checkout_payment, name='checkout_payment'),
    path('checkout/complete/', views.checkout_complete, name='checkout_complete'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('api/cart/count/', views.get_cart_count, name='get_cart_count'),
    path('api/cart/total/', views.get_cart_total, name='get_cart_total'),
]
