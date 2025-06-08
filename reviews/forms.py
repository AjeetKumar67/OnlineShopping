from django import forms
from .models import Review, ReviewImage

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['title', 'rating', 'comment']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Give your review a title'
            }),
            'rating': forms.Select(attrs={
                'class': 'form-select'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience with this product'
            })
        }
    
    # Use a field that properly supports multiple files
    images = forms.ImageField(
        required=False,
        error_messages={'invalid': "Image files only"},
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check if user has already reviewed this product
        if self.user and self.product and not self.instance.pk:
            existing_review = Review.objects.filter(user=self.user, product=self.product).exists()
            if existing_review:
                raise forms.ValidationError("You have already reviewed this product. You can edit your existing review.")
        
        return cleaned_data
    
    def save(self, commit=True):
        review = super().save(commit=False)
        
        if self.user:
            review.user = self.user
        if self.product:
            review.product = self.product
        
        if commit:
            review.save()
            
            # Handle multiple image uploads
            images = self.files.getlist('images')
            for image in images:
                ReviewImage.objects.create(review=review, image=image)
        
        return review
