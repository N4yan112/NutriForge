from decimal import Decimal

from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=4, blank=True, help_text='An emoji shown on category cards')
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['id']

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Goal(models.Model):
    """Fitness goals (e.g. Muscle Gain). Used by the recommendation feature."""
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    TYPE_CHOICES = [('powder', 'Powder'), ('capsule', 'Capsule / Softgel'),
                    ('tablet', 'Tablet'), ('bar', 'Bar'),
                    ('liquid', 'Liquid'), ('accessory', 'Accessory')]
    DIET_CHOICES = [('vegan', 'Vegan'), ('vegetarian', 'Vegetarian'),
                    ('non_veg', 'Non-Vegetarian')]
    LEVEL_CHOICES = [('all', 'All levels'), ('beginner', 'Beginner'),
                     ('intermediate', 'Intermediate'), ('advanced', 'Advanced')]

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    goals = models.ManyToManyField(Goal, blank=True, related_name='products')

    product_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='powder')
    dietary_preference = models.CharField(max_length=12, choices=DIET_CHOICES, default='vegetarian')
    suitable_level = models.CharField(max_length=12, choices=LEVEL_CHOICES, default='all')

    description = models.TextField()
    ingredients = models.TextField(blank=True)
    nutrition_info = models.TextField(blank=True, help_text='One per line, like  Protein: 24 g')

    price = models.DecimalField('MRP (₹)', max_digits=9, decimal_places=2)
    discount_percent = models.PositiveSmallIntegerField(default=0, help_text='0 - 90')
    sale_price = models.DecimalField(max_digits=9, decimal_places=2, editable=False, default=0)
    stock = models.PositiveIntegerField(default=0)
    low_stock_limit = models.PositiveIntegerField(default=10)

    image = models.ImageField(upload_to='products/', blank=True)
    is_best_seller = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sold_count = models.PositiveIntegerField(default=0)

    # Denormalised review stats (updated by Review.save/delete) - makes sorting easy
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        discount = min(max(self.discount_percent, 0), 90)
        self.sale_price = (Decimal(self.price) * (100 - discount) / 100).quantize(Decimal('1'))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.slug])

    # ---- helpers used by templates ----
    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock <= self.low_stock_limit

    @property
    def on_sale(self):
        return self.discount_percent > 0

    @property
    def rating_rounded(self):
        return int(round(self.avg_rating))

    @property
    def nutrition_rows(self):
        rows = []
        for line in self.nutrition_info.splitlines():
            if ':' in line:
                label, value = line.split(':', 1)
                rows.append((label.strip(), value.strip()))
        return rows

    def update_rating(self):
        """Recalculate average rating from approved reviews."""
        data = self.reviews.filter(is_approved=True).aggregate(
            avg=models.Avg('rating'), n=models.Count('id'))
        self.avg_rating = Decimal(str(round(data['avg'] or 0, 2)))
        self.review_count = data['n']
        Product.objects.filter(pk=self.pk).update(
            avg_rating=self.avg_rating, review_count=self.review_count)


class ProductImage(models.Model):
    """Extra gallery images for a product (one-to-many)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f'Image for {self.product.name}'


class ProductVariant(models.Model):
    """A flavour option of a product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    flavour = models.CharField(max_length=60)
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ('product', 'flavour')

    def __str__(self):
        return f'{self.product.name} - {self.flavour}'
