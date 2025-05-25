from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='index'),
    path('products/', views.product_list_view, name='product_list'),
    path('products/add/', views.product_add_view, name='product_add'),
    path('products/edit/<int:product_id>/', views.product_edit_view, name='product_edit'),
    path('products/delete/<int:product_id>/', views.product_delete_view, name='product_delete'),
    path('orders/', views.order_list_view, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
    path('orders/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('users/', views.user_list_view, name='user_list'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('inventory/', views.inventory_view, name='inventory'),
    path('api/stats/', views.get_dashboard_stats, name='get_stats'),
    path('api/sales-chart/', views.get_sales_chart_data, name='get_sales_chart'),
    path('api/inventory-alerts/', views.get_inventory_alerts, name='get_inventory_alerts'),
]
