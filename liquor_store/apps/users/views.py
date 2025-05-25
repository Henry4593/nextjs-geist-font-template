from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import uuid
from .models import User, Address, PasswordReset
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

def login_view(request):
    """Handle user login"""
    if request.method == 'POST':
        session = get_db_session()
        try:
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            user = session.query(User).filter(User.email == email).first()
            
            if user and user.check_password(password):
                if not user.is_active:
                    return render(request, 'users/login.html', {
                        'error': 'This account has been deactivated.'
                    })
                
                # Update last login
                user.last_login = datetime.utcnow()
                session.commit()
                
                # Log the user in
                login(request, user)
                
                next_url = request.GET.get('next', '/')
                return redirect(next_url)
            else:
                return render(request, 'users/login.html', {
                    'error': 'Invalid email or password.'
                })
                
        except Exception as e:
            logger.error(f"Error in login_view: {str(e)}")
            return render(request, 'users/login.html', {
                'error': 'An error occurred during login.'
            })
        finally:
            session.close()
    
    return render(request, 'users/login.html')

def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('/')

def register_view(request):
    """Handle user registration"""
    if request.method == 'POST':
        session = get_db_session()
        try:
            email = request.POST.get('email')
            username = request.POST.get('username')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validation
            if password != confirm_password:
                return render(request, 'users/register.html', {
                    'error': 'Passwords do not match.'
                })
            
            # Check if email or username already exists
            if session.query(User).filter(User.email == email).first():
                return render(request, 'users/register.html', {
                    'error': 'Email already registered.'
                })
            
            if session.query(User).filter(User.username == username).first():
                return render(request, 'users/register.html', {
                    'error': 'Username already taken.'
                })
            
            # Create new user
            user = User(
                email=email,
                username=username
            )
            user.set_password(password)
            
            session.add(user)
            session.commit()
            
            # Log the user in
            login(request, user)
            
            return redirect('/')
            
        except Exception as e:
            logger.error(f"Error in register_view: {str(e)}")
            return render(request, 'users/register.html', {
                'error': 'An error occurred during registration.'
            })
        finally:
            session.close()
    
    return render(request, 'users/register.html')

@login_required
def account_view(request):
    """Display user account dashboard"""
    session = get_db_session()
    try:
        user = session.query(User).get(request.user.id)
        if not user:
            return redirect('users:login')
        
        # Get user's addresses
        addresses = session.query(Address).filter(Address.user_id == user.id).all()
        
        # Get recent orders (from orders app)
        from liquor_store.apps.orders.models import Order
        recent_orders = session.query(Order)\
            .filter(Order.user_id == user.id)\
            .order_by(Order.created_at.desc())\
            .limit(5)\
            .all()
        
        context = {
            'user': user,
            'addresses': addresses,
            'recent_orders': recent_orders,
        }
        
        return render(request, 'users/account.html', context)
        
    except Exception as e:
        logger.error(f"Error in account_view: {str(e)}")
        return render(request, 'users/account.html', {
            'error': 'An error occurred while loading your account.'
        })
    finally:
        session.close()

@login_required
def account_settings_view(request):
    """Handle user account settings updates"""
    session = get_db_session()
    try:
        user = session.query(User).get(request.user.id)
        if not user:
            return redirect('users:login')
        
        if request.method == 'POST':
            # Update user information
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            
            # Handle password change
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if current_password and new_password:
                if not user.check_password(current_password):
                    return render(request, 'users/account_settings.html', {
                        'user': user,
                        'error': 'Current password is incorrect.'
                    })
                
                if new_password != confirm_password:
                    return render(request, 'users/account_settings.html', {
                        'user': user,
                        'error': 'New passwords do not match.'
                    })
                
                user.set_password(new_password)
            
            session.commit()
            
            return render(request, 'users/account_settings.html', {
                'user': user,
                'success': 'Account settings updated successfully.'
            })
        
        return render(request, 'users/account_settings.html', {'user': user})
        
    except Exception as e:
        logger.error(f"Error in account_settings_view: {str(e)}")
        return render(request, 'users/account_settings.html', {
            'error': 'An error occurred while updating your settings.'
        })
    finally:
        session.close()

@login_required
def order_history_view(request):
    """Display user's order history"""
    session = get_db_session()
    try:
        # Get all orders for the user
        from liquor_store.apps.orders.models import Order
        orders = session.query(Order)\
            .filter(Order.user_id == request.user.id)\
            .order_by(Order.created_at.desc())\
            .all()
        
        return render(request, 'users/order_history.html', {'orders': orders})
        
    except Exception as e:
        logger.error(f"Error in order_history_view: {str(e)}")
        return render(request, 'users/order_history.html', {
            'error': 'An error occurred while loading your order history.'
        })
    finally:
        session.close()

def password_reset_view(request):
    """Handle password reset request"""
    if request.method == 'POST':
        session = get_db_session()
        try:
            email = request.POST.get('email')
            user = session.query(User).filter(User.email == email).first()
            
            if user:
                # Generate reset token
                token = str(uuid.uuid4())
                expires_at = datetime.utcnow() + timedelta(hours=24)
                
                reset = PasswordReset(
                    user_id=user.id,
                    token=token,
                    expires_at=expires_at
                )
                
                session.add(reset)
                session.commit()
                
                # Here you would typically send an email with the reset link
                # For now, we'll just show a success message
                return render(request, 'users/password_reset.html', {
                    'success': 'Password reset instructions have been sent to your email.'
                })
            
            return render(request, 'users/password_reset.html', {
                'error': 'No account found with that email address.'
            })
            
        except Exception as e:
            logger.error(f"Error in password_reset_view: {str(e)}")
            return render(request, 'users/password_reset.html', {
                'error': 'An error occurred while processing your request.'
            })
        finally:
            session.close()
    
    return render(request, 'users/password_reset.html')

def password_reset_confirm_view(request, uidb64, token):
    """Handle password reset confirmation"""
    session = get_db_session()
    try:
        reset = session.query(PasswordReset)\
            .filter(PasswordReset.token == token)\
            .filter(PasswordReset.used == False)\
            .filter(PasswordReset.expires_at > datetime.utcnow())\
            .first()
        
        if not reset:
            return render(request, 'users/password_reset_confirm.html', {
                'error': 'Invalid or expired password reset link.'
            })
        
        if request.method == 'POST':
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            if password != confirm_password:
                return render(request, 'users/password_reset_confirm.html', {
                    'error': 'Passwords do not match.'
                })
            
            user = session.query(User).get(reset.user_id)
            user.set_password(password)
            reset.mark_as_used()
            
            session.commit()
            
            return redirect('users:login')
        
        return render(request, 'users/password_reset_confirm.html')
        
    except Exception as e:
        logger.error(f"Error in password_reset_confirm_view: {str(e)}")
        return render(request, 'users/password_reset_confirm.html', {
            'error': 'An error occurred while resetting your password.'
        })
    finally:
        session.close()
