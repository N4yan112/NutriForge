from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from products.models import Product


class Coupon(models.Model):
    TYPE_CHOICES = [('percent', 'Percentage (%)'), ('flat', 'Flat amount (₹)')]

    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=8, choices=TYPE_CHOICES, default='percent')
    value = models.DecimalField(max_digits=8, decimal_places=2)
    min_order = models.DecimalField('Minimum order (₹)', max_digits=9, decimal_places=2, default=0)
    max_discount = models.DecimalField('Max discount (₹)', max_digits=9, decimal_places=2,
                                       null=True, blank=True, help_text='Only for % coupons')
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text='Blank = unlimited')
    used_count = models.PositiveIntegerField(default=0, editable=False)

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code

    def validate_for(self, subtotal):
        """Return (True, '') if usable for this cart subtotal, else (False, reason)."""
        now = timezone.now()
        if not self.is_active or not (self.valid_from <= now <= self.valid_to):
            return False, 'This coupon has expired or is not active.'
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False, 'This coupon has reached its usage limit.'
        if subtotal < self.min_order:
            return False, f'Add items worth ₹{int(self.min_order)} or more to use this coupon.'
        return True, ''

    def discount_for(self, subtotal):
        subtotal = Decimal(subtotal)
        if self.discount_type == 'percent':
            discount = subtotal * self.value / 100
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = self.value
        return min(discount, subtotal).quantize(Decimal('1'))


class Order(models.Model):
    STATUS_CHOICES = [('placed', 'Placed'), ('confirmed', 'Confirmed'), ('packed', 'Packed'),
                      ('shipped', 'Shipped'), ('delivered', 'Delivered'),
                      ('cancelled', 'Cancelled')]
    FLOW = ['placed', 'confirmed', 'packed', 'shipped', 'delivered']

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                            related_name='orders')
    # Delivery address is copied here so later address edits never change old orders
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10)
    address = models.CharField(max_length=420)
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=60)
    pincode = models.CharField(max_length=6)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='placed')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    coupon_code = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    @property
    def order_number(self):
        return f'NF{10000 + (self.pk or 0)}'

    @property
    def can_cancel(self):
        return self.status in ('placed', 'confirmed')

    @property
    def steps(self):
        """Tracking steps for the template: [(label, done, current), ...]"""
        if self.status == 'cancelled':
            return []
        index = self.FLOW.index(self.status)
        labels = dict(self.STATUS_CHOICES)
        return [(labels[key], i <= index, i == index) for i, key in enumerate(self.FLOW)]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    # name/price are copied so history stays correct if the product changes later
    product_name = models.CharField(max_length=150)
    flavour = models.CharField(max_length=60, blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()

    @property
    def line_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f'{self.quantity} x {self.product_name}'


class Payment(models.Model):
    METHOD_CHOICES = [('cod', 'Cash on Delivery'),
                      ('upi', 'UPI (simulated)'),
                      ('card', 'Credit / Debit Card (simulated)')]
    STATUS_CHOICES = [('pending', 'Pending'), ('paid', 'Paid'),
                      ('failed', 'Failed'), ('refunded', 'Refunded')]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=5, choices=METHOD_CHOICES, default='cod')
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=30, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.order} - {self.get_method_display()}'
