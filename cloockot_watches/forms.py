from django import forms
from .models import Korisnik

# ======== Registracija ========
class RegistracijaForm(forms.ModelForm):
    lozinka = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Korisnik
        fields = ['ime', 'prezime', 'korisnicko_ime', 'email', 'telefon', 'lozinka']

# ======== Prijava ========
class PrijavaForm(forms.Form):
    korisnicko_ime = forms.CharField(max_length=30)
    lozinka = forms.CharField(widget=forms.PasswordInput)
