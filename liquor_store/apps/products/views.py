from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, or_
from .models import Product, Category
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

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

def product_list(request, category_slug=None):
    """View for listing products with optional category filter"""
    session = get_db_session()
    try:
        # Base query
        query = session.query(Product)

        # Apply category filter if provided
        category = None
        if category_slug:
            category = session.query(Category).filter(Category.slug == category_slug).first()
            if category:
                query = query.filter(Product.category_id == category.id)

        # Apply price filter
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price:
            query = query.filter(Product.price >= float(min_price))
        if max_price:
            query = query.filter(Product.price <= float(max_price))

        # Apply sorting
        sort_by = request.GET.get('sort')
        if sort_by == 'price_asc':
            query = query.order_by(Product.price.asc())
        elif sort_by == 'price_desc':
            query = query.order_by(Product.price.desc())
        elif sort_by == 'name':
            query = query.order_by(Product.name.asc())
        elif sort_by == 'rating':
            query = query.order_by(Product.rating.desc())
        else:
            # Default sorting
            query = query.order_by(Product.created_at.desc())

        # Get all categories for sidebar
        categories = session.query(Category).all()

        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(query.all(), 12)  # 12 products per page
        products = paginator.get_page(page)

        context = {
            'category': category,
            'categories': categories,
            'products': products,
            'min_price': min_price,
            'max_price': max_price,
            'sort_by': sort_by,
        }

        return render(request, 'products/product_list.html', context)

    except Exception as e:
        logger.error(f"Error in product_list view: {str(e)}")
        return render(request, 'products/product_list.html', {
            'error_message': 'An error occurred while loading products.'
        })
    finally:
        session.close()

def product_detail(request, product_id):
    """View for showing product details"""
    session = get_db_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            return render(request, 'products/product_detail.html', {
                'error_message': 'Product not found.'
            })

        # Get related products from same category
        related_products = session.query(Product)\
            .filter(Product.category_id == product.category_id)\
            .filter(Product.id != product.id)\
            .limit(4)\
            .all()

        context = {
            'product': product,
            'related_products': related_products,
        }

        return render(request, 'products/product_detail.html', context)

    except Exception as e:
        logger.error(f"Error in product_detail view: {str(e)}")
        return render(request, 'products/product_detail.html', {
            'error_message': 'An error occurred while loading the product.'
        })
    finally:
        session.close()

def filter_products(request):
    """API endpoint for filtering products"""
    session = get_db_session()
    try:
        query = session.query(Product)

        # Apply filters from request
        category_id = request.GET.get('category')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        sort_by = request.GET.get('sort')

        if category_id:
            query = query.filter(Product.category_id == int(category_id))
        if min_price:
            query = query.filter(Product.price >= float(min_price))
        if max_price:
            query = query.filter(Product.price <= float(max_price))

        # Apply sorting
        if sort_by == 'price_asc':
            query = query.order_by(Product.price.asc())
        elif sort_by == 'price_desc':
            query = query.order_by(Product.price.desc())
        elif sort_by == 'name':
            query = query.order_by(Product.name.asc())
        elif sort_by == 'rating':
            query = query.order_by(Product.rating.desc())

        # Convert products to dict for JSON response
        products = [product.to_dict() for product in query.all()]

        return JsonResponse({
            'success': True,
            'products': products
        })

    except Exception as e:
        logger.error(f"Error in filter_products view: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while filtering products.'
        })
    finally:
        session.close()

def search_products(request):
    """API endpoint for searching products"""
    session = get_db_session()
    try:
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Search query is required.'
            })

        # Search in product name, description, and brand
        products = session.query(Product).filter(
            or_(
                Product.name.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%'),
                Product.brand.ilike(f'%{query}%')
            )
        ).limit(10).all()

        results = [product.to_dict() for product in products]

        return JsonResponse({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"Error in search_products view: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while searching products.'
        })
    finally:
        session.close()
