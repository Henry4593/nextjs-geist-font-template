from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('<int:product_id>/', views.product_detail, name='product_detail'),
    path('category/<str:category_slug>/', views.product_list, name='product_list_by_category'),
    path('api/filter/', views.filter_products, name='filter_products'),
    path('api/search/', views.search_products, name='search_products'),
]
