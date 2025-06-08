from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse

from products.models import Product, Category, SubCategory, Brand
from orders.models import Order, OrderItem
from users.models import UserProfile, Address
from payments.models import Payment
from reviews.models import Review
from .models import SalesReport, ProductViewLog, Notification, StockAlert

from products.forms import ProductForm, CategoryForm, SubCategoryForm, BrandForm

def is_admin(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'admin'

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Get overview data for the dashboard
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Order statistics
    total_orders = Order.objects.count()
    recent_orders = Order.objects.filter(created_at__date=today).count()
    
    # Revenue statistics
    total_revenue = Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_revenue = Payment.objects.filter(
        status='completed', 
        created_at__date__gte=thirty_days_ago
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Product statistics
    total_products = Product.objects.count()
    out_of_stock_products = Product.objects.filter(stock=0).count()
    
    # User statistics
    total_users = UserProfile.objects.filter(role='customer').count()
    new_users = UserProfile.objects.filter(
        role='customer', 
        user__date_joined__date__gte=thirty_days_ago
    ).count()
    
    # Orders by date (for chart)
    last_7_days = [today - timedelta(days=i) for i in range(7)]
    orders_by_day = []
    
    for day in last_7_days:
        order_count = Order.objects.filter(created_at__date=day).count()
        orders_by_day.append({
            'date': day.strftime('%d %b'),
            'count': order_count
        })
    
    # Top selling products
    top_products = OrderItem.objects.values(
        'product__id', 'product__title'
    ).annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:5]
    
    # Recent orders
    recent_orders_list = Order.objects.order_by('-created_at')[:5]
    
    context = {
        'total_orders': total_orders,
        'recent_orders': recent_orders,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'total_products': total_products,
        'out_of_stock_products': out_of_stock_products,
        'total_users': total_users,
        'new_users': new_users,
        'orders_by_day': orders_by_day,
        'top_products': top_products,
        'recent_orders_list': recent_orders_list,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_products(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    # Filter products based on query parameters
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    query = request.GET.get('q')
    stock_status = request.GET.get('stock')
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if brand_id:
        products = products.filter(brand_id=brand_id)
    
    if query:
        products = products.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(brand__name__icontains=query)
        )
    
    if stock_status:
        if stock_status == 'in_stock':
            products = products.filter(stock__gt=0)
        elif stock_status == 'out_of_stock':
            products = products.filter(stock=0)
    
    context = {
        'products': products,
        'categories': categories,
        'brands': brands,
        'selected_category': category_id,
        'selected_brand': brand_id,
        'query': query,
        'stock_status': stock_status,
    }
    
    return render(request, 'admin_dashboard/products.html', context)

@login_required
@user_passes_test(is_admin)
def admin_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    
    # Filter orders based on query parameters
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    query = request.GET.get('q')
    
    if status:
        orders = orders.filter(status=status)
    
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    
    if query:
        orders = orders.filter(
            Q(order_id__icontains=query) | 
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query)
        )
    
    context = {
        'orders': orders,
        'selected_status': status,
        'start_date': start_date,
        'end_date': end_date,
        'query': query,
    }
    
    return render(request, 'admin_dashboard/orders.html', context)

@login_required
@user_passes_test(is_admin)
def admin_users(request):
    users = UserProfile.objects.filter(role='customer').select_related('user')
    
    # Filter users based on query parameters
    query = request.GET.get('q')
    date_joined = request.GET.get('date_joined')
    
    if query:
        users = users.filter(
            Q(user__username__icontains=query) | 
            Q(user__email__icontains=query) |
            Q(phone__icontains=query)
        )
    
    if date_joined:
        if date_joined == 'today':
            users = users.filter(user__date_joined__date=timezone.now().date())
        elif date_joined == 'this_week':
            week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
            users = users.filter(user__date_joined__date__gte=week_start)
        elif date_joined == 'this_month':
            month_start = timezone.now().date().replace(day=1)
            users = users.filter(user__date_joined__date__gte=month_start)
    
    context = {
        'users': users,
        'query': query,
        'date_joined': date_joined,
    }
    
    return render(request, 'admin_dashboard/users.html', context)

@login_required
@user_passes_test(is_admin)
def admin_reports(request):
    reports = SalesReport.objects.all().order_by('-generated_at')
    
    context = {
        'reports': reports,
    }
    
    return render(request, 'admin_dashboard/reports.html', context)

@login_required
@user_passes_test(is_admin)
def sales_report(request):
    report_type = request.GET.get('type', 'monthly')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    today = timezone.now().date()
    
    if report_type == 'daily':
        if not start_date:
            start_date = today
        if not end_date:
            end_date = today
    elif report_type == 'weekly':
        if not start_date:
            start_date = today - timedelta(days=7)
        if not end_date:
            end_date = today
    elif report_type == 'monthly':
        if not start_date:
            start_date = today.replace(day=1)
        if not end_date:
            end_date = today
    elif report_type == 'yearly':
        if not start_date:
            start_date = today.replace(month=1, day=1)
        if not end_date:
            end_date = today
    
    # Get orders in the date range
    orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders = orders.count()
    average_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    # Get sales by category
    sales_by_category = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'product__category__name'
    ).annotate(
        total_sales=Sum('price'),
        count=Count('id')
    ).order_by('-total_sales')
    
    # Get sales by payment method
    sales_by_payment = Payment.objects.filter(
        order__in=orders
    ).values(
        'payment_method'
    ).annotate(
        total_sales=Sum('amount'),
        count=Count('id')
    ).order_by('-total_sales')
    
    context = {
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': total_sales,
        'total_orders': total_orders,
        'average_order_value': average_order_value,
        'sales_by_category': sales_by_category,
        'sales_by_payment': sales_by_payment,
        'orders': orders,
    }
    
    return render(request, 'admin_dashboard/sales_report.html', context)

@login_required
@user_passes_test(is_admin)
def product_report(request):
    product_id = request.GET.get('product_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    today = timezone.now().date()
    
    if not start_date:
        start_date = today - timedelta(days=30)
    if not end_date:
        end_date = today
    
    products = Product.objects.all()
    
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        
        # Get product views
        product_views = ProductViewLog.objects.filter(
            product=product,
            viewed_at__date__gte=start_date,
            viewed_at__date__lte=end_date
        ).count()
        
        # Get sales data
        sales_data = OrderItem.objects.filter(
            product=product,
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date
        ).aggregate(
            total_sales=Sum('price'),
            total_quantity=Sum('quantity')
        )
        
        total_sales = sales_data['total_sales'] or 0
        total_quantity = sales_data['total_quantity'] or 0
        
        # Get ratings data
        ratings_data = Review.objects.filter(
            product=product
        ).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )
        
        avg_rating = ratings_data['avg_rating'] or 0
        total_reviews = ratings_data['total_reviews'] or 0
        
        context = {
            'products': products,
            'product': product,
            'start_date': start_date,
            'end_date': end_date,
            'product_views': product_views,
            'total_sales': total_sales,
            'total_quantity': total_quantity,
            'avg_rating': avg_rating,
            'total_reviews': total_reviews,
        }
    else:
        # Get top products by sales
        top_products = OrderItem.objects.filter(
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date
        ).values(
            'product__id', 'product__title'
        ).annotate(
            total_sales=Sum('price'),
            total_quantity=Sum('quantity')
        ).order_by('-total_sales')[:10]
        
        context = {
            'products': products,
            'start_date': start_date,
            'end_date': end_date,
            'top_products': top_products,
        }
    
    return render(request, 'admin_dashboard/product_report.html', context)

@login_required
@user_passes_test(is_admin)
def admin_settings(request):
    return render(request, 'admin_dashboard/settings.html')

@login_required
@user_passes_test(is_admin)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('admin_products')
    else:
        form = ProductForm()
    
    context = {
        'form': form,
        'title': 'Add Product',
    }
    
    return render(request, 'admin_dashboard/product_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('admin_products')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'title': 'Edit Product',
        'product': product,
    }
    
    return render(request, 'admin_dashboard/product_form.html', context)

@login_required
@user_passes_test(is_admin)
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('admin_products')
    
    context = {
        'product': product,
    }
    
    return render(request, 'admin_dashboard/product_confirm_delete.html', context)

@login_required
@user_passes_test(is_admin)
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            messages.success(request, 'Category added successfully!')
            return redirect('admin_products')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'title': 'Add Category',
    }
    
    return render(request, 'admin_dashboard/category_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully!')
            return redirect('admin_products')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'title': 'Edit Category',
        'category': category,
    }
    
    return render(request, 'admin_dashboard/category_form.html', context)

@login_required
@user_passes_test(is_admin)
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('admin_products')
    
    context = {
        'category': category,
    }
    
    return render(request, 'admin_dashboard/category_confirm_delete.html', context)

@login_required
@user_passes_test(is_admin)
def add_subcategory(request):
    if request.method == 'POST':
        form = SubCategoryForm(request.POST, request.FILES)
        if form.is_valid():
            subcategory = form.save()
            messages.success(request, 'Subcategory added successfully!')
            return redirect('admin_products')
    else:
        form = SubCategoryForm()
    
    context = {
        'form': form,
        'title': 'Add Subcategory',
    }
    
    return render(request, 'admin_dashboard/subcategory_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_subcategory(request, subcategory_id):
    subcategory = get_object_or_404(SubCategory, id=subcategory_id)
    
    if request.method == 'POST':
        form = SubCategoryForm(request.POST, request.FILES, instance=subcategory)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subcategory updated successfully!')
            return redirect('admin_products')
    else:
        form = SubCategoryForm(instance=subcategory)
    
    context = {
        'form': form,
        'title': 'Edit Subcategory',
        'subcategory': subcategory,
    }
    
    return render(request, 'admin_dashboard/subcategory_form.html', context)

@login_required
@user_passes_test(is_admin)
def delete_subcategory(request, subcategory_id):
    subcategory = get_object_or_404(SubCategory, id=subcategory_id)
    
    if request.method == 'POST':
        subcategory.delete()
        messages.success(request, 'Subcategory deleted successfully!')
        return redirect('admin_products')
    
    context = {
        'subcategory': subcategory,
    }
    
    return render(request, 'admin_dashboard/subcategory_confirm_delete.html', context)

@login_required
@user_passes_test(is_admin)
def add_brand(request):
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES)
        if form.is_valid():
            brand = form.save()
            messages.success(request, 'Brand added successfully!')
            return redirect('admin_products')
    else:
        form = BrandForm()
    
    context = {
        'form': form,
        'title': 'Add Brand',
    }
    
    return render(request, 'admin_dashboard/brand_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    
    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, 'Brand updated successfully!')
            return redirect('admin_products')
    else:
        form = BrandForm(instance=brand)
    
    context = {
        'form': form,
        'title': 'Edit Brand',
        'brand': brand,
    }
    
    return render(request, 'admin_dashboard/brand_form.html', context)

@login_required
@user_passes_test(is_admin)
def delete_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    
    if request.method == 'POST':
        brand.delete()
        messages.success(request, 'Brand deleted successfully!')
        return redirect('admin_products')
    
    context = {
        'brand': brand,
    }
    
    return render(request, 'admin_dashboard/brand_confirm_delete.html', context)
