from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(r'^\d{10}$', 'Enter a 10-digit phone number.')
pincode_validator = RegexValidator(r'^\d{6}$', 'Enter a 6-digit pincode.')


class User(AbstractUser):
    """Django's built-in user + unique email + phone number."""
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10, blank=True, validators=[phone_validator])


class Address(models.Model):
    """A user can save many delivery addresses (one-to-many)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='addresses')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10, validators=[phone_validator])
    line1 = models.CharField('Address line 1', max_length=200)
    line2 = models.CharField('Address line 2', max_length=200, blank=True)
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=60)
    pincode = models.CharField(max_length=6, validators=[pincode_validator])
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'addresses'
        ordering = ['-is_default', '-id']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:  # only one default address per user
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)

    def __str__(self):
        return f'{self.full_name}, {self.city} - {self.pincode}'
