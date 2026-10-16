"""Loads realistic sample data:  python manage.py load_sample_data
Creates categories, brands, goals, ~30 products (with generated images), coupons,
demo customers and reviews.  Safe to run more than once."""
import io
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from orders.models import Coupon
from products.models import (Brand, Category, Goal, Product, ProductImage,
                             ProductVariant)
from reviews.models import Review

CATEGORIES = [
    ('Whey Protein', '🥛'), ('Plant Protein', '🌱'), ('Mass Gainers', '💪'), ('Creatine', '⚡'),
    ('Pre-Workout', '🔥'), ('BCAA', '🧪'), ('EAA', '🧬'), ('Protein Bars', '🍫'),
    ('Vitamins & Minerals', '💊'), ('Omega-3 / Fish Oil', '🐟'), ('Fat Burners', '🏃'),
    ('Electrolytes', '💧'), ('Glutamine', '🔋'), ('Shakers & Accessories', '🥤'),
]
BRANDS = ['NutriForge', 'IronCore', 'PureLabs', 'GreenFuel', 'VitaPlus', 'HydroMax']
GOALS = ['Muscle Gain', 'Weight Loss', 'Endurance', 'General Health', 'Recovery']

# Short texts reused per category (keeps this file readable)
INFO = {
    'Whey Protein': ('Whey protein concentrate, cocoa, natural flavour, sucralose, lecithin.',
                     'Serving size: 30 g\nCalories: 120 kcal\nProtein: 24 g\nCarbohydrates: 3 g\nFat: 1.5 g\nBCAA: 5.2 g'),
    'Plant Protein': ('Pea protein isolate, brown rice protein, natural flavour, stevia.',
                      'Serving size: 33 g\nCalories: 125 kcal\nProtein: 24 g\nCarbohydrates: 4 g\nFat: 2 g\nFibre: 2 g'),
    'Mass Gainers': ('Maltodextrin, whey protein concentrate, oat flour, MCT powder, vitamins.',
                     'Serving size: 150 g\nCalories: 590 kcal\nProtein: 30 g\nCarbohydrates: 105 g\nFat: 5 g'),
    'Creatine': ('Micronised creatine monohydrate (100%).',
                 'Serving size: 3 g\nCreatine monohydrate: 3 g\nCalories: 0 kcal'),
    'Pre-Workout': ('Beta-alanine, citrulline malate, caffeine anhydrous, taurine, natural flavour.',
                    'Serving size: 10 g\nCaffeine: 150 mg\nCitrulline malate: 6 g\nBeta-alanine: 2 g\nTaurine: 1 g'),
    'BCAA': ('L-leucine, L-isoleucine, L-valine (2:1:1), citric acid, natural flavour.',
             'Serving size: 8 g\nBCAA: 5 g\nLeucine: 2.5 g\nCalories: 20 kcal'),
    'EAA': ('9 essential amino acids, citric acid, natural flavour, stevia.',
            'Serving size: 12 g\nEssential amino acids: 9 g\nLeucine: 2.7 g\nCalories: 36 kcal'),
    'Protein Bars': ('Whey protein, almonds, dates, cocoa butter, oats.',
                     'Serving size: 60 g bar\nCalories: 220 kcal\nProtein: 20 g\nSugar: 3 g\nFat: 8 g'),
    'Vitamins & Minerals': ('Vitamin C, D3, B-complex, zinc, magnesium, selenium.',
                            'Serving size: 1 tablet\nVitamin C: 80 mg\nVitamin D3: 600 IU\nZinc: 10 mg\nMagnesium: 100 mg'),
    'Omega-3 / Fish Oil': ('Purified fish oil, gelatin capsule shell, glycerin, natural tocopherols.',
                           'Serving size: 1 softgel\nEPA: 360 mg\nDHA: 240 mg\nTotal omega-3: 600 mg'),
    'Fat Burners': ('Green tea extract, L-carnitine, garcinia, black pepper extract.',
                    'Serving size: 2 capsules\nGreen tea extract: 500 mg\nL-carnitine: 500 mg\nCalories: 5 kcal'),
    'Electrolytes': ('Sodium, potassium, magnesium, dextrose, citric acid, natural flavour.',
                     'Serving size: 8 g\nSodium: 200 mg\nPotassium: 150 mg\nMagnesium: 50 mg\nCalories: 20 kcal'),
    'Glutamine': ('L-glutamine (100%).', 'Serving size: 5 g\nL-glutamine: 5 g\nCalories: 20 kcal'),
    'Shakers & Accessories': ('', ''),
}
DESC = {
    'Whey Protein': 'Fast-absorbing whey protein for muscle growth and recovery after training.',
    'Plant Protein': 'Clean plant-based protein that is easy to digest and free from dairy.',
    'Mass Gainers': 'High-calorie formula to help hard gainers add quality size.',
    'Creatine': 'Pure creatine to improve strength, power and training performance.',
    'Pre-Workout': 'Energy and focus formula to power through your toughest sessions.',
    'BCAA': 'Branched-chain amino acids to support muscle recovery and reduce fatigue.',
    'EAA': 'Complete essential amino acid profile for recovery and muscle protein synthesis.',
    'Protein Bars': 'Tasty high-protein snack with low sugar - perfect on the go.',
    'Vitamins & Minerals': 'Daily vitamins and minerals to support immunity and energy.',
    'Omega-3 / Fish Oil': 'High-strength omega-3 for heart, joint and brain health.',
    'Fat Burners': 'Thermogenic support to complement a calorie-controlled diet and training.',
    'Electrolytes': 'Replenish salts lost in sweat to stay hydrated and avoid cramps.',
    'Glutamine': 'Supports muscle recovery and gut health after intense workouts.',
    'Shakers & Accessories': 'Durable, leak-proof gear for your daily training.',
}
FLAVOURS = {
    'Whey Protein': ['Chocolate', 'Vanilla', 'Cookies & Cream'], 'Plant Protein': ['Chocolate', 'Peanut Butter'],
    'Mass Gainers': ['Chocolate', 'Banana'], 'Pre-Workout': ['Fruit Punch', 'Blue Raspberry'],
    'BCAA': ['Watermelon', 'Orange'], 'EAA': ['Mango', 'Lemon Lime'], 'Protein Bars': ['Choco Almond', 'Peanut Butter'],
    'Electrolytes': ['Lemon', 'Orange'], 'Glutamine': ['Unflavoured'], 'Creatine': ['Unflavoured'],
}

# name, category, brand, type, diet, MRP, discount%, stock, best, new, goals, level
P = [
    ('NutriForge Whey Protein 1kg', 'Whey Protein', 'NutriForge', 'powder', 'vegetarian', 2999, 20, 60, 1, 0, ['Muscle Gain', 'Recovery'], 'all'),
    ('IronCore Whey Isolate 2kg', 'Whey Protein', 'IronCore', 'powder', 'vegetarian', 6499, 15, 25, 0, 1, ['Muscle Gain', 'Weight Loss'], 'intermediate'),
    ('PureLabs Whey Concentrate 500g', 'Whey Protein', 'PureLabs', 'powder', 'vegetarian', 1599, 10, 8, 0, 0, ['Muscle Gain'], 'beginner'),
    ('NutriForge Plant Protein 1kg', 'Plant Protein', 'NutriForge', 'powder', 'vegan', 2799, 15, 40, 1, 0, ['Muscle Gain', 'General Health'], 'all'),
    ('GreenFuel Vegan Protein 2kg', 'Plant Protein', 'GreenFuel', 'powder', 'vegan', 5299, 20, 18, 0, 1, ['Muscle Gain', 'Weight Loss'], 'all'),
    ('NutriForge Mass Gainer 3kg', 'Mass Gainers', 'NutriForge', 'powder', 'vegetarian', 3499, 25, 30, 1, 0, ['Muscle Gain'], 'beginner'),
    ('IronCore Serious Mass 5kg', 'Mass Gainers', 'IronCore', 'powder', 'vegetarian', 5999, 10, 12, 0, 0, ['Muscle Gain'], 'intermediate'),
    ('Pure Creatine Monohydrate 250g', 'Creatine', 'PureLabs', 'powder', 'vegan', 1499, 20, 80, 1, 0, ['Muscle Gain', 'Endurance'], 'all'),
    ('NutriForge Creatine Monohydrate 100g', 'Creatine', 'NutriForge', 'powder', 'vegan', 699, 0, 5, 0, 1, ['Muscle Gain'], 'beginner'),
    ('NutriForge Advanced Pre-Workout 300g', 'Pre-Workout', 'NutriForge', 'powder', 'vegan', 1999, 25, 35, 1, 0, ['Endurance', 'Muscle Gain'], 'intermediate'),
    ('IronCore Extreme Pre-Workout 250g', 'Pre-Workout', 'IronCore', 'powder', 'vegan', 2299, 10, 20, 0, 1, ['Endurance'], 'advanced'),
    ('PureLabs BCAA 2:1:1 250g', 'BCAA', 'PureLabs', 'powder', 'vegan', 1399, 15, 45, 0, 0, ['Recovery', 'Endurance'], 'all'),
    ('HydroMax BCAA Recovery 400g', 'BCAA', 'HydroMax', 'powder', 'vegan', 1899, 20, 22, 0, 1, ['Recovery'], 'all'),
    ('NutriForge EAA Intra-Workout 300g', 'EAA', 'NutriForge', 'powder', 'vegan', 1799, 15, 28, 0, 1, ['Recovery', 'Muscle Gain'], 'intermediate'),
    ('GreenFuel Plant EAA 250g', 'EAA', 'GreenFuel', 'powder', 'vegan', 1599, 0, 15, 0, 0, ['Recovery', 'General Health'], 'all'),
    ('NutriForge Protein Bars (Box of 12)', 'Protein Bars', 'NutriForge', 'bar', 'vegetarian', 1299, 10, 70, 1, 0, ['Muscle Gain', 'Weight Loss'], 'all'),
    ('GreenFuel Vegan Protein Bars (Box of 6)', 'Protein Bars', 'GreenFuel', 'bar', 'vegan', 799, 0, 40, 0, 1, ['General Health', 'Weight Loss'], 'all'),
    ('VitaPlus Daily Multivitamin (60 tablets)', 'Vitamins & Minerals', 'VitaPlus', 'tablet', 'vegetarian', 799, 20, 90, 1, 0, ['General Health'], 'all'),
    ('VitaPlus Vitamin D3 + K2 (60 capsules)', 'Vitamins & Minerals', 'VitaPlus', 'capsule', 'vegan', 599, 10, 50, 0, 1, ['General Health', 'Recovery'], 'all'),
    ('NutriForge Omega-3 Capsules (90 softgels)', 'Omega-3 / Fish Oil', 'NutriForge', 'capsule', 'non_veg', 999, 15, 65, 1, 0, ['General Health', 'Recovery'], 'all'),
    ('VitaPlus Algae Omega-3 (60 capsules)', 'Omega-3 / Fish Oil', 'VitaPlus', 'capsule', 'vegan', 1399, 0, 20, 0, 1, ['General Health'], 'all'),
    ('IronCore Fat Burner Thermo (60 capsules)', 'Fat Burners', 'IronCore', 'capsule', 'vegan', 1499, 30, 33, 0, 0, ['Weight Loss'], 'intermediate'),
    ('PureLabs CLA + L-Carnitine (90 capsules)', 'Fat Burners', 'PureLabs', 'capsule', 'vegetarian', 1299, 20, 3, 0, 0, ['Weight Loss'], 'beginner'),
    ('HydroMax Electrolyte Powder 400g', 'Electrolytes', 'HydroMax', 'powder', 'vegan', 899, 10, 75, 1, 0, ['Endurance', 'Recovery'], 'all'),
    ('NutriForge Electrolyte Sachets (Box of 20)', 'Electrolytes', 'NutriForge', 'powder', 'vegan', 599, 0, 55, 0, 1, ['Endurance'], 'all'),
    ('PureLabs L-Glutamine 250g', 'Glutamine', 'PureLabs', 'powder', 'vegan', 1199, 15, 38, 0, 0, ['Recovery'], 'all'),
    ('NutriForge Fitness Shaker 700ml', 'Shakers & Accessories', 'NutriForge', 'accessory', 'vegan', 399, 0, 120, 1, 0, ['General Health'], 'all'),
    ('HydroMax Steel Gym Bottle 1L', 'Shakers & Accessories', 'HydroMax', 'accessory', 'vegan', 699, 20, 45, 0, 1, ['General Health'], 'all'),
    ('IronCore Lifting Straps & Gloves Set', 'Shakers & Accessories', 'IronCore', 'accessory', 'vegan', 899, 25, 30, 0, 0, ['Muscle Gain'], 'all'),
]

PALETTE = [(249, 115, 22), (37, 99, 235), (22, 163, 74), (220, 38, 38), (147, 51, 234), (13, 148, 136)]


def _font(size):
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                 'C:/Windows/Fonts/arialbd.ttf', '/Library/Fonts/Arial Bold.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_image(title, brand, color, variant=0):
    """Draw a simple supplement tub as a placeholder product photo (no copyrighted images)."""
    w = 700
    img = Image.new('RGB', (w, w), (245, 245, 247))
    d = ImageDraw.Draw(img)
    for y in range(w):                                  # soft vertical gradient background
        shade = 245 - int(y / w * 25)
        d.line([(0, y), (w, y)], fill=(shade, shade, shade + 2))
    if variant == 0:                                    # front of tub
        d.ellipse([170, 560, 530, 620], fill=(215, 215, 218))
        d.rounded_rectangle([190, 200, 510, 590], 28, fill=(30, 30, 36))
        d.rounded_rectangle([210, 140, 490, 215], 18, fill=color)
        d.rectangle([190, 330, 510, 470], fill=color)
        d.text((350, 390), brand.upper(), font=_font(38), fill='white', anchor='mm')
        words, lines, line = title.replace('NutriForge ', '').split(), [], ''
        for word in words:
            if len(line + word) > 17:
                lines.append(line.strip()); line = ''
            line += word + ' '
        lines.append(line.strip())
        for i, text in enumerate(lines[:3]):
            d.text((350, 505 + i * 26), text, font=_font(20), fill='white', anchor='mm')
    else:                                               # extra gallery views
        d.rounded_rectangle([120, 100, 580, 600], 24, fill='white', outline=color, width=8)
        d.text((350, 170), 'SUPPLEMENT FACTS' if variant == 1 else 'HOW TO USE', font=_font(32), fill=color, anchor='mm')
        for i in range(6):
            d.line([(170, 240 + i * 55), (530, 240 + i * 55)], fill=(220, 220, 224), width=3)
        d.text((350, 560), brand.upper(), font=_font(24), fill=(90, 90, 100), anchor='mm')
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=85)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = 'Load sample NutriForge data (products, categories, coupons, demo users)'

    def handle(self, *args, **options):
        random.seed(42)
        User = get_user_model()
        cats = {}
        for name, icon in CATEGORIES:
            cats[name], _ = Category.objects.get_or_create(
                name=name, defaults={'slug': slugify(name), 'icon': icon})
        brands = {n: Brand.objects.get_or_create(name=n, defaults={'slug': slugify(n)})[0] for n in BRANDS}
        goals = {n: Goal.objects.get_or_create(name=n, defaults={'slug': slugify(n)})[0] for n in GOALS}

        created = 0
        for i, (name, cat, brand, ptype, diet, mrp, disc, stock, best, new, gl, level) in enumerate(P):
            if Product.objects.filter(name=name).exists():
                continue
            ingredients, nutrition = INFO[cat]
            product = Product.objects.create(
                name=name, slug=slugify(name), category=cats[cat], brand=brands[brand],
                product_type=ptype, dietary_preference=diet, suitable_level=level,
                description=DESC[cat], ingredients=ingredients, nutrition_info=nutrition,
                price=mrp, discount_percent=disc, stock=stock, is_best_seller=bool(best),
                is_new=bool(new), sold_count=random.randint(5, 400))
            product.goals.set([goals[g] for g in gl])
            color = PALETTE[i % len(PALETTE)]
            product.image.save(f'{product.slug}.jpg', make_image(name, brand, color), save=True)
            for v in (1, 2):
                gallery = ProductImage(product=product, alt_text=f'{name} view {v}')
                gallery.image.save(f'{product.slug}-{v}.jpg', make_image(name, brand, color, v), save=True)
            for flavour in FLAVOURS.get(cat, []):
                ProductVariant.objects.create(product=product, flavour=flavour)
            created += 1

        # Demo customers + reviews (fake data only)
        comments = [
            (5, 'Great quality', 'Mixes well, tastes great and I recovered faster. Will buy again!'),
            (4, 'Value for money', 'Good product at a fair price. Delivery was quick.'),
            (5, 'Highly recommend', 'Genuine product, sealed packing. Saw results within weeks.'),
            (3, 'Decent', 'Works fine but the flavour is a bit sweet for me.'),
            (4, 'Solid choice', 'No stomach issues and easy to use daily.'),
        ]
        users = []
        for n in range(1, 4):
            user, made = User.objects.get_or_create(username=f'demo{n}', defaults={'email': f'demo{n}@example.com'})
            if made:
                user.set_password('Demo@12345')
                user.save()
            users.append(user)
        products = list(Product.objects.all())
        if not Review.objects.exists():
            for product in products:
                for user in random.sample(users, random.randint(1, 3)):
                    rating, title, text = random.choice(comments)
                    Review.objects.create(product=product, user=user, rating=rating, title=title,
                                          comment=text, verified_purchase=True)

        now = timezone.now()
        Coupon.objects.get_or_create(code='WELCOME10', defaults={
            'discount_type': 'percent', 'value': 10, 'min_order': 499, 'max_discount': 300,
            'valid_to': now + timedelta(days=365)})
        Coupon.objects.get_or_create(code='FLAT200', defaults={
            'discount_type': 'flat', 'value': 200, 'min_order': 1999,
            'valid_to': now + timedelta(days=365)})

        self.stdout.write(self.style.SUCCESS(
            f'Done! {created} new products. Coupons: WELCOME10, FLAT200. '
            'Demo customers: demo1/demo2/demo3 (password Demo@12345).'))
