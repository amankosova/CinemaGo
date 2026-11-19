
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label=_("Email"))

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class ProfileEditForm(forms.ModelForm):
    email = forms.EmailField(
        label=_("Email"),
        required=True
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput
    )