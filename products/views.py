from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Avg, Count, Sum
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Product, Category, SubCategory, Brand, ProductImage, ProductViewLog
from reviews.models import Review
from wishlist.models import Wishlist
from cart.models import Cart, CartItem

def home(request):
    """
    Home page view showing featured products, deals of the day, and top categories.
    """
    featured_products = Product.objects.filter(is_featured=True, is_available=True)[:8]
    new_arrivals = Product.objects.filter(is_available=True).order_by('-created_at')[:8]
    bestsellers = Product.objects.filter(is_available=True, is_featured=True).order_by('-created_at')[:8]
    top_rated = Product.objects.filter(is_available=True).annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')[:8]
    
    # Change is_active to filter by pk instead since it might not exist
    categories = Category.objects.all()[:6]
    
    context = {
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'bestsellers': bestsellers,
        'top_rated': top_rated,
        'categories': categories,
    }
    return render(request, 'home.html', context)

def product_search(request):
    """
    Search products by query, with filters for category, brand, price range.
    """
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    brand_id = request.GET.get('brand', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort = request.GET.get('sort', 'relevance')
    
    products = Product.objects.filter(is_available=True)
    
    # Apply search query
    if query:
        products = products.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(brand__name__icontains=query)
        )
    
    # Apply filters
    if category_id:
        products = products.filter(category_id=category_id)
    
    if brand_id:
        products = products.filter(brand_id=brand_id)
    
    # Apply price range filter
    if min_price:
        products = products.filter(price__gte=min_price)
    
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Apply sorting
    if sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')
    elif sort == 'popularity':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    
    # Get filter options
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'query': query,
        'categories': categories,
        'brands': brands,
        'selected_category': category_id,
        'selected_brand': brand_id,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
    }
    
    return render(request, 'products/product_search.html', context)

def category_products(request, category_slug):
    """
    Display all products in a specific category.
    """
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    subcategory_slug = request.GET.get('subcategory')
    
    if subcategory_slug:
        subcategory = get_object_or_404(SubCategory, slug=subcategory_slug, category=category)
        products = Product.objects.filter(subcategory=subcategory, is_available=True)
        title = f"{subcategory.name} in {category.name}"
    else:
        products = Product.objects.filter(category=category, is_available=True)
        title = category.name
    
    # Filter by brand
    brand_slug = request.GET.get('brand')
    if brand_slug:
        brand = get_object_or_404(Brand, slug=brand_slug)
        products = products.filter(brand=brand)
        title = f"{brand.name} {title}"
    
    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(current_price__gte=min_price)
    if max_price:
        products = products.filter(current_price__lte=max_price)
    
    # Sort products
    sort_by = request.GET.get('sort')
    if sort_by == 'price_low':
        products = products.order_by('current_price')
    elif sort_by == 'price_high':
        products = products.order_by('-current_price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    
    # Paginate results
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)
    
    # Get all subcategories for the sidebar
    subcategories = SubCategory.objects.filter(category=category)
    
    # Get brands for the sidebar
    brands = Brand.objects.filter(
        id__in=Product.objects.filter(category=category).values_list('brand', flat=True).distinct()
    )
    
    context = {
        'category': category,
        'subcategories': subcategories,
        'brands': brands,
        'products': products_page,
        'title': title,
        'product_count': products.count(),
    }
    return render(request, 'products/category_products.html', context)

def product_detail(request, product_slug):
    """
    Display detailed information about a specific product.
    """
    product = get_object_or_404(Product, slug=product_slug, is_available=True)
    images = ProductImage.objects.filter(product=product)
    related_products = Product.objects.filter(
        category=product.category, 
        is_available=True
    ).exclude(id=product.id)[:6]
    
    # Log product view
    if request.user.is_authenticated:
        ProductViewLog.objects.create(
            product=product,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    else:
        ProductViewLog.objects.create(
            product=product,
            ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    
    # Check if product is in user's wishlist
    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
    
    context = {
        'product': product,
        'images': images,
        'related_products': related_products,
        'categories': Category.objects.all(),  # For navbar
        'is_in_wishlist': is_in_wishlist,
    }
    
    return render(request, 'products/product_detail.html', context)

def brand_products(request, brand_slug):
    """
    Display all products for a specific brand.
    """
    brand = get_object_or_404(Brand, slug=brand_slug)
    products = Product.objects.filter(brand=brand, is_available=True)
    
    # Filter by category
    category_slug = request.GET.get('category')
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    # Sort products
    sort_by = request.GET.get('sort')
    if sort_by == 'price_low':
        products = products.order_by('current_price')
    elif sort_by == 'price_high':
        products = products.order_by('-current_price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    
    # Paginate results
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)
    
    # Get categories for the sidebar
    categories = Category.objects.filter(
        id__in=products.values_list('category', flat=True).distinct()
    )
    
    context = {
        'brand': brand,
        'categories': categories,
        'products': products_page,
        'product_count': products.count(),
    }
    return render(request, 'products/brand_products.html', context)

def search_products(request):
    """
    Search for products by query.
    """
    query = request.GET.get('q', '')
    if not query:
        return redirect('home')
    
    products = Product.objects.filter(
        Q(title__icontains=query) | 
        Q(description__icontains=query) |
        Q(category__name__icontains=query) |
        Q(subcategory__name__icontains=query) |
        Q(brand__name__icontains=query),
        is_available=True
    ).distinct()
    
    # Sort products
    sort_by = request.GET.get('sort')
    if sort_by == 'price_low':
        products = products.order_by('current_price')
    elif sort_by == 'price_high':
        products = products.order_by('-current_price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    
    # Paginate results
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)
    
    context = {
        'query': query,
        'products': products_page,
        'product_count': products.count(),
    }
    return render(request, 'products/search_results.html', context)

@login_required
def add_to_cart(request):
    """
    Add a product to the user's cart.
    """
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id, is_available=True)
            
            # Check if product is in stock
            if product.stock < quantity:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Only {product.stock} items available in stock.'
                })
            
            # Get or create cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Check if item already in cart
            try:
                cart_item = CartItem.objects.get(cart=cart, product=product)
                cart_item.quantity += quantity
                cart_item.save()
            except CartItem.DoesNotExist:
                cart_item = CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=quantity
                )
            
            # Count total items in cart
            cart_count = CartItem.objects.filter(cart=cart).aggregate(
                total_items=Sum('quantity')
            )['total_items'] or 0
            
            return JsonResponse({
                'status': 'success',
                'message': 'Product added to cart successfully!',
                'cart_count': cart_count
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Product not found or unavailable.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })

@login_required
def add_to_wishlist(request):
    """
    Add a product to the user's wishlist.
    """
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id)
            
            # Check if product already in wishlist
            wishlist_item, created = Wishlist.objects.get_or_create(
                user=request.user,
                product=product
            )
            
            if created:
                status = 'success'
                message = 'Product added to wishlist successfully!'
            else:
                status = 'info'
                message = 'Product already in your wishlist.'
                
            return JsonResponse({
                'status': status,
                'message': message
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Product not found.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })

def get_subcategories(request):
    """
    Ajax view to get subcategories for a given category.
    Used in product forms.
    """
    category_id = request.GET.get('category_id')
    subcategories = {}
    
    if category_id:
        category_subcategories = SubCategory.objects.filter(category_id=category_id)
        subcategories = {subcategory.id: subcategory.name for subcategory in category_subcategories}
    
    return JsonResponse(subcategories)
