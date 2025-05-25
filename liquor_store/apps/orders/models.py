from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class OrderStatus(enum.Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'

class PaymentStatus(enum.Enum):
    PENDING = 'pending'
    PAID = 'paid'
    FAILED = 'failed'
    REFUNDED = 'refunded'

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, nullable=False)
    shipping_cost = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    shipping_address_id = Column(Integer, ForeignKey('addresses.id'))
    billing_address_id = Column(Integer, ForeignKey('addresses.id'))
    tracking_number = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='orders')
    items = relationship('OrderItem', back_populates='order')
    shipping_address = relationship('Address', foreign_keys=[shipping_address_id])
    billing_address = relationship('Address', foreign_keys=[billing_address_id])

    def __repr__(self):
        return f'<Order {self.id}>'

    def calculate_totals(self):
        """Calculate order totals"""
        self.subtotal = sum(item.subtotal for item in self.items)
        self.tax = self.subtotal * 0.1  # 10% tax
        self.total = self.subtotal + self.tax + self.shipping_cost

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status.value,
            'payment_status': self.payment_status.value,
            'subtotal': self.subtotal,
            'tax': self.tax,
            'shipping_cost': self.shipping_cost,
            'total': self.total,
            'tracking_number': self.tracking_number,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'items': [item.to_dict() for item in self.items]
        }


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)  # Price at time of purchase
    subtotal = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship('Order', back_populates='items')
    product = relationship('Product')

    def __repr__(self):
        return f'<OrderItem {self.id}>'

    def calculate_subtotal(self):
        """Calculate item subtotal"""
        self.subtotal = self.price * self.quantity

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'price': self.price,
            'subtotal': self.subtotal,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'product': {
                'name': self.product.name,
                'image_url': self.product.image_url
            } if self.product else None
        }


class Cart(Base):
    __tablename__ = 'carts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    session_id = Column(String(100))  # For guest users
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship('CartItem', back_populates='cart', cascade='all, delete-orphan')
    user = relationship('User')

    def __repr__(self):
        return f'<Cart {self.id}>'

    @property
    def total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items)

    @property
    def subtotal(self):
        """Calculate cart subtotal"""
        return sum(item.subtotal for item in self.items)

    @property
    def total(self):
        """Calculate cart total with tax"""
        return self.subtotal * 1.1  # 10% tax

    def add_item(self, product, quantity=1):
        """Add item to cart"""
        existing_item = next((item for item in self.items if item.product_id == product.id), None)
        if existing_item:
            existing_item.quantity += quantity
            existing_item.calculate_subtotal()
        else:
            item = CartItem(
                cart=self,
                product=product,
                quantity=quantity,
                price=product.price
            )
            item.calculate_subtotal()
            self.items.append(item)

    def remove_item(self, product_id):
        """Remove item from cart"""
        self.items = [item for item in self.items if item.product_id != product_id]

    def update_item_quantity(self, product_id, quantity):
        """Update item quantity"""
        item = next((item for item in self.items if item.product_id == product_id), None)
        if item:
            item.quantity = quantity
            item.calculate_subtotal()

    def clear(self):
        """Clear all items from cart"""
        self.items = []

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'total_items': self.total_items,
            'subtotal': self.subtotal,
            'total': self.total,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CartItem(Base):
    __tablename__ = 'cart_items'

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Float, nullable=False)  # Price at time of adding to cart
    subtotal = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cart = relationship('Cart', back_populates='items')
    product = relationship('Product')

    def __repr__(self):
        return f'<CartItem {self.id}>'

    def calculate_subtotal(self):
        """Calculate item subtotal"""
        self.subtotal = self.price * self.quantity

    def to_dict(self):
        return {
            'id': self.id,
            'cart_id': self.cart_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'price': self.price,
            'subtotal': self.subtotal,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'product': {
                'name': self.product.name,
                'image_url': self.product.image_url
            } if self.product else None
        }
