from django.db import models
from django.contrib.auth.models import User
from products.models import Product
from orders.models import Order

class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=100)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified_purchase = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.rating} stars for {self.product.title} by {self.user.username}"
    
    def save(self, *args, **kwargs):
        if self.order and self.order.user == self.user and self.order.order_status == 'delivered':
            self.is_verified_purchase = True
        super().save(*args, **kwargs)

class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='reviews')
    
    def __str__(self):
        return f"Image for {self.review}"

class ReviewVote(models.Model):
    VOTE_CHOICES = (
        ('upvote', 'Upvote'),
        ('downvote', 'Downvote'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='votes')
    vote = models.CharField(max_length=15, choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'review')

    def __str__(self):
        return f"{self.user.username} found review {self.review.id} {self.vote}"
