from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from datetime import datetime
import json
import uuid
from .models import Cart, CartItem, Order, OrderItem, OrderStatus, PaymentStatus
from ..products.models import Product
from ..users.models import Address
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
import os
from urllib.parse import quote_plus

db_settings = settings.DATABASES['default']
engine = None

if db_settings['ENGINE'] == 'django.db.backends.sqlite3':
    db_path = db_settings['NAME']
    if not os.path.isabs(db_path):
        db_path = os.path.join(settings.BASE_DIR, db_path)
    engine = create_engine(f'sqlite:///{db_path}')
else:
    user = quote_plus(db_settings.get('USER', ''))
    password = quote_plus(db_settings.get('PASSWORD', ''))
    host = db_settings.get('HOST', '')
    port = db_settings.get('PORT', '')
    name = db_settings.get('NAME', '')
    port_part = f":{port}" if port else ''
    engine = create_engine(f'postgresql://{user}:{password}@{host}{port_part}/{name}')

def get_db_session():
    """Create and return a new database session"""
    return Session(engine)

def get_or_create_cart(request):
    """Get existing cart or create new one"""
    session = get_db_session()
    try:
        if request.user.is_authenticated:
            cart = session.query(Cart).filter(Cart.user_id == request.user.id).first()
            if not cart:
                cart = Cart(user_id=request.user.id)
                session.add(cart)
                session.commit()
        else:
            session_id = request.session.get('cart_id')
            if session_id:
                cart = session.query(Cart).filter(Cart.session_id == session_id).first()
                if not cart:
                    cart = Cart(session_id=session_id)
                    session.add(cart)
                    session.commit()
            else:
                session_id = str(uuid.uuid4())
                request.session['cart_id'] = session_id
                cart = Cart(session_id=session_id)
                session.add(cart)
                session.commit()
        return cart
    except Exception as e:
        logger.error(f"Error in get_or_create_cart: {str(e)}")
        return None
    finally:
        session.close()

def cart_view(request):
    """Display shopping cart"""
    session = get_db_session()
    try:
        cart = get_or_create_cart(request)
        if not cart:
            return render(request, 'orders/cart.html', {'error': 'Unable to load cart.'})

        return render(request, 'orders/cart.html', {
            'cart': cart.to_dict()
        })
    except Exception as e:
        logger.error(f"Error in cart_view: {str(e)}")
        return render(request, 'orders/cart.html', {
            'error': 'An error occurred while loading your cart.'
        })
    finally:
        session.close()

def add_to_cart(request, product_id):
    """Add item to cart"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    session = get_db_session()
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            return JsonResponse({'error': 'Invalid quantity.'}, status=400)

        product = session.query(Product).get(product_id)
        if not product:
            return JsonResponse({'error': 'Product not found.'}, status=404)

        cart = get_or_create_cart(request)
        if not cart:
            return JsonResponse({'error': 'Unable to access cart.'}, status=500)

        cart.add_item(product, quantity)
        session.commit()

        return JsonResponse({
            'success': True,
            'cart': cart.to_dict()
        })

    except Exception as e:
        logger.error(f"Error in add_to_cart: {str(e)}")
        return JsonResponse({'error': 'An error occurred while adding to cart.'}, status=500)
    finally:
        session.close()

def remove_from_cart(request, item_id):
    """Remove item from cart"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    session = get_db_session()
    try:
        cart = get_or_create_cart(request)
        if not cart:
            return JsonResponse({'error': 'Unable to access cart.'}, status=500)

        item = session.query(CartItem).get(item_id)
        if not item or item.cart_id != cart.id:
            return JsonResponse({'error': 'Item not found.'}, status=404)

        session.delete(item)
        session.commit()

        return JsonResponse({
            'success': True,
            'cart': cart.to_dict()
        })

    except Exception as e:
        logger.error(f"Error in remove_from_cart: {str(e)}")
        return JsonResponse({'error': 'An error occurred while removing from cart.'}, status=500)
    finally:
        session.close()

def update_cart_item(request, item_id):
    """Update cart item quantity"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    session = get_db_session()
    try:
        quantity = int(request.POST.get('quantity', 0))
        if quantity < 1:
            return JsonResponse({'error': 'Invalid quantity.'}, status=400)

        cart = get_or_create_cart(request)
        if not cart:
            return JsonResponse({'error': 'Unable to access cart.'}, status=500)

        item = session.query(CartItem).get(item_id)
        if not item or item.cart_id != cart.id:
            return JsonResponse({'error': 'Item not found.'}, status=404)

        item.quantity = quantity
        item.calculate_subtotal()
        session.commit()

        return JsonResponse({
            'success': True,
            'cart': cart.to_dict()
        })

    except Exception as e:
        logger.error(f"Error in update_cart_item: {str(e)}")
        return JsonResponse({'error': 'An error occurred while updating cart.'}, status=500)
    finally:
        session.close()

@login_required
def checkout_view(request):
    """Display checkout page"""
    session = get_db_session()
    try:
        cart = get_or_create_cart(request)
        if not cart or not cart.items:
            return redirect('orders:cart')

        # Get user's addresses
        addresses = session.query(Address).filter(Address.user_id == request.user.id).all()

        return render(request, 'orders/checkout.html', {
            'cart': cart.to_dict(),
            'addresses': [addr.to_dict() for addr in addresses]
        })

    except Exception as e:
        logger.error(f"Error in checkout_view: {str(e)}")
        return render(request, 'orders/checkout.html', {
            'error': 'An error occurred during checkout.'
        })
    finally:
        session.close()

@login_required
def checkout_shipping(request):
    """Handle shipping information"""
    if request.method != 'POST':
        return redirect('orders:checkout')

    session = get_db_session()
    try:
        cart = get_or_create_cart(request)
        if not cart or not cart.items:
            return redirect('orders:cart')

        shipping_address_id = request.POST.get('shipping_address')
        if not shipping_address_id:
            return render(request, 'orders/checkout.html', {
                'error': 'Please select a shipping address.'
            })

        # Store shipping info in session
        request.session['checkout_shipping'] = {
            'address_id': shipping_address_id
        }

        return redirect('orders:checkout_payment')

    except Exception as e:
        logger.error(f"Error in checkout_shipping: {str(e)}")
        return render(request, 'orders/checkout.html', {
            'error': 'An error occurred while processing shipping information.'
        })
    finally:
        session.close()

@login_required
def checkout_payment(request):
    """Handle payment processing"""
    if request.method != 'POST':
        return redirect('orders:checkout')

    session = get_db_session()
    try:
        cart = get_or_create_cart(request)
        if not cart or not cart.items:
            return redirect('orders:cart')

        shipping_info = request.session.get('checkout_shipping')
        if not shipping_info:
            return redirect('orders:checkout')

        # Create order
        order = Order(
            user_id=request.user.id,
            shipping_address_id=shipping_info['address_id'],
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            shipping_cost=10.00,  # Fixed shipping cost for now
            subtotal=cart.subtotal,
            tax=cart.subtotal * 0.1,
            total=cart.total + 10.00  # Including shipping cost
        )
        session.add(order)

        # Create order items
        for item in cart.items:
            order_item = OrderItem(
                order=order,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
                subtotal=item.subtotal
            )
            session.add(order_item)

        # Clear cart
        session.delete(cart)
        session.commit()

        # Clear checkout session
        request.session.pop('checkout_shipping', None)

        return redirect('orders:checkout_complete')

    except Exception as e:
        logger.error(f"Error in checkout_payment: {str(e)}")
        return render(request, 'orders/checkout.html', {
            'error': 'An error occurred while processing your payment.'
        })
    finally:
        session.close()

@login_required
def checkout_complete(request):
    """Display order confirmation"""
    return render(request, 'orders/checkout_complete.html')

@login_required
def order_detail(request, order_id):
    """Display order details"""
    session = get_db_session()
    try:
        order = session.query(Order).get(order_id)
        if not order or order.user_id != request.user.id:
            return redirect('users:order_history')

        return render(request, 'orders/order_detail.html', {
            'order': order.to_dict()
        })

    except Exception as e:
        logger.error(f"Error in order_detail: {str(e)}")
        return render(request, 'orders/order_detail.html', {
            'error': 'An error occurred while loading the order details.'
        })
    finally:
        session.close()

def get_cart_count(request):
    """Get number of items in cart"""
    session = get_db_session()
    try:
        cart = get_or_create_cart(request)
        return JsonResponse({
            'count': cart.total_items if cart else 0
        })
    except Exception as e:
        logger.error(f"Error in get_cart_count: {str(e)}")
        return JsonResponse({'error': 'Unable to get cart count.'}, status=500)
    finally:
        session.close()

def get_cart_total(request):
    """Get cart total"""
    session = get_db_session()
    try:
        cart = get_or_create_cart(request)
        return JsonResponse({
            'total': cart.total if cart else 0
        })
    except Exception as e:
        logger.error(f"Error in get_cart_total: {str(e)}")
        return JsonResponse({'error': 'Unable to get cart total.'}, status=500)
    finally:
        session.close()
