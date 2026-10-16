# NutriForge – Fitness Supplement E-Commerce Website

A BCA final-year project: an online store for fitness supplements built with **Django + MySQL + Tailwind CSS**.

## 1. Project overview
NutriForge lets customers browse supplements, search and filter, add to cart or wishlist, place orders (Cash on Delivery or simulated payment), track orders, review products and get rule-based product recommendations. Administrators manage everything from a customised Django admin with a statistics dashboard.

## 2. Features
- Home page: hero, categories, best sellers, new arrivals, popular, special offers, why-choose-us, reviews, newsletter
- Products: search (name / brand / category / type), filters (category, brand, price, rating, diet, type), sorting, pagination
- Product details: image gallery, flavours, nutrition table, ingredients, quantity selector, reviews, related products
- Cart (quantity update, remove, coupon), checkout (saved/new address, delivery charge, payment simulation)
- Accounts: register, login, logout, password validation, forgot password, profile, saved addresses
- Orders: history, details, tracking (Placed → Confirmed → Packed → Shipped → Delivered), cancel with stock restore
- Wishlist (add, remove, move to cart), reviews with rating, coupons
- "Find My Supplement": rule-based recommendations (goal, budget, level, diet, type)
- Admin: products, stock, categories, brands, images, customers, orders (status update), coupons, reviews, dashboard stats
- Toasts, AJAX add-to-cart/wishlist, live search suggestions, confirmation dialogs, client-side validation

## 3. Technology stack
HTML5, CSS3, JavaScript (vanilla), Tailwind CSS (CDN), Python 3.10+, Django 5, MySQL 8. No React/Node/other frameworks.

## 4. System requirements
Python 3.10+, MySQL 8 (or MariaDB 10.5+), pip, any modern browser, internet connection for the Tailwind CDN.

## 5. Installation
```bash
cd nutriforge_project
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```
If `mysqlclient` fails on Windows: `pip install pymysql` instead (the project switches to it automatically).

## 6. MySQL configuration
```sql
CREATE DATABASE nutriforge_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Open `nutriforge/settings.py` and set `MYSQL_PASSWORD` (or set the environment variables `MYSQL_DB`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`).
Want to try it without MySQL first? Set `NUTRIFORGE_DB=sqlite` (Windows: `set NUTRIFORGE_DB=sqlite`).

## 7–12. Django setup and running
```bash
python manage.py migrate                 # create tables (migration files are included)
python manage.py load_sample_data        # 29 sample products, coupons, demo users, reviews
python manage.py createsuperuser         # admin login
python manage.py runserver               # http://127.0.0.1:8000/
```
If you change a model: `python manage.py makemigrations` then `python manage.py migrate`.

- Store: http://127.0.0.1:8000/  ·  Admin: http://127.0.0.1:8000/admin/
- Demo customers: `demo1`, `demo2`, `demo3` – password `Demo@12345`
- Coupons: `WELCOME10` (10%, min ₹499), `FLAT200` (₹200 off, min ₹1,999)
- Password-reset emails are printed in the terminal window running the server.

## 8. Database structure
| Table (model) | Key relationships |
|---|---|
| User (accounts) | extends Django `AbstractUser` + phone |
| Address | FK → User (one user, many addresses) |
| Category, Brand, Goal | independent lookup tables |
| Product | FK → Category, FK → Brand, M2M ↔ Goal |
| ProductImage | FK → Product (gallery) |
| ProductVariant | FK → Product (flavours) |
| Cart | OneToOne → User |
| CartItem | FK → Cart, FK → Product, FK → ProductVariant |
| Wishlist | FK → User, FK → Product (unique pair) |
| Review | FK → Product, FK → User (unique pair) |
| Coupon | independent |
| Order | FK → User, FK → Coupon (address copied in as a snapshot) |
| OrderItem | FK → Order, FK → Product (name/price copied in) |
| Payment | OneToOne → Order |
| NewsletterSubscriber, ContactMessage | independent (core app) |

Why copy address/price into orders? So changing a product price or address later never alters old orders – a common viva question.

## 9. Folder structure
```
nutriforge_project/
├── manage.py, requirements.txt, README.md
├── nutriforge/        settings.py, urls.py
├── accounts/          User, Address, register/login/profile/addresses, password reset
├── products/          Category, Brand, Product..., list/detail/search, load_sample_data command
├── cart/              Cart, CartItem, coupons on cart
├── orders/            Order, OrderItem, Payment, Coupon, pricing.py, services.py (place/cancel order)
├── wishlist/          Wishlist
├── reviews/           Review (+ signal that updates product rating)
├── recommendations/   rule-based recommendation form + view
├── core/              home/about/contact/newsletter, context processor, admin dashboard, tests
├── templates/         base.html, includes/, per-app templates, admin/index.html
├── static/            css/style.css, js/main.js
└── media/             uploaded/generated product images
```

## 13. Major modules explained
- **pricing.py / services.py (orders):** all money maths and order creation live here. `place_order()` runs in one database transaction: it re-checks stock, reads prices from the database, creates the order, reduces stock and clears the cart.
- **Product.save():** calculates `sale_price` from MRP and discount so filtering/sorting by price is one simple query.
- **Review signal:** saving or deleting a review recalculates the product's average rating.
- **context_processors.py:** supplies cart count, wishlist count and categories to every page.
- **recommendations/views.py:** four plain filters (diet, level, goal, type) plus budget, then a simple score (rating + best-seller + sales).
- **core/admin.py:** adds the dashboard statistics to the admin home page.
- **static/js/main.js:** one commented block per feature (toasts, menu, AJAX forms, quantity, gallery, filters, search suggestions, validation).

## 14. Future enhancements
Real payment gateway (Razorpay), email/SMS order notifications, product variants with separate prices and stock, guest cart, invoice PDFs, return/refund workflow, Redis caching, Tailwind build step (npm) for production, REST API for a mobile app.

## 15. Limitations
Payment is simulated; cart requires login; stock is tracked per product (not per flavour); Tailwind is loaded from a CDN (fine for a project, not ideal for production); sample images are generated placeholders; emails go to the console.

## 16. Testing approach
Automated tests (`python manage.py test`, 23 tests) cover public pages, search/filter/sort, registration and weak passwords, login protection, cart rules (stock cap, server-side prices, coupons), checkout (COD, simulated payment, free delivery rule, stock check), order cancellation, **authorization (users cannot open other users' orders)**, wishlist, reviews, recommendations and the admin dashboard.
Manual checklist: register → browse → search "creatine" → filter → add to cart → apply `WELCOME10` → checkout → track order → change status in admin → leave a review → try the recommender → test on a phone-sized browser window.

## Security notes
CSRF tokens on all forms, hashed passwords, Django password validators, `login_required` on private pages, queries filtered by `user=request.user`, POST-only actions for cart/order changes, server-side price/quantity/stock validation, safe redirects. Before real deployment: set `DEBUG=False`, a new `SECRET_KEY`, and `ALLOWED_HOSTS`.
