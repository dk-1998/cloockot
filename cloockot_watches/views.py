from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .forms import RegistracijaForm, PrijavaForm
import json
from .models import Korisnik, Porudzbina
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)

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

# Checkout - poboljšana verzija
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
            email_context = {
                'order_id': porudzbina.id,
                'order_date': porudzbina.datum.strftime('%d.%m.%Y %H:%M'),
                'customer': {
                    'username': korisnik.korisnicko_ime,
                    'email': korisnik.email,
                    'ime': korisnik.ime,
                    'prezime': korisnik.prezime,
                },
                'items': artikli_lista,
                'total': ukupno,
            }
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>🚀 Nova porudžbina #{porudzbina.id}</h2>
                <p><strong>Datum:</strong> {email_context['order_date']}</p>
                <p><strong>Korisnik:</strong> {korisnik.korisnicko_ime} ({korisnik.ime} {korisnik.prezime})</p>
                <p><strong>Email:</strong> {korisnik.email}</p>
                <p><strong>Telefon:</strong> {korisnik.telefon}</p>
                
                <h3>Stavke porudžbine:</h3>
                <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
                    <thead style="background: #f5f5f5;">
                        <tr>
                            <th>Proizvod</th>
                            <th>Brend</th>
                            <th>Cena</th>
                            <th>Količina</th>
                            <th>Ukupno</th>
                        </tr>
                    </thead>
                    <tbody>
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
                    </tbody>
                    <tfoot>
                        <tr style="background: #f5f5f5; font-weight: bold;">
                            <td colspan="4" style="text-align: right;">UKUPNO:</td>
                            <td>{ukupno:,} RSD</td>
                        </tr>
                    </tfoot>
                </table>
                <hr>
                <p><em>Porudžbina je automatski sačuvana u sistemu.</em></p>
                <p>Hvala vam na poverenju!</p>
            </body>
            </html>
            """
            
            text_content = strip_tags(html_content)
            subject = f'🚀 Nova porudžbina #{porudzbina.id} - {korisnik.korisnicko_ime}'
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['cloockot@gmail.com'],
                reply_to=[korisnik.email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)
            logger.info(f"Email porudžbine #{porudzbina.id} poslat uspešno")
            
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


# Kontakt forma - slanje emaila (sa smtplib i dužim timeout-om)
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

        # Test konekcije pre slanja
        import smtplib
        try:
            server = smtplib.SMTP('smtp-relay.brevo.com', 587, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            msg = MIMEMultipart('mixed')
            msg['Subject'] = f'Kontakt poruka od {ime_korisnika}'
            msg['From'] = 'cloockot@gmail.com'
            msg['To'] = 'cloockot@gmail.com'
            msg['Reply-To'] = email_korisnika
            
            tekst = f"Od: {ime_korisnika}\nEmail: {email_korisnika}\nTelefon: {telefon}\n\nPoruka:\n{poruka}"
            msg.attach(MIMEText(tekst, 'plain'))
            
            server.sendmail('cloockot@gmail.com', ['cloockot@gmail.com'], msg.as_string())
            server.quit()
            
            return JsonResponse({'success': True, 'message': 'Poruka je uspešno poslata!'})
            
        except smtplib.SMTPAuthenticationError as e:
            return JsonResponse({'error': f'Gmail autentifikacija neuspešna: {str(e)}'}, status=500)
        except smtplib.SMTPConnectError as e:
            return JsonResponse({'error': f'Ne mogu da se povežem na Gmail: {str(e)}'}, status=500)
        except smtplib.SMTPException as e:
            return JsonResponse({'error': f'SMTP greška: {str(e)}'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': f'Greška: {str(e)}'}, status=500)