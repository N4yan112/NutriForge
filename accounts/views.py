from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Order
from wishlist.models import Wishlist
from .forms import AddressForm, ProfileForm, RegisterForm
from .models import Address


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)  # log the user in right after registering
        messages.success(request, 'Welcome to NutriForge!')
        return redirect('dashboard')
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'accounts/dashboard.html', {
        'recent_orders': orders[:3],
        'order_count': orders.count(),
        'wishlist_count': Wishlist.objects.filter(user=request.user).count(),
        'address_count': request.user.addresses.count(),
    })


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def addresses(request):
    form = AddressForm(request.POST or None)
    if form.is_valid():
        address = form.save(commit=False)
        address.user = request.user          # always attach to the logged-in user
        address.save()
        messages.success(request, 'Address saved.')
        return redirect('addresses')
    return render(request, 'accounts/addresses.html', {
        'form': form,
        'addresses': request.user.addresses.all(),   # only this user's addresses
    })


@login_required
@require_POST
def delete_address(request, pk):
    get_object_or_404(Address, pk=pk, user=request.user).delete()
    messages.success(request, 'Address removed.')
    return redirect('addresses')
