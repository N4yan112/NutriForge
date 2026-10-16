from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from products.models import Category, Product
from reviews.models import Review
from .forms import ContactForm
from .models import NewsletterSubscriber

FAQS = [
    ('How long does delivery take?', 'Most orders arrive within 3-6 working days across India.'),
    ('Is Cash on Delivery available?', 'Yes. You can pay in cash when your order arrives.'),
    ('Are your supplements genuine?', 'Yes. NutriForge lists only sealed products from verified brands.'),
    ('Can I cancel my order?', 'You can cancel from My Orders until the order is packed.'),
    ('How do I track my order?', 'Open My Orders and select the order to see its status.'),
]


def home(request):
    active = Product.objects.filter(is_active=True).select_related('brand', 'category')
    return render(request, 'core/home.html', {
        'categories': Category.objects.all(),
        'best_sellers': active.filter(is_best_seller=True)[:4],
        'new_arrivals': active.filter(is_new=True)[:4],
        'popular': active.order_by('-sold_count')[:4],
        'offers': active.filter(discount_percent__gte=20).order_by('-discount_percent')[:4],
        'reviews': Review.objects.filter(is_approved=True, rating__gte=4)
                         .select_related('user', 'product')[:3],
    })


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    form = ContactForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Thank you! We have received your message.')
        return redirect('contact')
    return render(request, 'core/contact.html', {'form': form, 'faqs': FAQS})


@require_POST
def newsletter(request):
    email = request.POST.get('email', '').strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, 'Please enter a valid email address.')
        return redirect('home')
    _, created = NewsletterSubscriber.objects.get_or_create(email=email)
    messages.success(request, 'You are subscribed!' if created else 'You are already subscribed.')
    return redirect('home')
