from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .forms import RegistracijaForm, PrijavaForm
import json
from .models import Korisnik, Porudzbina
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
import logging
from django.core.mail import EmailMessage
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os

logger = logging.getLogger(__name__)

@csrf_exempt
def upload_slika_api(request):
    """Privremeno prima sliku i vraća URL"""
    if request.method == 'POST' and request.FILES.get('slika'):
        slika = request.FILES['slika']
        
        # Sačuvaj sliku u media/temp_uploads/
        file_path = default_storage.save(f'temp_uploads/{slika.name}', ContentFile(slika.read()))
        file_url = request.build_absolute_uri(default_storage.url(file_path))
        
        return JsonResponse({
            'success': True, 
            'url': file_url,
            'message': 'Slika je sačuvana'
        })
    
    return JsonResponse({'success': False, 'error': 'Nema slike'}, status=400)
# ======== OSNOVNE STRANICE ========
def index(request): 
    return render(request, 'cloockot_watches/index.html')

def onama(request): 
    return render(request, 'cloockot_watches/onama.html')

def satovi(request):
    ulogovan = 'korisnicko_ime' in request.session
    context = {
        'ulogovan': ulogovan,
    }
    return render(request, 'cloockot_watches/satovi.html', context)

def kontakt(request): 
    return render(request, 'cloockot_watches/kontakt.html')


# ======== REGISTRACIJA ========
def registracija(request):
    if request.method == 'POST':
        form = RegistracijaForm(request.POST)
        if form.is_valid():
            korisnik = form.save(commit=False)
            korisnik.lozinka = make_password(form.cleaned_data['lozinka'])
            korisnik.save()
            messages.success(request, f"Uspešno ste se registrovali kao {korisnik.korisnicko_ime}! Sada se možete prijaviti.")
            return redirect('prijava')
    else:
        form = RegistracijaForm()
    
    return render(request, 'cloockot_watches/registracija.html', {'form': form})


# ======== PRIJAVA ========
def prijava(request):
    if request.method == 'POST':
        form = PrijavaForm(request.POST)
        if form.is_valid():
            korisnicko_ime = form.cleaned_data['korisnicko_ime']
            lozinka = form.cleaned_data['lozinka']

            try:
                korisnik = Korisnik.objects.get(korisnicko_ime=korisnicko_ime)
                if check_password(lozinka, korisnik.lozinka):
                    request.session['korisnik_id'] = korisnik.id
                    request.session['korisnicko_ime'] = korisnik.korisnicko_ime
                    messages.success(request, f"Dobrodošli {korisnik.korisnicko_ime}!")
                    return redirect('satovi')
                else:
                    messages.error(request, "Neispravna lozinka.")
            except Korisnik.DoesNotExist:
                messages.error(request, "Korisnik ne postoji.")
    else:
        form = PrijavaForm()

    return render(request, 'cloockot_watches/prijava.html', {'form': form})


# ======== ODJAVA ========
def odjava(request):
    request.session.flush()
    return redirect('index')


# ======== CHECKOUT ========
@require_http_methods(["POST"])
@ensure_csrf_cookie
def checkout(request):
    if not request.session.get('korisnicko_ime'):
        return JsonResponse({'error': 'Morate biti ulogovani da biste nastavili sa plaćanjem.'}, status=403)

    try:
        data = json.loads(request.body)
        korpa = data.get('cart', [])
        
        if not korpa:
            return JsonResponse({'error': 'Korpa je prazna.'}, status=400)
        
        korisnicko_ime = request.session['korisnicko_ime']
        try:
            korisnik = Korisnik.objects.get(korisnicko_ime=korisnicko_ime)
        except Korisnik.DoesNotExist:
            return JsonResponse({'error': 'Korisnik ne postoji.'}, status=400)
        
        ukupno = 0
        artikli_lista = []
        
        for artikal in korpa:
            cena = int(artikal['price'])
            kolicina = int(artikal.get('quantity', 1))
            ukupno += cena * kolicina
            
            artikli_lista.append({
                'id': artikal['id'],
                'naziv': artikal['title'],
                'brend': artikal.get('brand', ''),
                'cena': cena,
                'kolicina': kolicina,
                'ukupno_za_artikal': cena * kolicina
            })
        
        # Kreiraj porudžbinu u bazi
        porudzbina = Porudzbina.objects.create(
            korisnik=korisnik,
            artikli=artikli_lista,
            ukupno=ukupno
        )
        
        logger.info(f"Porudžbina #{porudzbina.id} kreirana - Korisnik: {korisnicko_ime}, Ukupno: {ukupno} RSD")
        
        return JsonResponse({
            'success': True, 
            'message': 'Porudžbina je uspešno kreirana.',
            'order_id': porudzbina.id,
            'total': ukupno
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Neispravan format podataka.'}, status=400)
    except Exception as e:
        logger.error(f"Greška u checkout: {str(e)}")
        return JsonResponse({'error': f'Došlo je do greške: {str(e)}'}, status=400)


# ======== KONTAKT FORMA – SLANJE EMAIL (RESEND) ========
@require_http_methods(["POST"])
@ensure_csrf_cookie
def posalji_kontakt(request):
    """Šalje email iz kontakt forme preko Resend SMTP"""
    try:
        email_korisnika = request.POST.get('email', '').strip()
        ime = request.POST.get('ime', '').strip()
        telefon = request.POST.get('telefon', '').strip()
        poruka = request.POST.get('poruka', '').strip()
        
        if not email_korisnika:
            return JsonResponse({'success': False, 'error': 'Email adresa je obavezna.'})
        if not poruka:
            return JsonResponse({'success': False, 'error': 'Poruka je obavezna.'})
        
        subject = f"Kontakt poruka sa Cloockot sajta - od {email_korisnika}"
        
        body = f"""
Nova poruka sa kontakt forme:

Ime: {ime if ime else 'Nije navedeno'}
Email: {email_korisnika}
Telefon: {telefon if telefon else 'Nije naveden'}

Poruka:
{poruka}
        """
        
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email='kontakt@cloockot.com',     # Sa tvog verifikovanog domena
            to=['cloockot2026@gmail.com'],          # Gde stiže poruka (tvoj Gmail)
            reply_to=[email_korisnika]              # Kada odgovoriš, ide korisniku
        )
        
        # Dodaj sliku ako postoji
        if request.FILES.get('slika'):
            slika = request.FILES['slika']
            email.attach(slika.name, slika.read(), slika.content_type)
        
        email.send(fail_silently=False)
        
        logger.info(f"Kontakt email poslat od {email_korisnika} na cloockot2026@gmail.com")
        
        return JsonResponse({'success': True, 'message': 'Poruka je uspešno poslata.'})
        
    except Exception as e:
        logger.error(f"Greška pri slanju kontakt emaila: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Greška: {str(e)}'})