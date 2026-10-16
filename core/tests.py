"""Run with:  python manage.py test
Covers the main customer journey and the security rules."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cart.models import Cart
from orders.models import Coupon, Order
from products.models import Brand, Category, Goal, Product, ProductVariant
from reviews.models import Review

User = get_user_model()


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])  # faster tests
class ShopTestBase(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='Creatine', slug='creatine')
        brand = Brand.objects.create(name='PureLabs', slug='purelabs')
        goal = Goal.objects.create(name='Muscle Gain', slug='muscle-gain')
        self.creatine = Product.objects.create(
            name='Pure Creatine 250g', slug='pure-creatine-250g', category=cat, brand=brand,
            description='d', price=1000, discount_percent=20, stock=5, product_type='powder',
            dietary_preference='vegan')
        self.creatine.goals.add(goal)
        self.whey = Product.objects.create(
            name='Whey 1kg', slug='whey-1kg', category=Category.objects.create(name='Whey', slug='whey'),
            brand=brand, description='d', price=2000, discount_percent=0, stock=10,
            dietary_preference='vegetarian')
        ProductVariant.objects.create(product=self.whey, flavour='Chocolate')
        self.user = User.objects.create_user('asha', 'asha@example.com', 'Str0ng!Pass99')
        self.other = User.objects.create_user('ravi', 'ravi@example.com', 'Str0ng!Pass99')
        self.goal = goal

    def login(self, user=None):
        self.client.force_login(user or self.user)


class PublicPagesTests(ShopTestBase):
    def test_pages_load(self):
        for name in ('home', 'about', 'contact', 'product_list', 'recommend', 'login', 'register',
                     'password_reset'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(self.creatine.get_absolute_url()).status_code, 200)

    def test_sale_price_calculated(self):
        self.assertEqual(self.creatine.sale_price, Decimal('800'))

    def test_search_by_name_brand_category(self):
        for q in ('creatine', 'purelabs', 'Whey'):
            resp = self.client.get(reverse('product_list'), {'q': q})
            self.assertTrue(len(resp.context['page'].object_list) >= 1, q)
        resp = self.client.get(reverse('product_list'), {'q': 'creatine'})
        names = [p.name for p in resp.context['page'].object_list]
        self.assertIn('Pure Creatine 250g', names)
        self.assertNotIn('Whey 1kg', names)

    def test_filters_and_sorting(self):
        resp = self.client.get(reverse('product_list'), {'min_price': 1000, 'sort': 'price_desc'})
        self.assertEqual([p.name for p in resp.context['page'].object_list], ['Whey 1kg'])
        resp = self.client.get(reverse('product_list'), {'diet': 'vegan'})
        self.assertEqual(resp.context['page'].paginator.count, 1)


class AuthTests(ShopTestBase):
    def test_register_rejects_weak_password(self):
        resp = self.client.post(reverse('register'), {
            'username': 'newbie', 'email': 'n@example.com', 'phone': '9876543210',
            'password1': '12345678', 'password2': '12345678'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='newbie').exists())

    def test_register_ok(self):
        resp = self.client.post(reverse('register'), {
            'username': 'newbie', 'email': 'n@example.com', 'phone': '9876543210',
            'password1': 'Gym!Rat2024x', 'password2': 'Gym!Rat2024x'})
        self.assertRedirects(resp, reverse('dashboard'))

    def test_protected_pages_redirect_to_login(self):
        for name in ('dashboard', 'profile', 'order_list', 'cart', 'wishlist', 'checkout'):
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302, name)
            self.assertIn('/accounts/login/', resp.url)


class CartTests(ShopTestBase):
    def test_add_requires_login_json(self):
        resp = self.client.post(reverse('cart_add', args=[self.creatine.pk]),
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 401)

    def test_add_and_quantity_capped_by_stock(self):
        self.login()
        self.client.post(reverse('cart_add', args=[self.creatine.pk]), {'quantity': 99})
        item = Cart.for_user(self.user).items.get()
        self.assertEqual(item.quantity, 5)                    # stock is 5
        self.assertEqual(item.line_total, Decimal('4000'))   # price from DB

    def test_flavour_auto_selected_and_invalid_rejected(self):
        self.login()
        self.client.post(reverse('cart_add', args=[self.whey.pk]), {'quantity': 1})
        self.assertEqual(Cart.for_user(self.user).items.get().variant.flavour, 'Chocolate')
        resp = self.client.post(reverse('cart_add', args=[self.whey.pk]), {'variant': 9999},
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 400)

    def test_coupon(self):
        self.login()
        Coupon.objects.create(code='SAVE10', discount_type='percent', value=10, min_order=500,
                              valid_to=timezone.now() + timedelta(days=5))
        self.client.post(reverse('cart_add', args=[self.whey.pk]), {'quantity': 1})
        self.client.post(reverse('coupon_apply'), {'code': 'save10'})
        resp = self.client.get(reverse('cart'))
        self.assertEqual(resp.context['totals']['discount'], Decimal('200'))
        self.client.post(reverse('coupon_apply'), {'code': 'NOPE'})       # invalid code keeps the old one
        self.assertEqual(self.client.get(reverse('cart')).context['coupon'].code, 'SAVE10')


class OrderTests(ShopTestBase):
    ADDRESS = {'address': '', 'payment_method': 'cod', 'new-full_name': 'Asha K', 'new-phone': '9876543210',
               'new-line1': '12 MG Road', 'new-line2': '', 'new-city': 'Pune', 'new-state': 'MH',
               'new-pincode': '411001'}

    def place(self, qty=2, data=None):
        self.login()
        self.client.post(reverse('cart_add', args=[self.creatine.pk]), {'quantity': qty})
        return self.client.post(reverse('checkout'), data or self.ADDRESS)

    def test_cod_order_flow(self):
        resp = self.place(2)
        order = Order.objects.get()
        self.assertRedirects(resp, reverse('order_detail', args=[order.pk]))
        self.assertEqual(order.subtotal, Decimal('1600'))
        self.assertEqual(order.delivery_charge, Decimal('0'))      # 1600 is above ₹999 -> free
        self.creatine.refresh_from_db()
        self.assertEqual(self.creatine.stock, 3)
        self.assertEqual(self.creatine.sold_count, 2)
        self.assertFalse(Cart.for_user(self.user).items.exists())
        self.assertEqual(order.payment.status, 'pending')

    def test_free_delivery_threshold(self):
        self.place(2)
        self.assertEqual(Order.objects.get().delivery_charge, Decimal('0'))   # 1600 >= 999

    def test_small_order_pays_delivery(self):
        self.place(1)
        order = Order.objects.get()
        self.assertEqual(order.delivery_charge, Decimal('49'))
        self.assertEqual(order.total, Decimal('849'))

    def test_simulated_upi_is_paid(self):
        self.place(1, {**self.ADDRESS, 'payment_method': 'upi'})
        self.assertEqual(Order.objects.get().payment.status, 'paid')

    def test_invalid_address_blocks_order(self):
        self.place(1, {**self.ADDRESS, 'new-pincode': '12'})
        self.assertEqual(Order.objects.count(), 0)

    def test_cannot_view_or_cancel_other_users_order(self):
        self.place(1)
        order = Order.objects.get()
        self.login(self.other)
        self.assertEqual(self.client.get(reverse('order_detail', args=[order.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('order_cancel', args=[order.pk])).status_code, 404)

    def test_cancel_restores_stock(self):
        self.place(2)
        order = Order.objects.get()
        self.client.post(reverse('order_cancel', args=[order.pk]))
        order.refresh_from_db()
        self.creatine.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(self.creatine.stock, 5)

    def test_stock_checked_at_checkout(self):
        self.login()
        self.client.post(reverse('cart_add', args=[self.creatine.pk]), {'quantity': 4})
        Product.objects.filter(pk=self.creatine.pk).update(stock=2)   # someone else bought items
        self.client.post(reverse('checkout'), self.ADDRESS)
        self.assertEqual(Order.objects.count(), 0)


class WishlistReviewRecommendTests(ShopTestBase):
    def test_wishlist_toggle_and_move(self):
        self.login()
        r = self.client.post(reverse('wishlist_toggle', args=[self.creatine.pk]),
                             HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTrue(r.json()['added'])
        item = self.user.wishlist_items.get()
        self.client.post(reverse('wishlist_move', args=[item.pk]))
        self.assertEqual(self.user.wishlist_items.count(), 0)
        self.assertEqual(Cart.for_user(self.user).items.count(), 1)

    def test_review_updates_rating(self):
        self.login()
        self.client.post(reverse('submit_review', args=[self.creatine.pk]),
                         {'rating': 4, 'title': 'Good', 'comment': 'Works well'})
        self.creatine.refresh_from_db()
        self.assertEqual(self.creatine.avg_rating, Decimal('4.00'))
        self.assertEqual(self.creatine.review_count, 1)
        Review.objects.filter(product=self.creatine).update(is_approved=False)

    def test_recommendation_rules(self):
        resp = self.client.get(reverse('recommend'), {
            'goal': self.goal.pk, 'budget': 1000, 'level': 'beginner', 'diet': 'vegan',
            'supplement_type': 'any'})
        self.assertEqual([p.name for p in resp.context['results']], ['Pure Creatine 250g'])
        resp = self.client.get(reverse('recommend'), {
            'goal': self.goal.pk, 'budget': 500, 'level': 'beginner', 'diet': 'vegan',
            'supplement_type': 'any'})
        self.assertEqual(resp.context['results'], [])         # over budget


class AdminTests(ShopTestBase):
    def test_admin_dashboard_stats(self):
        admin_user = User.objects.create_superuser('boss', 'boss@example.com', 'Adm1n!Pass99')
        self.client.force_login(admin_user)
        resp = self.client.get('/admin/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Total revenue')
        for url in ('/admin/products/product/', '/admin/orders/order/', '/admin/reviews/review/',
                    '/admin/orders/coupon/'):
            self.assertEqual(self.client.get(url).status_code, 200, url)
