from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from datetime import datetime, timedelta
import json
from ..products.models import Product, Category
from ..orders.models import Order, OrderStatus
from ..users.models import User
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

def is_admin(user):
    """Check if user is an admin"""
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def dashboard_view(request):
    """Main dashboard view"""
    session = get_db_session()
    try:
        # Get recent orders
        recent_orders = session.query(Order)\
            .order_by(Order.created_at.desc())\
            .limit(5)\
            .all()

        # Get low stock products
        low_stock_products = session.query(Product)\
            .filter(Product.stock < 10)\
            .limit(5)\
            .all()

        # Get basic stats
        total_orders = session.query(func.count(Order.id)).scalar()
        total_users = session.query(func.count(User.id)).scalar()
        total_products = session.query(func.count(Product.id)).scalar()

        context = {
            'recent_orders': [order.to_dict() for order in recent_orders],
            'low_stock_products': [product.to_dict() for product in low_stock_products],
            'total_orders': total_orders,
            'total_users': total_users,
            'total_products': total_products
        }

        return render(request, 'dashboard/index.html', context)

    except Exception as e:
        logger.error(f"Error in dashboard_view: {str(e)}")
        return render(request, 'dashboard/index.html', {
            'error': 'An error occurred while loading the dashboard.'
        })
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def product_list_view(request):
    """Display all products"""
    session = get_db_session()
    try:
        products = session.query(Product).all()
        categories = session.query(Category).all()

        return render(request, 'dashboard/products/list.html', {
            'products': [product.to_dict() for product in products],
            'categories': [category.to_dict() for category in categories]
        })

    except Exception as e:
        logger.error(f"Error in product_list_view: {str(e)}")
        return render(request, 'dashboard/products/list.html', {
            'error': 'An error occurred while loading products.'
        })
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def product_add_view(request):
    """Add new product"""
    if request.method == 'POST':
        session = get_db_session()
        try:
            product = Product(
                name=request.POST['name'],
                description=request.POST['description'],
                price=float(request.POST['price']),
                stock=int(request.POST['stock']),
                category_id=int(request.POST['category']),
                image_url=request.POST.get('image_url'),
                alcohol_content=float(request.POST.get('alcohol_content', 0)),
                volume=float(request.POST.get('volume', 0)),
                brand=request.POST.get('brand'),
                country_of_origin=request.POST.get('country_of_origin')
            )
            session.add(product)
            session.commit()

            return redirect('dashboard:product_list')

        except Exception as e:
            logger.error(f"Error in product_add_view: {str(e)}")
            return render(request, 'dashboard/products/add.html', {
                'error': 'An error occurred while adding the product.'
            })
        finally:
            session.close()

    session = get_db_session()
    try:
        categories = session.query(Category).all()
        return render(request, 'dashboard/products/add.html', {
            'categories': [category.to_dict() for category in categories]
        })
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def product_edit_view(request, product_id):
    """Edit existing product"""
    session = get_db_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            return redirect('dashboard:product_list')

        if request.method == 'POST':
            product.name = request.POST['name']
            product.description = request.POST['description']
            product.price = float(request.POST['price'])
            product.stock = int(request.POST['stock'])
            product.category_id = int(request.POST['category'])
            product.image_url = request.POST.get('image_url')
            product.alcohol_content = float(request.POST.get('alcohol_content', 0))
            product.volume = float(request.POST.get('volume', 0))
            product.brand = request.POST.get('brand')
            product.country_of_origin = request.POST.get('country_of_origin')

            session.commit()
            return redirect('dashboard:product_list')

        categories = session.query(Category).all()
        return render(request, 'dashboard/products/edit.html', {
            'product': product.to_dict(),
            'categories': [category.to_dict() for category in categories]
        })

    except Exception as e:
        logger.error(f"Error in product_edit_view: {str(e)}")
        return render(request, 'dashboard/products/edit.html', {
            'error': 'An error occurred while editing the product.'
        })
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def product_delete_view(request, product_id):
    """Delete product"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    session = get_db_session()
    try:
        product = session.query(Product).get(product_id)
        if product:
            session.delete(product)
            session.commit()
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Product not found.'}, status=404)

    except Exception as e:
        logger.error(f"Error in product_delete_view: {str(e)}")
        return JsonResponse({'error': 'An error occurred while deleting the product.'}, status=500)
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def order_list_view(request):
    """Display all orders"""
    session = get_db_session()
    try:
        orders = session.query(Order)\
            .order_by(Order.created_at.desc())\
            .all()

        return render(request, 'dashboard/orders/list.html', {
            'orders': [order.to_dict() for order in orders]
        })

    except Exception as e:
        logger.error(f"Error in order_list_view: {str(e)}")
        return render(request, 'dashboard/orders/list.html', {
            'error': 'An error occurred while loading orders.'
        })
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def order_detail_view(request, order_id):
    """Display order details"""
    session = get_db_session()
    try:
        order = session.query(Order).get(order_id)
        if not order:
            return redirect('dashboard:order_list')

        return render(request, 'dashboard/orders/detail.html', {
            'order': order.to_dict()
        })

    except Exception as e:
        logger.error(f"Error in order_detail_view: {str(e)}")
        return render(request, 'dashboard/orders/detail.html', {
            'error': 'An error occurred while loading the order.'
        })
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def update_order_status(request, order_id):
    """Update order status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    session = get_db_session()
    try:
        order = session.query(Order).get(order_id)
        if not order:
            return JsonResponse({'error': 'Order not found.'}, status=404)

        status = request.POST.get('status')
        if status not in [s.value for s in OrderStatus]:
            return JsonResponse({'error': 'Invalid status.'}, status=400)

        order.status = OrderStatus(status)
        session.commit()

        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Error in update_order_status: {str(e)}")
        return JsonResponse({'error': 'An error occurred while updating the order.'}, status=500)
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def user_list_view(request):
    """Display all users"""
    session = get_db_session()
    try:
        users = session.query(User).all()
        return render(request, 'dashboard/users/list.html', {
            'users': [user.to_dict() for user in users]
        })

    except Exception as e:
        logger.error(f"Error in user_list_view: {str(e)}")
        return render(request, 'dashboard/users/list.html', {
            'error': 'An error occurred while loading users.'
        })
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def user_detail_view(request, user_id):
    """Display user details"""
    session = get_db_session()
    try:
        user = session.query(User).get(user_id)
        if not user:
            return redirect('dashboard:user_list')

        # Get user's orders
        orders = session.query(Order)\
            .filter(Order.user_id == user_id)\
            .order_by(Order.created_at.desc())\
            .all()

        return render(request, 'dashboard/users/detail.html', {
            'user': user.to_dict(),
            'orders': [order.to_dict() for order in orders]
        })

    except Exception as e:
        logger.error(f"Error in user_detail_view: {str(e)}")
        return render(request, 'dashboard/users/detail.html', {
            'error': 'An error occurred while loading the user.'
        })
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def analytics_view(request):
    """Display analytics dashboard"""
    return render(request, 'dashboard/analytics.html')

@login_required
@user_passes_test(is_admin)
def inventory_view(request):
    """Display inventory management"""
    session = get_db_session()
    try:
        products = session.query(Product)\
            .order_by(Product.stock.asc())\
            .all()

        return render(request, 'dashboard/inventory.html', {
            'products': [product.to_dict() for product in products]
        })

    except Exception as e:
        logger.error(f"Error in inventory_view: {str(e)}")
        return render(request, 'dashboard/inventory.html', {
            'error': 'An error occurred while loading inventory.'
        })
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def get_dashboard_stats(request):
    """Get dashboard statistics"""
    session = get_db_session()
    try:
        # Get today's stats
        today = datetime.now().date()
        today_orders = session.query(func.count(Order.id))\
            .filter(func.date(Order.created_at) == today)\
            .scalar()
        today_sales = session.query(func.sum(Order.total))\
            .filter(func.date(Order.created_at) == today)\
            .scalar() or 0

        # Get weekly stats
        week_ago = today - timedelta(days=7)
        weekly_orders = session.query(func.count(Order.id))\
            .filter(func.date(Order.created_at) > week_ago)\
            .scalar()
        weekly_sales = session.query(func.sum(Order.total))\
            .filter(func.date(Order.created_at) > week_ago)\
            .scalar() or 0

        return JsonResponse({
            'today_orders': today_orders,
            'today_sales': float(today_sales),
            'weekly_orders': weekly_orders,
            'weekly_sales': float(weekly_sales)
        })

    except Exception as e:
        logger.error(f"Error in get_dashboard_stats: {str(e)}")
        return JsonResponse({'error': 'An error occurred while loading statistics.'}, status=500)
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def get_sales_chart_data(request):
    """Get sales chart data"""
    session = get_db_session()
    try:
        # Get last 30 days of sales
        thirty_days_ago = datetime.now() - timedelta(days=30)
        sales_data = session.query(
            func.date(Order.created_at).label('date'),
            func.sum(Order.total).label('total')
        )\
            .filter(Order.created_at >= thirty_days_ago)\
            .group_by(func.date(Order.created_at))\
            .order_by(func.date(Order.created_at))\
            .all()

        return JsonResponse({
            'dates': [str(data.date) for data in sales_data],
            'sales': [float(data.total) for data in sales_data]
        })

    except Exception as e:
        logger.error(f"Error in get_sales_chart_data: {str(e)}")
        return JsonResponse({'error': 'An error occurred while loading chart data.'}, status=500)
    finally:
        session.close()

@login_required
@user_passes_test(is_admin)
def get_inventory_alerts(request):
    """Get low stock alerts"""
    session = get_db_session()
    try:
        low_stock_products = session.query(Product)\
            .filter(Product.stock < 10)\
            .all()

        return JsonResponse({
            'alerts': [product.to_dict() for product in low_stock_products]
        })

    except Exception as e:
        logger.error(f"Error in get_inventory_alerts: {str(e)}")
        return JsonResponse({'error': 'An error occurred while loading inventory alerts.'}, status=500)
    finally:
        session.close()
