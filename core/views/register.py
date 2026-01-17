from django.contrib.auth import get_user_model, login
from django.views.generic.edit import FormView
from django import forms

User = get_user_model()

class UserRegistrationForm(forms.Form):
    email = forms.EmailField(required=True, label="Email")
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Mot de passe"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Confirmer le mot de passe"
    )
    first_name = forms.CharField(required=True, label="Prénom")
    last_name = forms.CharField(required=True, label="Nom")

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email déjà utilisé.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password:
            raise forms.ValidationError("Le mot de passe est requis.")

        if len(password) < 8 or not any(char.isdigit() for char in password) or not any(char.isupper() for char in password):
            raise forms.ValidationError("Le mot de passe doit contenir au moins 8 caractères, une lettre majuscule et un chiffre.")

        return password

class RegisterFormView(FormView):
    template_name = "registration/register.html"
    form_class = UserRegistrationForm
    success_url = "/auth/me/"

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        first_name = form.cleaned_data["first_name"]
        last_name = form.cleaned_data["last_name"]

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        login(self.request, user)

        return super().form_valid(form)
