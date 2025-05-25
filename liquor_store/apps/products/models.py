from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    products = relationship('Product', back_populates='category')

    def __repr__(self):
        return f'<Category {self.name}>'


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    image_url = Column(String(500), nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    alcohol_content = Column(Float, nullable=True)  # Percentage of alcohol
    volume = Column(Float, nullable=True)  # Volume in ml
    brand = Column(String(100), nullable=True)
    country_of_origin = Column(String(100), nullable=True)
    rating = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    category = relationship('Category', back_populates='products')

    def __repr__(self):
        return f'<Product {self.name}>'

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def formatted_price(self):
        return f"${self.price:.2f}"

    def to_dict(self):
        """Convert product to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'price': self.price,
            'formatted_price': self.formatted_price,
            'stock': self.stock,
            'image_url': self.image_url,
            'category_id': self.category_id,
            'alcohol_content': self.alcohol_content,
            'volume': self.volume,
            'brand': self.brand,
            'country_of_origin': self.country_of_origin,
            'rating': self.rating,
            'is_in_stock': self.is_in_stock,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
