from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'verified_purchase', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'verified_purchase')
    list_editable = ('is_approved',)
    search_fields = ('product__name', 'user__username', 'comment')
    actions = ['approve', 'hide']

    @admin.action(description='Approve selected reviews')
    def approve(self, request, queryset):
        for r in queryset:          # save() one by one so ratings are recalculated
            r.is_approved = True
            r.save()

    @admin.action(description='Hide selected reviews')
    def hide(self, request, queryset):
        for r in queryset:
            r.is_approved = False
            r.save()
