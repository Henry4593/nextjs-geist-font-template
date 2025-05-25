from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('account/', views.account_view, name='account'),
    path('account/orders/', views.order_history_view, name='order_history'),
    path('account/settings/', views.account_settings_view, name='account_settings'),
    path('password/reset/', views.password_reset_view, name='password_reset'),
    path('password/reset/confirm/<uidb64>/<token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
]
