# seed_db.py
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    
    customer_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    region = Column(String(50))  # Categorical column (e.g. 'North America', 'Europe')

class Product(Base):
    __tablename__ = 'products'
    
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    category = Column(String(50))
    price = Column(Float, nullable=False)

class Order(Base):
    __tablename__ = 'orders'
    
    order_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.customer_id'))
    product_id = Column(Integer, ForeignKey('products.product_id'))
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)

def init_db():
    engine = create_engine('sqlite:///./test_db.db')
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Add dummy records
    c1 = Customer(name="Alice Smith", email="alice@example.com", region="North America")
    c2 = Customer(name="Bob Jones", email="bob@example.com", region="Europe")
    
    p1 = Product(product_name="Laptop", category="Electronics", price=1200.0)
    p2 = Product(product_name="Headphones", category="Electronics", price=150.0)
    
    o1 = Order(customer_id=1, product_id=1, quantity=1, total_amount=1200.0)
    o2 = Order(customer_id=2, product_id=2, quantity=2, total_amount=300.0)
    
    session.add_all([c1, c2, p1, p2, o1, o2])
    session.commit()
    session.close()
    print("Database seeded successfully with sample tables and rows!")

if __name__ == "__main__":
    init_db()