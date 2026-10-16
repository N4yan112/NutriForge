from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.utils import respond, shop_login_required
from orders.models import Coupon
from orders.pricing import calculate_totals, get_session_coupon
from products.models import Product
from .models import Cart


@shop_login_required
def cart_page(request):
    cart = Cart.for_user(request.user)
    items = list(cart.line_items())
    subtotal = sum(i.line_total for i in items)
    coupon = get_session_coupon(request, subtotal)
    return render(request, 'cart/cart.html', {
        'items': items,
        'totals': calculate_totals(subtotal, coupon),
        'coupon': coupon,
        'free_delivery_above': settings.FREE_DELIVERY_ABOVE,
        'max_qty': settings.MAX_QTY_PER_ITEM,
    })


def _read_quantity(request):
    """Validate quantity from the form on the server side."""
    try:
        qty = int(request.POST.get('quantity', 1))
    except ValueError:
        qty = 1
    return max(1, min(qty, settings.MAX_QTY_PER_ITEM))


@require_POST
@shop_login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if not product.in_stock:
        return respond(request, False, 'Sorry, this product is out of stock.')

    variant = None
    variants = product.variants.filter(is_available=True)
    variant_id = request.POST.get('variant')
    if variant_id:                       # flavour picked on the details page
        variant = variants.filter(pk=variant_id).first()
        if variant is None:
            return respond(request, False, 'Please choose a valid flavour.')
    elif variants.exists():              # quick-add from a product card: first flavour
        variant = variants.first()

    cart = Cart.for_user(request.user)
    cart.add(product, variant, _read_quantity(request))

    if request.POST.get('buy_now'):
        return respond(request, True, 'Proceeding to checkout.', reverse('checkout'),
                       cart_count=cart.count, redirect=reverse('checkout'))
    return respond(request, True, f'{product.name} added to cart.', cart_count=cart.count)


@require_POST
@shop_login_required
def update_item(request, item_id):
    item = get_object_or_404(Cart.for_user(request.user).items, pk=item_id)
    qty = _read_quantity(request)
    if qty > item.product.stock:
        qty = item.product.stock
        messages.warning(request, f'Only {qty} in stock for {item.product.name}.')
    if qty < 1:
        item.delete()
    else:
        item.quantity = qty
        item.save()
    return redirect('cart')


@require_POST
@shop_login_required
def remove_item(request, item_id):
    get_object_or_404(Cart.for_user(request.user).items, pk=item_id).delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')


@require_POST
@shop_login_required
def apply_coupon(request):
    code = request.POST.get('code', '').strip()
    subtotal = Cart.for_user(request.user).subtotal
    coupon = Coupon.objects.filter(code__iexact=code).first()
    if coupon is None:
        messages.error(request, 'Invalid coupon code.')
    else:
        ok, msg = coupon.validate_for(subtotal)
        if ok:
            request.session['coupon_code'] = coupon.code
            messages.success(request, f'Coupon {coupon.code} applied!')
        else:
            messages.error(request, msg)
    return redirect('cart')


@require_POST
@shop_login_required
def remove_coupon(request):
    request.session.pop('coupon_code', None)
    messages.success(request, 'Coupon removed.')
    return redirect('cart')
