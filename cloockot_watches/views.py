from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .forms import RegistracijaForm, PrijavaForm
import json
from .models import Korisnik, Porudzbina
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
import logging
import os
import requests

logger = logging.getLogger(__name__)

# Funkcija za slanje emaila preko Brevo API-ja (jednostavnija verzija)
def send_brevo_email(to_email, to_name, subject, html_content, reply_to_email=None, reply_to_name=None):
    api_key = os.environ.get('BREVO_API_KEY', '')
    
    if not api_key:
        logger.error("BREVO_API_KEY nije podešen")
        return False
    
    url = "https://api.brevo.com/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key
    }
    
    payload = {
        "sender": {
            "name": "Cloockot Watches",
            "email": "cloockot@gmail.com"
        },
        "to": [
            {
                "email": to_email,
                "name": to_name
            }
        ],
        "subject": subject,
        "htmlContent": html_content
    }
    
    if reply_to_email:
        payload["replyTo"] = {
            "email": reply_to_email,
            "name": reply_to_name if reply_to_name else reply_to_email
        }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Email poslat uspešno. Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Greška pri slanju emaila: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response body: {e.response.text}")
        return False

# Osnovne stranice
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

# Registracija
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

# Prijava
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

# Odjava
def odjava(request):
    request.session.flush()
    return redirect('index')

# Checkout
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
        
        # Kreiraj porudžbinu
        porudzbina = Porudzbina.objects.create(
            korisnik=korisnik,
            artikli=artikli_lista,
            ukupno=ukupno
        )
        
        # Slanje email potvrde
        try:
            # Jednostavan HTML za porudžbinu
            html_content = f"""
            <h2>Nova porudžbina #{porudzbina.id}</h2>
            <p><strong>Datum:</strong> {porudzbina.datum.strftime('%d.%m.%Y %H:%M')}</p>
            <p><strong>Korisnik:</strong> {korisnik.ime} {korisnik.prezime} ({korisnik.korisnicko_ime})</p>
            <p><strong>Email:</strong> {korisnik.email}</p>
            <p><strong>Telefon:</strong> {korisnik.telefon}</p>
            
            <h3>Stavke porudžbine:</h3>
            <table border="1" cellpadding="5">
                <tr><th>Proizvod</th><th>Brend</th><th>Cena</th><th>Kol.</th><th>Ukupno</th></tr>
            """
            
            for item in artikli_lista:
                html_content += f"""
                <tr>
                    <td>{item['naziv']}</td>
                    <td>{item['brend']}</td>
                    <td>{item['cena']:,} RSD</td>
                    <td>{item['kolicina']}</td>
                    <td>{item['ukupno_za_artikal']:,} RSD</td>
                </tr>
                """
            
            html_content += f"""
            </table>
            <h3>UKUPNO: {ukupno:,} RSD</h3>
            <p>Hvala na porudžbini!</p>
            """
            
            send_brevo_email(
                to_email="cloockot@gmail.com",
                to_name="Cloockot",
                subject=f"Nova porudžbina #{porudzbina.id} - {korisnik.korisnicko_ime}",
                html_content=html_content,
                reply_to_email=korisnik.email,
                reply_to_name=f"{korisnik.ime} {korisnik.prezime}"
            )
            
        except Exception as e:
            logger.error(f"Greška pri slanju emaila za porudžbinu #{porudzbina.id}: {e}")
        
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


# Kontakt forma
@require_http_methods(["POST"])
@ensure_csrf_cookie
def posalji_email(request):
    try:
        if request.session.get('korisnicko_ime'):
            try:
                korisnik = Korisnik.objects.get(korisnicko_ime=request.session['korisnicko_ime'])
                email_korisnika = korisnik.email
                ime_korisnika = f"{korisnik.ime} {korisnik.prezime}"
            except Korisnik.DoesNotExist:
                email_korisnika = request.POST.get('email', '')
                ime_korisnika = email_korisnika
        else:
            email_korisnika = request.POST.get('email', '')
            ime_korisnika = email_korisnika

        telefon = request.POST.get('telefon', '')
        poruka = request.POST.get('poruka', '')

        if not email_korisnika:
            return JsonResponse({'error': 'Email adresa je obavezna.'}, status=400)
        if not poruka:
            return JsonResponse({'error': 'Poruka je obavezna.'}, status=400)

        # Jednostavan HTML za kontakt poruku
        html_content = f"""
        <h2>Nova kontakt poruka</h2>
        <p><strong>Od:</strong> {ime_korisnika}</p>
        <p><strong>Email:</strong> {email_korisnika}</p>
        <p><strong>Telefon:</strong> {telefon if telefon else 'Nije naveden'}</p>
        <hr>
        <h3>Poruka:</h3>
        <p>{poruka}</p>
        <hr>
        <p><em>Poslato sa Cloockot.com kontakt forme</em></p>
        """
        
        success = send_brevo_email(
            to_email="cloockot@gmail.com",
            to_name="Cloockot",
            subject=f"Kontakt poruka od {ime_korisnika}",
            html_content=html_content,
            reply_to_email=email_korisnika,
            reply_to_name=ime_korisnika
        )
        
        if success:
            return JsonResponse({'success': True, 'message': 'Poruka je uspešno poslata!'})
        else:
            return JsonResponse({'error': 'Greška pri slanju emaila. Proverite API ključ.'}, status=500)
            
    except Exception as e:
        logger.error(f"Greška u posalji_email: {e}")
        return JsonResponse({'error': f'Došlo je do greške: {str(e)}'}, status=500)