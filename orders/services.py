"""Order creation. Everything runs in ONE database transaction:
either the whole order is created, or nothing is."""
import uuid

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from products.models import Product
from .models import Coupon, Order, OrderItem, Payment
from .pricing import calculate_totals


class OrderError(Exception):
    """Raised with a message that is safe to show to the customer."""


@transaction.atomic
def place_order(user, cart, address, payment_method, coupon=None):
    items = list(cart.items.select_related('product', 'variant'))
    if not items:
        raise OrderError('Your cart is empty.')

    # Lock the product rows so two customers cannot buy the last item together
    products = {p.pk: p for p in Product.objects.select_for_update()
                .filter(pk__in=[i.product_id for i in items])}

    subtotal = 0
    for item in items:
        product = products[item.product_id]
        if not product.is_active or product.stock < item.quantity:
            raise OrderError(f'Sorry, only {product.stock} unit(s) of "{product.name}" left.')
        subtotal += product.sale_price * item.quantity     # price from DB, not from browser

    if coupon:
        coupon = Coupon.objects.select_for_update().get(pk=coupon.pk)
        ok, reason = coupon.validate_for(subtotal)
        if not ok:
            raise OrderError(reason)
    totals = calculate_totals(subtotal, coupon)

    order = Order.objects.create(
        user=user, full_name=address['full_name'], phone=address['phone'],
        address=f"{address['line1']} {address['line2']}".strip(),
        city=address['city'], state=address['state'], pincode=address['pincode'],
        subtotal=totals['subtotal'], discount=totals['discount'],
        delivery_charge=totals['delivery'], total=totals['total'],
        coupon=coupon, coupon_code=coupon.code if coupon else '')

    for item in items:
        product = products[item.product_id]
        OrderItem.objects.create(
            order=order, product=product, product_name=product.name,
            flavour=item.variant.flavour if item.variant else '',
            price=product.sale_price, quantity=item.quantity)
        Product.objects.filter(pk=product.pk).update(
            stock=F('stock') - item.quantity, sold_count=F('sold_count') + item.quantity)

    if coupon:
        Coupon.objects.filter(pk=coupon.pk).update(used_count=F('used_count') + 1)

    # Payment is simulated: no real card/UPI details are ever collected.
    if payment_method == 'cod':
        Payment.objects.create(order=order, method='cod', status='pending',
                               amount=order.total)
    else:
        Payment.objects.create(order=order, method=payment_method, status='paid',
                               amount=order.total, paid_at=timezone.now(),
                               transaction_id='SIM' + uuid.uuid4().hex[:10].upper())

    cart.items.all().delete()
    return order


@transaction.atomic
def cancel_order(order):
    """Cancel an order and put the stock back."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.can_cancel:
        raise OrderError('This order can no longer be cancelled.')
    for item in order.items.all():
        if item.product_id:
            Product.objects.filter(pk=item.product_id).update(
                stock=F('stock') + item.quantity, sold_count=F('sold_count') - item.quantity)
    order.status = 'cancelled'
    order.save()
    if hasattr(order, 'payment') and order.payment.status == 'paid':
        order.payment.status = 'refunded'
        order.payment.save()
    return order
