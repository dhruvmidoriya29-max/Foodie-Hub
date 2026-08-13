"""
FoodieHub - Full-stack Food Ordering Website
Flask + SQLAlchemy + Flask-Login demo application.
"""

import os
import random
import string
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, redirect, url_for, flash, request,
    jsonify, abort, session
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

# --------------------------------------------------------------------------
# App configuration
# --------------------------------------------------------------------------
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'foodiehub-demo-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

DELIVERY_FEE = 40.0
TAX_RATE = 0.05  # 5%


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # customer / admin
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='customer', lazy=True, cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == 'admin'


class FoodItem(db.Model):
    __tablename__ = 'food_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(500))
    rating = db.Column(db.Float, default=4.0)
    is_available = db.Column(db.Boolean, default=True)
    is_veg = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'image_url': self.image_url,
            'rating': self.rating,
            'is_available': self.is_available,
            'is_veg': self.is_veg,
        }


class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('food_items.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    food = db.relationship('FoodItem')

    @property
    def subtotal(self):
        return round(self.food.price * self.quantity, 2)


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(20), nullable=False)

    subtotal = db.Column(db.Float, nullable=False)
    delivery_fee = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)

    payment_method = db.Column(db.String(30), nullable=False)  # cod / upi / card
    status = db.Column(db.String(30), nullable=False, default='Order Placed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    STATUS_STEPS = ['Order Placed', 'Preparing', 'Out for Delivery', 'Delivered']

    @property
    def status_index(self):
        try:
            return self.STATUS_STEPS.index(self.status)
        except ValueError:
            return 0


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('food_items.id'), nullable=True)

    food_name = db.Column(db.String(150), nullable=False)
    food_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    food = db.relationship('FoodItem')

    @property
    def subtotal(self):
        return round(self.food_price * self.quantity, 2)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON 401 for fetch/AJAX calls, otherwise redirect to login."""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Please log in first.'}), 401
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('login', next=request.path))


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.path))
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def generate_order_number():
    return 'FH' + ''.join(random.choices(string.digits, k=8))


def get_cart_summary(cart_items):
    subtotal = round(sum(item.subtotal for item in cart_items), 2)
    delivery_fee = DELIVERY_FEE if subtotal > 0 else 0.0
    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + delivery_fee + tax, 2)
    return {
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'tax': tax,
        'total': total,
    }


@app.context_processor
def inject_globals():
    cart_count = 0
    if current_user.is_authenticated:
        cart_count = sum(ci.quantity for ci in CartItem.query.filter_by(user_id=current_user.id).all())
    return dict(cart_count=cart_count, current_year=datetime.utcnow().year)


# --------------------------------------------------------------------------
# Public routes
# --------------------------------------------------------------------------
@app.route('/')
def index():
    popular = FoodItem.query.filter_by(is_available=True).order_by(FoodItem.rating.desc()).limit(8).all()
    categories = db.session.query(FoodItem.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('index.html', popular=popular, categories=categories)


@app.route('/menu')
def menu():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', '')
    veg_only = request.args.get('veg_only', '')

    query = FoodItem.query

    if category and category != 'all':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(FoodItem.name.ilike(f'%{search}%'))
    if veg_only == '1':
        query = query.filter_by(is_veg=True)

    if sort == 'price_low':
        query = query.order_by(FoodItem.price.asc())
    elif sort == 'price_high':
        query = query.order_by(FoodItem.price.desc())
    elif sort == 'rating':
        query = query.order_by(FoodItem.rating.desc())
    else:
        query = query.order_by(FoodItem.id.asc())

    items = query.all()
    categories = [c[0] for c in db.session.query(FoodItem.category).distinct().all()]

    return render_template(
        'menu.html', items=items, categories=categories,
        selected_category=category, search=search, sort=sort, veg_only=veg_only
    )


@app.route('/api/menu')
def api_menu():
    """JSON endpoint used for smooth client-side filtering."""
    items = FoodItem.query.all()
    return jsonify([i.to_dict() for i in items])


# --------------------------------------------------------------------------
# Auth routes
# --------------------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []
        if not name or len(name) < 2:
            errors.append('Please enter your full name.')
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        if not phone or len(phone) < 10:
            errors.append('Please enter a valid 10-digit phone number.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html', name=name, email=email, phone=phone)

        user = User(name=name, email=email, phone=phone, role='customer')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.name.split()[0]}!', 'success')
            next_page = request.args.get('next')
            if user.is_admin and not next_page:
                return redirect(url_for('admin_dashboard'))
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# --------------------------------------------------------------------------
# Cart routes
# --------------------------------------------------------------------------
@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    summary = get_cart_summary(cart_items)
    return render_template('cart.html', cart_items=cart_items, summary=summary)


@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    food_id = request.form.get('food_id', type=int)
    quantity = request.form.get('quantity', default=1, type=int)
    food = FoodItem.query.get_or_404(food_id)

    if not food.is_available:
        return jsonify({'success': False, 'message': 'This item is currently unavailable.'}), 400

    existing = CartItem.query.filter_by(user_id=current_user.id, food_id=food_id).first()
    if existing:
        existing.quantity += max(quantity, 1)
    else:
        existing = CartItem(user_id=current_user.id, food_id=food_id, quantity=max(quantity, 1))
        db.session.add(existing)
    db.session.commit()

    cart_count = sum(ci.quantity for ci in CartItem.query.filter_by(user_id=current_user.id).all())
    return jsonify({'success': True, 'message': f'{food.name} added to cart.', 'cart_count': cart_count})


@app.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    item_id = request.form.get('item_id', type=int)
    action = request.form.get('action')

    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()

    if action == 'increase':
        item.quantity += 1
    elif action == 'decrease':
        item.quantity -= 1
        if item.quantity <= 0:
            db.session.delete(item)
    elif action == 'remove':
        db.session.delete(item)

    db.session.commit()

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    summary = get_cart_summary(cart_items)
    cart_count = sum(ci.quantity for ci in cart_items)

    return jsonify({
        'success': True,
        'cart_count': cart_count,
        'summary': summary,
        'item_subtotal': item.subtotal if action != 'remove' and item.quantity > 0 else 0,
        'removed': action == 'remove' or item.quantity <= 0,
    })


@app.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Cart cleared.', 'info')
    return redirect(url_for('cart'))


# --------------------------------------------------------------------------
# Checkout / Orders
# --------------------------------------------------------------------------
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty. Add some delicious food first!', 'warning')
        return redirect(url_for('menu'))

    summary = get_cart_summary(cart_items)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        pincode = request.form.get('pincode', '').strip()
        payment_method = request.form.get('payment_method', 'cod')

        errors = []
        if not name:
            errors.append('Please enter the recipient name.')
        if not phone or len(phone) < 10:
            errors.append('Please enter a valid phone number.')
        if not address:
            errors.append('Please enter a delivery address.')
        if not city:
            errors.append('Please enter a city.')
        if not pincode or len(pincode) < 4:
            errors.append('Please enter a valid pincode.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('checkout.html', cart_items=cart_items, summary=summary,
                                    name=name, phone=phone, address=address, city=city, pincode=pincode)

        order = Order(
            order_number=generate_order_number(),
            user_id=current_user.id,
            customer_name=name,
            phone=phone,
            address=address,
            city=city,
            pincode=pincode,
            subtotal=summary['subtotal'],
            delivery_fee=summary['delivery_fee'],
            tax=summary['tax'],
            total=summary['total'],
            payment_method=payment_method,
            status='Order Placed',
        )
        db.session.add(order)
        db.session.flush()  # get order.id before commit

        for ci in cart_items:
            db.session.add(OrderItem(
                order_id=order.id,
                food_id=ci.food_id,
                food_name=ci.food.name,
                food_price=ci.food.price,
                quantity=ci.quantity,
            ))

        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        return redirect(url_for('order_confirmation', order_number=order.order_number))

    return render_template('checkout.html', cart_items=cart_items, summary=summary,
                            name=current_user.name, phone=current_user.phone or '',
                            address=current_user.address or '', city=current_user.city or '',
                            pincode=current_user.pincode or '')


@app.route('/order-confirmation/<order_number>')
@login_required
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    return render_template('order_confirmation.html', order=order)


@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)


@app.route('/orders/<order_number>')
@login_required
def order_details(order_number):
    if current_user.is_admin:
        order = Order.query.filter_by(order_number=order_number).first_or_404()
    else:
        order = Order.query.filter_by(order_number=order_number, user_id=current_user.id).first_or_404()
    return render_template('order_details.html', order=order)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name).strip()
        current_user.phone = request.form.get('phone', current_user.phone).strip()
        current_user.address = request.form.get('address', '').strip()
        current_user.city = request.form.get('city', '').strip()
        current_user.pincode = request.form.get('pincode', '').strip()
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))

    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    total_spent = round(sum(o.total for o in user_orders), 2)
    return render_template('profile.html', orders=user_orders, total_spent=total_spent)


# --------------------------------------------------------------------------
# Admin routes
# --------------------------------------------------------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    total_users = User.query.filter_by(role='customer').count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(func.sum(Order.total)).scalar() or 0
    total_food_items = FoodItem.query.count()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(6).all()

    # Orders over last 7 days
    today = datetime.utcnow().date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    orders_by_day = []
    revenue_by_day = []
    for d in days:
        day_orders = Order.query.filter(func.date(Order.created_at) == d.isoformat()).all()
        orders_by_day.append(len(day_orders))
        revenue_by_day.append(round(sum(o.total for o in day_orders), 2))

    # Popular items (by quantity ordered)
    popular_query = (
        db.session.query(OrderItem.food_name, func.sum(OrderItem.quantity).label('qty'))
        .group_by(OrderItem.food_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )
    popular_labels = [p[0] for p in popular_query]
    popular_values = [int(p[1]) for p in popular_query]

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_food_items=total_food_items,
        recent_orders=recent_orders,
        day_labels=[d.strftime('%b %d') for d in days],
        orders_by_day=orders_by_day,
        revenue_by_day=revenue_by_day,
        popular_labels=popular_labels,
        popular_values=popular_values,
    )


@app.route('/admin/food')
@admin_required
def admin_food():
    items = FoodItem.query.order_by(FoodItem.id.desc()).all()
    return render_template('admin_food.html', items=items)


@app.route('/admin/food/add', methods=['GET', 'POST'])
@admin_required
def admin_add_food():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        category = request.form.get('category', '').strip()
        image_url = request.form.get('image_url', '').strip()
        rating = request.form.get('rating', default=4.0, type=float)
        is_veg = bool(request.form.get('is_veg'))
        is_available = bool(request.form.get('is_available'))

        errors = []
        if not name:
            errors.append('Food name is required.')
        if not price or price <= 0:
            errors.append('Please enter a valid price.')
        if not category:
            errors.append('Please select a category.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin_add_food.html', form=request.form)

        item = FoodItem(
            name=name, description=description, price=price, category=category,
            image_url=image_url or 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600',
            rating=rating, is_veg=is_veg, is_available=is_available,
        )
        db.session.add(item)
        db.session.commit()
        flash(f'"{name}" has been added to the menu.', 'success')
        return redirect(url_for('admin_food'))

    return render_template('admin_add_food.html', form={})


@app.route('/admin/food/edit/<int:food_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_food(food_id):
    item = FoodItem.query.get_or_404(food_id)

    if request.method == 'POST':
        item.name = request.form.get('name', '').strip()
        item.description = request.form.get('description', '').strip()
        item.price = request.form.get('price', type=float)
        item.category = request.form.get('category', '').strip()
        item.image_url = request.form.get('image_url', '').strip()
        item.rating = request.form.get('rating', type=float)
        item.is_veg = bool(request.form.get('is_veg'))
        item.is_available = bool(request.form.get('is_available'))

        db.session.commit()
        flash(f'"{item.name}" has been updated.', 'success')
        return redirect(url_for('admin_food'))

    return render_template('admin_edit_food.html', item=item)


@app.route('/admin/food/delete/<int:food_id>', methods=['POST'])
@admin_required
def admin_delete_food(food_id):
    item = FoodItem.query.get_or_404(food_id)
    name = item.name
    db.session.delete(item)
    db.session.commit()
    flash(f'"{name}" has been removed from the menu.', 'info')
    return redirect(url_for('admin_food'))


@app.route('/admin/food/toggle/<int:food_id>', methods=['POST'])
@admin_required
def admin_toggle_food(food_id):
    item = FoodItem.query.get_or_404(food_id)
    item.is_available = not item.is_available
    db.session.commit()
    return jsonify({'success': True, 'is_available': item.is_available})


@app.route('/admin/orders')
@admin_required
def admin_orders():
    status_filter = request.args.get('status', 'all')
    query = Order.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    all_orders = query.order_by(Order.created_at.desc()).all()
    return render_template('admin_orders.html', orders=all_orders, status_filter=status_filter,
                            statuses=Order.STATUS_STEPS)


@app.route('/admin/orders/update-status', methods=['POST'])
@admin_required
def admin_update_order_status():
    order_id = request.form.get('order_id', type=int)
    new_status = request.form.get('status')

    order = Order.query.get_or_404(order_id)
    if new_status in Order.STATUS_STEPS:
        order.status = new_status
        db.session.commit()
        return jsonify({'success': True, 'status': order.status})

    return jsonify({'success': False, 'message': 'Invalid status.'}), 400


@app.route('/admin/customers')
@admin_required
def admin_customers():
    customers = User.query.filter_by(role='customer').order_by(User.created_at.desc()).all()
    customer_data = []
    for c in customers:
        order_count = Order.query.filter_by(user_id=c.id).count()
        total_spent = db.session.query(func.sum(Order.total)).filter_by(user_id=c.id).scalar() or 0
        customer_data.append({'user': c, 'order_count': order_count, 'total_spent': round(total_spent, 2)})
    return render_template('admin_customers.html', customer_data=customer_data)


# --------------------------------------------------------------------------
# Error handlers
# --------------------------------------------------------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# --------------------------------------------------------------------------
# Database initialization & demo data seeding
# --------------------------------------------------------------------------
def seed_demo_data():
    """Populate the database with demo data if it is empty."""

    if User.query.filter_by(role='admin').first() is None:
        admin = User(
            name='Admin User',
            email='admin@foodiehub.com',
            phone='9999900000',
            role='admin',
            address='FoodieHub HQ, MG Road',
            city='Bengaluru',
            pincode='560001',
        )
        admin.set_password('admin123')
        db.session.add(admin)

    if User.query.filter_by(role='customer').count() == 0:
        demo_customers = [
            ('Riya Sharma', 'riya@example.com', '9876500001', 'Koramangala 5th Block', 'Bengaluru', '560095'),
            ('Arjun Mehta', 'arjun@example.com', '9876500002', 'Baner Road', 'Pune', '411045'),
            ('Sneha Iyer', 'sneha@example.com', '9876500003', 'Anna Nagar', 'Chennai', '600040'),
            ('Karan Verma', 'karan@example.com', '9876500004', 'Sector 18', 'Noida', '201301'),
        ]
        for name, email, phone, address, city, pincode in demo_customers:
            u = User(name=name, email=email, phone=phone, role='customer',
                     address=address, city=city, pincode=pincode)
            u.set_password('password123')
            db.session.add(u)

    db.session.commit()

    if FoodItem.query.count() == 0:
        demo_food = [
            # Pizza
            ('Margherita Pizza', 'Classic delight with 100% real mozzarella cheese and fresh basil.', 249, 'Pizza', 'https://images.unsplash.com/photo-1604068549290-dea0e4a305ca?w=600', 4.5, True, True),
            ('Farmhouse Pizza', 'Loaded with onion, capsicum, tomato, grilled mushroom and corn.', 329, 'Pizza', 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600', 4.4, True, True),
            ('Pepperoni Pizza', 'A timeless favourite topped with double pepperoni and cheese.', 379, 'Pizza', 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=600', 4.7, True, False),
            ('Peppy Paneer Pizza', 'Spicy triple topping of paneer, capsicum and red paprika.', 349, 'Pizza', 'https://images.unsplash.com/photo-1594007654729-407eedc4be65?w=600', 4.3, True, True),
            # Burger
            ('Classic Veg Burger', 'Crispy veg patty, fresh lettuce, tomato and signature sauce.', 129, 'Burger', 'https://images.unsplash.com/photo-1550317138-10000687a72b?w=600', 4.2, True, True),
            ('Cheese Chicken Burger', 'Grilled chicken patty topped with melted cheddar cheese.', 179, 'Burger', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600', 4.6, True, False),
            ('Double Patty Beef Burger', 'Two juicy beef patties stacked with cheese and pickles.', 229, 'Burger', 'https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=600', 4.5, True, False),
            ('Spicy Paneer Burger', 'Crunchy paneer tikki with spicy mayo and fresh veggies.', 149, 'Burger', 'https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=600', 4.1, True, True),
            # Indian
            ('Butter Chicken', 'Tender chicken cooked in rich tomato and butter gravy.', 289, 'Indian', 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=600', 4.8, True, False),
            ('Paneer Butter Masala', 'Cottage cheese cubes in a creamy tomato-cashew gravy.', 259, 'Indian', 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600', 4.6, True, True),
            ('Dal Makhani', 'Slow-cooked black lentils finished with cream and butter.', 199, 'Indian', 'https://images.unsplash.com/photo-1626132647523-66f5bf380027?w=600', 4.4, True, True),
            ('Chicken Biryani', 'Fragrant basmati rice layered with spiced chicken and saffron.', 269, 'Indian', 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600', 4.9, True, False),
            # Chinese
            ('Veg Hakka Noodles', 'Wok-tossed noodles with fresh julienned vegetables.', 179, 'Chinese', 'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600', 4.2, True, True),
            ('Chilli Chicken', 'Indo-Chinese classic with crispy chicken in spicy sauce.', 229, 'Chinese', 'https://images.unsplash.com/photo-1626200419199-391ae4be7a41?w=600', 4.5, True, False),
            ('Veg Manchurian', 'Deep fried vegetable balls tossed in tangy Manchurian sauce.', 189, 'Chinese', 'https://images.unsplash.com/photo-1541014741259-de529411b96a?w=600', 4.3, True, True),
            ('Schezwan Fried Rice', 'Spicy schezwan style fried rice loaded with vegetables.', 199, 'Chinese', 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600', 4.1, True, True),
            # South Indian
            ('Masala Dosa', 'Crispy rice crepe filled with spiced potato masala.', 129, 'South Indian', 'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=600', 4.6, True, True),
            ('Idli Sambar', 'Steamed rice cakes served with sambar and coconut chutney.', 99, 'South Indian', 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600', 4.4, True, True),
            ('Medu Vada', 'Crispy golden lentil doughnuts served with chutney.', 109, 'South Indian', 'https://images.unsplash.com/photo-1630383249896-24404d599e60?w=600', 4.2, True, True),
            ('Uttapam', 'Thick savoury pancake topped with onion and tomato.', 139, 'South Indian', 'https://images.unsplash.com/photo-1630383249896-24404d599e60?w=600', 4.0, True, True),
            # Desserts
            ('Chocolate Brownie', 'Fudgy chocolate brownie served warm with chocolate sauce.', 149, 'Desserts', 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=600', 4.7, True, True),
            ('Gulab Jamun', 'Soft milk dumplings soaked in rose flavoured sugar syrup.', 99, 'Desserts', 'https://images.unsplash.com/photo-1601303516361-f2b0f0f7e73e?w=600', 4.5, True, True),
            ('New York Cheesecake', 'Creamy baked cheesecake with a buttery biscuit base.', 199, 'Desserts', 'https://images.unsplash.com/photo-1567327613485-fbc7bf196333?w=600', 4.6, True, True),
            # Beverages
            ('Masala Chai', 'Freshly brewed Indian spiced tea with milk.', 49, 'Beverages', 'https://images.unsplash.com/photo-1571934811356-5cc061b6821f?w=600', 4.3, True, True),
            ('Cold Coffee', 'Chilled coffee blended with milk and ice cream.', 99, 'Beverages', 'https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=600', 4.4, True, True),
            ('Fresh Lime Soda', 'Refreshing lime soda, sweet or salted, over crushed ice.', 69, 'Beverages', 'https://images.unsplash.com/photo-1621263764928-df1444c5e859?w=600', 4.1, True, True),
            ('Mango Lassi', 'Thick and creamy yoghurt shake blended with fresh mango.', 89, 'Beverages', 'https://images.unsplash.com/photo-1626200419199-391ae4be7a41?w=600', 4.6, True, True),
        ]

        for name, desc, price, cat, img, rating, avail, veg in demo_food:
            db.session.add(FoodItem(
                name=name, description=desc, price=price, category=cat,
                image_url=img, rating=rating, is_available=avail, is_veg=veg,
            ))
        db.session.commit()

    if Order.query.count() == 0:
        customers = User.query.filter_by(role='customer').all()
        foods = FoodItem.query.all()
        statuses = Order.STATUS_STEPS
        payment_methods = ['cod', 'upi', 'card']

        if customers and foods:
            for i in range(10):
                cust = random.choice(customers)
                chosen_items = random.sample(foods, k=random.randint(1, 4))
                subtotal = 0
                order = Order(
                    order_number=generate_order_number(),
                    user_id=cust.id,
                    customer_name=cust.name,
                    phone=cust.phone,
                    address=cust.address or 'Demo Address',
                    city=cust.city or 'Demo City',
                    pincode=cust.pincode or '000000',
                    subtotal=0, delivery_fee=DELIVERY_FEE, tax=0, total=0,
                    payment_method=random.choice(payment_methods),
                    status=random.choice(statuses),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 6),
                                                              hours=random.randint(0, 23)),
                )
                db.session.add(order)
                db.session.flush()

                for f in chosen_items:
                    qty = random.randint(1, 3)
                    subtotal += f.price * qty
                    db.session.add(OrderItem(
                        order_id=order.id, food_id=f.id, food_name=f.name,
                        food_price=f.price, quantity=qty,
                    ))

                tax = round(subtotal * TAX_RATE, 2)
                order.subtotal = round(subtotal, 2)
                order.tax = tax
                order.total = round(subtotal + DELIVERY_FEE + tax, 2)

            db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        seed_demo_data()


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
