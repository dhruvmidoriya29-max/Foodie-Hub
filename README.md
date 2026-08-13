# 🍔 FoodieHub — Full-Stack Food Ordering Website

A complete, polished, full-stack food ordering web application built with **Flask**, **SQLAlchemy**, and **Bootstrap 5**. Built as a college / portfolio demo project — fully functional, responsive, and populated with realistic demo data out of the box.

![Python](https://img.shields.io/badge/Python-3.9+-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-black) ![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey) ![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)

---

## 1. Project Overview

FoodieHub is a modern, original-design food-delivery platform demo. Customers can browse a menu, filter and search dishes, add items to a cart, check out with demo payment options, and track their orders on a live status timeline. Admins get a full dashboard to manage the menu, orders, and customers, complete with Chart.js analytics.

This is a **demo project** — no real payment gateway is integrated. Cash on Delivery, Demo UPI, and Demo Card are simulated payment options only.

---

## 2. Features

### Customer-facing
- Modern responsive landing page with hero, categories, popular dishes, and offers
- Full menu with 27 demo dishes across 7 categories
- Live search, category filters, price/rating sorting, veg-only filter
- Fully working shopping cart (add / increase / decrease / remove / clear) with AJAX updates
- Checkout with delivery details form and 3 demo payment methods
- Order confirmation page styled as a kitchen ticket / receipt
- Order tracking with a 4-stage visual timeline (Order Placed → Preparing → Out for Delivery → Delivered)
- Customer dashboard: profile editing, order history, total spend
- Toast notifications, empty states, form validation, loading states

### Admin-facing
- Protected admin dashboard with key metrics (customers, orders, revenue, menu items)
- Chart.js visualizations: orders & revenue trend (7 days), popular items breakdown
- Full food item CRUD (create, read, update, delete, toggle availability)
- Order management with live status updates (AJAX, no page reload)
- Customer directory with per-customer order count and total spend

### Security
- Passwords hashed with Werkzeug (`generate_password_hash` / `check_password_hash`) — never stored in plain text
- Session-based authentication via Flask-Login
- Protected routes (`@login_required`) and admin-only routes (`@admin_required`, returns HTTP 403 for non-admins)
- Server-side input validation on all forms
- Custom friendly error pages for 404 / 403 / 500 (no technical details leaked)

---

## 3. Technology Stack

| Layer          | Technology                              |
|-----------------|------------------------------------------|
| Frontend        | HTML5, CSS3, Vanilla JavaScript, Bootstrap 5, Font Awesome, Google Fonts |
| Backend         | Python 3, Flask                          |
| Database        | SQLite via SQLAlchemy ORM                |
| Authentication  | Flask-Login, Werkzeug password hashing   |
| Charts          | Chart.js                                 |

---

## 4. Folder Structure

```
foodiehub/
│
├── app.py                     # Flask app: models, routes, auth, seeding
├── requirements.txt
├── README.md
│
├── instance/
│   └── database.db            # SQLite database (auto-created & auto-seeded)
│
├── templates/
│   ├── base.html               # Shared layout: navbar, flash toasts, footer
│   ├── index.html               # Landing page
│   ├── login.html / register.html
│   ├── menu.html
│   ├── cart.html
│   ├── checkout.html
│   ├── order_confirmation.html
│   ├── orders.html / order_details.html
│   ├── profile.html
│   ├── admin_dashboard.html
│   ├── admin_food.html / admin_add_food.html / admin_edit_food.html
│   ├── admin_orders.html / admin_customers.html
│   ├── partials/
│   │   ├── food_card.html
│   │   └── admin_sidebar.html
│   └── errors/
│       ├── 404.html / 403.html / 500.html
│
└── static/
    ├── css/style.css           # Full design system (custom, not default Bootstrap look)
    └── js/script.js            # Cart AJAX, filters, admin controls, toasts
```

---

## 5. Installation Instructions

**Requirements:** Python 3.9 or newer.

```bash
# 1. Extract / clone the project, then move into the folder
cd foodiehub

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 6. Database Initialization

The database is initialized and populated **automatically** the first time you run the app — no manual setup step required.

- If `instance/database.db` does not exist, all tables are created.
- If the database is empty, it is auto-seeded with:
  - 1 admin account
  - 4 demo customer accounts
  - 27 food items across all 7 categories
  - 10 sample orders (for a populated admin dashboard on first run)

To reset the demo data at any time, simply delete `instance/database.db` and restart the app — it will be recreated and reseeded automatically.

---

## 7. Running the Application

```bash
python app.py
```

Then open your browser to:

```
http://127.0.0.1:5000
```

---

## 8. Demo Login Credentials

| Role      | Email                   | Password     |
|-----------|--------------------------|---------------|
| **Admin**    | `admin@foodiehub.com`     | `admin123`     |
| Customer  | `riya@example.com`       | `password123`  |
| Customer  | `arjun@example.com`      | `password123`  |
| Customer  | `sneha@example.com`      | `password123`  |
| Customer  | `karan@example.com`      | `password123`  |

You can also register a brand-new customer account from the **Sign Up** page at any time.

---

## 9. Using the Customer Features

1. **Browse & Search** — From the home page or the Menu page, browse dishes by category, search by name, sort by price/rating, or filter to vegetarian-only.
2. **Add to Cart** — Click the `+` button on any food card. A toast confirms the item was added, and the cart icon in the navbar updates instantly.
3. **Manage Cart** — Go to the cart page to increase/decrease quantities, remove items, or clear the cart. Totals (subtotal, delivery fee, tax, grand total) update live.
4. **Checkout** — Enter delivery details and choose a demo payment method (Cash on Delivery, Demo UPI, or Demo Card), then place the order.
5. **Track Orders** — After placing an order you're shown a receipt-style confirmation with a unique order number. Visit **My Orders** any time to see order history, or open an order to see its live delivery timeline.
6. **Profile** — Update your name, phone, and saved address from the Profile page; view your total orders and total spend.

---

## 10. Using the Admin Dashboard

1. Log in with the admin credentials above — you'll be taken straight to the **Admin Panel**.
2. **Dashboard** — View total customers, total orders, total revenue, and menu item count, plus charts for weekly orders/revenue and the most popular dishes.
3. **Manage Food** — Add new dishes, edit existing ones, delete items, or toggle availability instantly with the switch in the table.
4. **Manage Orders** — Filter orders by status and update any order's status (Order Placed → Preparing → Out for Delivery → Delivered) directly from the dropdown — updates apply instantly via AJAX.
5. **Customers** — View all registered customers along with their order count and total amount spent.

---

## Notes

- This is a demonstration project. Payment methods are simulated only — no real payment processing occurs anywhere in the codebase.
- Food images are pulled from public Unsplash URLs for demo purposes.
- The Flask development server (`python app.py`) is suitable for local demos only; for production use, deploy behind a proper WSGI server (e.g. Gunicorn) and set a strong, unique `SECRET_KEY`.
