from decimal import Decimal

from django.conf import settings
from django.db import models
from products.models import Product, ProductVariant


class Cart(models.Model):
    """Every user has exactly one cart (one-to-one)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='cart')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Cart of {self.user}'

    @classmethod
    def for_user(cls, user):
        cart, _ = cls.objects.get_or_create(user=user)
        return cart

    def line_items(self):
        return self.items.select_related('product', 'product__brand', 'variant')

    @property
    def subtotal(self):
        return sum((i.line_total for i in self.line_items()), Decimal('0'))

    @property
    def count(self):
        return sum(i.quantity for i in self.items.all())

    def add(self, product, variant, quantity):
        """Add to cart (merging with an existing line). Quantity is capped by stock."""
        limit = min(product.stock, settings.MAX_QTY_PER_ITEM)
        item = self.items.filter(product=product, variant=variant).first()
        new_qty = (item.quantity if item else 0) + quantity
        new_qty = min(new_qty, limit)
        if item:
            item.quantity = new_qty
            item.save()
        else:
            item = self.items.create(product=product, variant=variant, quantity=new_qty)
        return item


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveSmallIntegerField(default=1)

    @property
    def line_total(self):
        # Price always comes from the database, never from the browser
        return self.product.sale_price * self.quantity

    def __str__(self):
        return f'{self.quantity} x {self.product}'
