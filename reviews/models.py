from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from products.models import Product


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=100, blank=True)
    comment = models.TextField(max_length=1000)
    verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)   # admin can hide a review
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')      # one review per user per product
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.product} ({self.rating}★)'


# Keep Product.avg_rating in sync whenever a review is saved or deleted
@receiver([post_save, post_delete], sender=Review)
def refresh_product_rating(sender, instance, **kwargs):
    instance.product.update_rating()
