from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Address


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (('Extra', {'fields': ('phone',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': ('email', 'phone')}),)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'city', 'pincode', 'is_default')
    search_fields = ('full_name', 'user__username', 'city', 'pincode')
