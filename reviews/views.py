from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q

from .forms import ReviewForm
from .models import Review, ReviewVote
from products.models import Product

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user has purchased the product
    has_purchased = product.has_been_purchased_by(request.user)
    
    # Check if user already has a review for this product
    existing_review = Review.objects.filter(user=request.user, product=product).first()
    if existing_review:
        return redirect('edit_review', review_id=existing_review.id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, user=request.user, product=product)
        if form.is_valid():
            review = form.save()
            
            # If user has purchased the product, mark as verified purchase
            if has_purchased:
                review.is_verified_purchase = True
                review.save()
                
            messages.success(request, "Your review has been submitted successfully!")
            return redirect('product_detail', slug=product.slug)
    else:
        form = ReviewForm(user=request.user, product=product)
    
    context = {
        'form': form,
        'product': product,
        'has_purchased': has_purchased,
    }
    return render(request, 'reviews/add_review.html', context)

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product = review.product
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, instance=review, user=request.user, product=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Your review has been updated successfully!")
            return redirect('product_detail', slug=product.slug)
    else:
        form = ReviewForm(instance=review, user=request.user, product=product)
    
    context = {
        'form': form,
        'product': product,
        'review': review,
        'is_edit': True,
    }
    return render(request, 'reviews/add_review.html', context)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product_slug = review.product.slug
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, "Your review has been deleted successfully!")
        return redirect('product_detail', slug=product_slug)
    
    context = {
        'review': review,
    }
    return render(request, 'reviews/delete_review.html', context)

def product_reviews(request, slug):
    product = get_object_or_404(Product, slug=slug)
    
    # Filter by rating
    rating_filter = request.GET.get('rating')
    if rating_filter and rating_filter.isdigit():
        reviews = Review.objects.filter(product=product, rating=int(rating_filter))
    else:
        reviews = Review.objects.filter(product=product)
    
    # Filter by verified purchases
    verified_only = request.GET.get('verified') == '1'
    if verified_only:
        reviews = reviews.filter(is_verified_purchase=True)
    
    # Filter by reviews with images
    with_images = request.GET.get('with_images') == '1'
    if with_images:
        reviews = reviews.filter(images__isnull=False).distinct()
    
    # Sort reviews
    sort_by = request.GET.get('sort', 'recent')
    if sort_by == 'recent':
        reviews = reviews.order_by('-created_at')
    elif sort_by == 'helpful':
        reviews = reviews.annotate(upvote_count=Count('votes', filter=Q(votes__vote='upvote'))).order_by('-upvote_count')
    elif sort_by == 'high_rating':
        reviews = reviews.order_by('-rating')
    elif sort_by == 'low_rating':
        reviews = reviews.order_by('rating')
    
    # Paginate results
    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get user's votes if logged in
    user_votes = {}
    if request.user.is_authenticated:
        user_votes = {
            vote.review_id: vote.vote 
            for vote in ReviewVote.objects.filter(user=request.user, review__product=product)
        }
    
    context = {
        'product': product,
        'page_obj': page_obj,
        'user_votes': user_votes,
        'review_count': reviews.count(),
        'filter_params': request.GET.copy(),
    }
    return render(request, 'reviews/product_reviews.html', context)

@login_required
def vote_review(request):
    if request.method == 'POST' and request.is_ajax():
        review_id = request.POST.get('review_id')
        vote_type = request.POST.get('vote_type')
        
        if vote_type not in ['upvote', 'downvote']:
            return JsonResponse({'status': 'error', 'message': 'Invalid vote type'})
        
        try:
            review = Review.objects.get(id=review_id)
            
            # Can't vote on your own review
            if review.user == request.user:
                return JsonResponse({'status': 'error', 'message': 'You cannot vote on your own review'})
            
            # Get or create vote
            vote, created = ReviewVote.objects.get_or_create(
                user=request.user,
                review=review,
                defaults={'vote': vote_type}
            )
            
            # If vote exists and matches requested type, remove the vote
            if not created and vote.vote == vote_type:
                vote.delete()
                action = 'removed'
            # If vote exists but is different type, update it
            elif not created:
                vote.vote = vote_type
                vote.save()
                action = 'updated'
            # New vote was created
            else:
                action = 'added'
            
            # Get updated vote counts
            upvotes = ReviewVote.objects.filter(review=review, vote='upvote').count()
            downvotes = ReviewVote.objects.filter(review=review, vote='downvote').count()
            
            return JsonResponse({
                'status': 'success',
                'action': action,
                'upvotes': upvotes,
                'downvotes': downvotes
            })
            
        except Review.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Review not found'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})
