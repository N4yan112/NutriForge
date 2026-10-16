from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from cart.models import Cart
from core.utils import respond, shop_login_required
from products.models import Product
from .models import Wishlist


@shop_login_required
def wishlist_page(request):
    items = Wishlist.objects.filter(user=request.user, product__is_active=True)\
        .select_related('product', 'product__brand')
    return render(request, 'wishlist/list.html', {'items': items})


@require_POST
@shop_login_required
def toggle(request, pk):
    """Add the product if it is not in the wishlist, otherwise remove it."""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.delete()
    count = Wishlist.objects.filter(user=request.user).count()
    msg = 'Added to wishlist.' if created else 'Removed from wishlist.'
    return respond(request, True, msg, added=created, wishlist_count=count)


@require_POST
@shop_login_required
def move_to_cart(request, pk):
    item = get_object_or_404(Wishlist, pk=pk, user=request.user)
    product = item.product
    if not product.in_stock:
        return respond(request, False, 'This product is out of stock.', reverse('wishlist'))
    cart = Cart.for_user(request.user)
    cart.add(product, None, 1)
    item.delete()
    return respond(request, True, f'{product.name} moved to cart.', reverse('wishlist'))
