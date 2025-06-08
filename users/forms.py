from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, Address

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=15, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

class ProfileUpdateForm(forms.ModelForm):
    phone = forms.CharField(max_length=15, required=False)
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'profile_image']

class AddressForm(forms.ModelForm):
    set_default = forms.BooleanField(required=False, initial=False, 
                                     label='Set as default address')
    
    class Meta:
        model = Address
        fields = ['address_line1', 'address_line2', 'city', 'state', 'pincode', 'country']
        widgets = {
            'address_line1': forms.TextInput(attrs={'placeholder': 'House No., Building Name'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Area, Street, Sector, Village'}),
        }
