from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from core.utils import shop_login_required
from orders.models import OrderItem
from products.models import Product
from .forms import ReviewForm
from .models import Review


@require_POST
@shop_login_required
def submit_review(request, pk):
    """Create or update the logged-in user's review for a product."""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    existing = Review.objects.filter(product=product, user=request.user).first()
    form = ReviewForm(request.POST, instance=existing)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user                      # never trust a user id from the form
        review.verified_purchase = OrderItem.objects.filter(
            order__user=request.user, product=product).exists()
        review.save()
        messages.success(request, 'Thanks! Your review has been saved.')
    else:
        messages.error(request, 'Please write a comment and choose a rating.')
    return redirect(product.get_absolute_url() + '#reviews')
