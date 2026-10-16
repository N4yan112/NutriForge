from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.forms import AddressForm
from accounts.models import Address
from cart.models import Cart
from .models import Order, Payment
from .pricing import calculate_totals, get_session_coupon
from .services import OrderError, cancel_order, place_order


@login_required
def checkout(request):
    cart = Cart.for_user(request.user)
    items = list(cart.line_items())
    if not items:
        messages.info(request, 'Your cart is empty.')
        return redirect('cart')

    subtotal = sum(i.line_total for i in items)
    coupon = get_session_coupon(request, subtotal)
    saved = request.user.addresses.all()
    new_form = AddressForm(request.POST or None, prefix='new', initial={
        'full_name': request.user.get_full_name(), 'phone': request.user.phone})
    selected = request.POST.get('address', str(saved[0].pk) if saved else '')
    payment_method = request.POST.get('payment_method', 'cod')

    if request.method == 'POST':
        address_data = None
        if payment_method not in dict(Payment.METHOD_CHOICES):
            messages.error(request, 'Please choose a payment method.')
        elif selected:                                    # a saved address was picked
            address = saved.filter(pk=selected).first()   # only THIS user's addresses
            if address is None:
                messages.error(request, 'Please choose a valid address.')
            else:
                address_data = {f: getattr(address, f) for f in (
                    'full_name', 'phone', 'line1', 'line2', 'city', 'state', 'pincode')}
        elif new_form.is_valid():                         # a new address was typed
            address = new_form.save(commit=False)
            address.user = request.user
            address.save()
            address_data = new_form.cleaned_data

        if address_data:
            try:
                order = place_order(request.user, cart, address_data, payment_method, coupon)
            except OrderError as error:
                messages.error(request, str(error))
                return redirect('cart')
            request.session.pop('coupon_code', None)
            messages.success(request, f'Order {order.order_number} placed successfully!')
            return redirect('order_detail', pk=order.pk)

    return render(request, 'orders/checkout.html', {
        'items': items, 'totals': calculate_totals(subtotal, coupon), 'coupon': coupon,
        'saved_addresses': saved, 'new_form': new_form, 'selected': selected,
        'payment_methods': Payment.METHOD_CHOICES, 'payment_method': payment_method,
    })


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/order_list.html', {'orders': orders})


@login_required
def order_detail(request, pk):
    # user=request.user -> nobody can open another customer's order
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=pk, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    try:
        cancel_order(order)
        messages.success(request, f'Order {order.order_number} cancelled.')
    except OrderError as error:
        messages.error(request, str(error))
    return redirect('order_detail', pk=pk)
