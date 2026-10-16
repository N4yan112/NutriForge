from django.contrib import admin
from django.db.models import F
from .models import Brand, Category, Goal, Product, ProductImage, ProductVariant


class LowStockFilter(admin.SimpleListFilter):
    title = 'stock level'
    parameter_name = 'stock_level'

    def lookups(self, request, model_admin):
        return [('low', 'Low stock'), ('out', 'Out of stock')]

    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(stock__gt=0, stock__lte=F('low_stock_limit'))
        if self.value() == 'out':
            return queryset.filter(stock=0)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price', 'discount_percent',
                    'sale_price', 'stock', 'is_active', 'is_best_seller', 'is_new')
    list_editable = ('price', 'discount_percent', 'stock', 'is_active')   # quick stock/price edits
    list_filter = (LowStockFilter, 'category', 'brand', 'product_type',
                   'dietary_preference', 'is_active', 'is_best_seller', 'is_new')
    search_fields = ('name', 'brand__name', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('goals',)
    inlines = [ProductVariantInline, ProductImageInline]
    fieldsets = (
        ('Basic', {'fields': ('name', 'slug', 'category', 'brand', 'image', 'description')}),
        ('Pricing & stock', {'fields': ('price', 'discount_percent', 'stock', 'low_stock_limit')}),
        ('Details', {'fields': ('ingredients', 'nutrition_info')}),
        ('Classification', {'fields': ('product_type', 'dietary_preference',
                                       'suitable_level', 'goals')}),
        ('Flags', {'fields': ('is_active', 'is_best_seller', 'is_new')}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(Goal, admin.ModelAdmin)
