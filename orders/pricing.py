"""Price calculations. Used by the cart page, checkout page and order creation."""
from decimal import Decimal

from django.conf import settings

from .models import Coupon


def calculate_totals(subtotal, coupon=None):
    subtotal = Decimal(subtotal)
    discount = coupon.discount_for(subtotal) if coupon else Decimal('0')
    after_discount = subtotal - discount
    if after_discount == 0 or after_discount >= settings.FREE_DELIVERY_ABOVE:
        delivery = Decimal('0')
    else:
        delivery = Decimal(settings.DELIVERY_CHARGE)
    return {'subtotal': subtotal, 'discount': discount,
            'delivery': delivery, 'total': after_discount + delivery}


def get_session_coupon(request, subtotal):
    """Return the coupon saved in the session if it is still valid, else None."""
    code = request.session.get('coupon_code')
    if not code:
        return None
    coupon = Coupon.objects.filter(code=code).first()
    if coupon and coupon.validate_for(subtotal)[0]:
        return coupon
    request.session.pop('coupon_code', None)
    return None
