from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .forms import RegistracijaForm, PrijavaForm
import json
from .models import Korisnik, Porudzbina
from django.shortcuts import redirect
from django.core.mail import EmailMultiAlternatives
from django.utils.html import format_html
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMessage
from django.core.files.images import get_image_dimensions
from email.mime.image import MIMEImage
from django.conf import settings

from django.http import JsonResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from email.mime.image import MIMEImage
import logging
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

@csrf_exempt
def posalji_email(request):
    if request.method == "POST":
        try:
            # Ako je korisnik ulogovan
            if request.session.get('korisnik_id'):
                try:
                    korisnik = Korisnik.objects.get(id=request.session['korisnik_id'])
                    email = korisnik.email
                except Korisnik.DoesNotExist:
                    return JsonResponse(
                        {'error': 'Korisnik nije pronađen.'},
                        status=400
                    )
            else:
                email = request.POST.get("email")
                if not email:
                    return JsonResponse(
                        {'error': 'Email je obavezan za neulogovane korisnike.'},
                        status=400
                    )

            telefon = request.POST.get("telefon", "")
            poruka = request.POST.get("poruka", "")
            slika = request.FILES.get("slika")

            if not poruka:
                return JsonResponse(
                    {'error': 'Poruka je obavezno polje.'},
                    status=400
                )

            subject = "Upit sa Cloockot sajta"
            
            # Tekstualna verzija (plain text)
            body_text = f"""
Email pošiljaoca: {email}
Telefon: {telefon}
Poruka: {poruka}
            """
            
            # HTML verzija
            body_html = f"""
            <html>
            <body>
                <h2>Nov upit sa Cloockot sajta</h2>
                <p><strong>Email pošiljaoca:</strong> {email}</p>
                <p><strong>Telefon:</strong> {telefon}</p>
                <p><strong>Poruka:</strong><br>{poruka.replace(chr(10), '<br>')}</p>
            </body>
            </html>
            """

            # Kreiraj email poruku
            msg = EmailMultiAlternatives(
                subject=subject,
                body=body_text,
                from_email=settings.EMAIL_HOST_USER,
                to=['cloockot@gmail.com'],  # Proverite da li je ova adresa ispravna
                reply_to=[email],
            )
            
            # Dodaj HTML verziju
            msg.attach_alternative(body_html, "text/html")

            # Ako postoji slika, dodaj je
            if slika:
                # Proveri veličinu slike (maks 5MB)
                if slika.size > 5 * 1024 * 1024:
                    return JsonResponse(
                        {'error': 'Slika je prevelika. Maksimalna veličina je 5MB.'},
                        status=400
                    )
                
                # Dodaj sliku kao attachment sa inline prikazom
                try:
                    img_data = slika.read()
                    img = MIMEImage(img_data)
                    img.add_header('Content-ID', '<attachment1>')
                    img.add_header('Content-Disposition', 'attachment', filename=slika.name)
                    msg.attach(img)
                    
                    # Dodaj referencu slike u HTML (opciono)
                    body_html_with_img = body_html.replace('</body>', f'<p><strong>Priložena slika:</strong> {slika.name}</p></body>')
                    msg.attach_alternative(body_html_with_img, "text/html")
                    
                except Exception as img_error:
                    logger.error(f"Greška sa slikom: {str(img_error)}")
                    # Nastavi bez slike

            # Pokušaj poslati email
            try:
                msg.send(fail_silently=False)
                logger.info(f"Email uspešno poslat od: {email}")
                return JsonResponse({'success': True, 'message': 'Email je uspešno poslat.'})
                
            except Exception as email_error:
                logger.error(f"Greška pri slanju emaila: {str(email_error)}")
                return JsonResponse(
                    {'error': f'Greška pri slanju emaila: {str(email_error)}'},
                    status=500
                )

        except Exception as e:
            logger.error(f"Opšta greška: {str(e)}")
            return JsonResponse(
                {'error': f'Došlo je do greške: {str(e)}'},
                status=500
            )

    return JsonResponse({'error': 'Metoda nije dozvoljena.'}, status=405)

# Dodajte u views.py

def test_email(request):
    try:
        send_mail(
            'Test email',
            'Ovo je test poruka.',
            settings.EMAIL_HOST_USER,
            ['cloockot@gmail.com'],  # Vaša email adresa
            fail_silently=False,
        )
        return JsonResponse({'success': True, 'message': 'Test email je poslat!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
# Osnovne stranice
def index(request): return render(request, 'cloockot_watches/index.html')
def onama(request): return render(request, 'cloockot_watches/onama.html')
def satovi(request):
    # Proveri da li je korisnik ulogovan
    ulogovan = 'korisnicko_ime' in request.session
    
    # Dodajte ovaj kontekst kako biste mogli da ga koristite u template-u
    context = {
        'ulogovan': ulogovan,
    }
    
    return render(request, 'cloockot_watches/satovi.html', context)
def kontakt(request): return render(request, 'cloockot_watches/kontakt.html')

# Registracija
def registracija(request):
    if request.method == 'POST':
        form = RegistracijaForm(request.POST)
        if form.is_valid():
            korisnik = form.save(commit=False)
            korisnik.lozinka = make_password(form.cleaned_data['lozinka'])
            korisnik.save()
            
            # NE AUTOMATSKI LOGUJ KORISNIKA
            # request.session['korisnik_id'] = korisnik.id
            # request.session['korisnicko_ime'] = korisnik.korisnicko_ime
            
            # Dodaj poruku za uspešnu registraciju
            messages.success(request, f"Uspešno ste se registrovali kao {korisnik.korisnicko_ime}! Sada se možete prijaviti.")
            
            # Preusmeri na stranicu za prijavu
            return redirect('prijava')
    else:
        form = RegistracijaForm()
    
    return render(request, 'cloockot_watches/registracija.html', {'form': form})

# Prijava (ostaje ista, ali možete dodati poruku)
def prijava(request):
    if request.method == 'POST':
        form = PrijavaForm(request.POST)
        if form.is_valid():
            korisnicko_ime = form.cleaned_data['korisnicko_ime']
            lozinka = form.cleaned_data['lozinka']
            next_url = request.POST.get('next')  # 👈 BITNO

            try:
                korisnik = Korisnik.objects.get(korisnicko_ime=korisnicko_ime)
                if check_password(lozinka, korisnik.lozinka):
                    request.session['korisnik_id'] = korisnik.id
                    request.session['korisnicko_ime'] = korisnik.korisnicko_ime
                    messages.success(request, f"Dobrodošli {korisnik.korisnicko_ime}!")

                    # 👇 AKO POSTOJI next → VRATI TAMO
                    if next_url:
                        return redirect('next_url')

                    # fallback
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
# Checkout

def checkout(request):
    if not request.session.get('korisnicko_ime'):
        return JsonResponse({'error': 'Morate biti ulogovani da biste nastavili sa plaćanjem.'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            korpa = data.get('cart', [])
            
            korisnicko_ime = request.session['korisnicko_ime']
            try:
                korisnik = Korisnik.objects.get(korisnicko_ime=korisnicko_ime)
            except Korisnik.DoesNotExist:
                return JsonResponse({'error': 'Korisnik ne postoji.'}, status=400)
            
            ukupno = 0
            artikli_lista = []
            
            for artikal in korpa:
                cena = int(artikal['price'])
                kolicina = int(artikal.get('qty', 1))
                ukupno += cena * kolicina
                
                artikli_lista.append({
                    'id': artikal['id'],
                    'naziv': artikal['title'],
                    'brend': artikal['brand'],
                    'cena': cena,
                    'kolicina': kolicina,
                    'ukupno_za_artikal': cena * kolicina
                })
            
            porudzbina = Porudzbina.objects.create(
                korisnik=korisnik,
                artikli=artikli_lista,
                ukupno=ukupno
            )
            
            # ========== SLANJE EMAIL-A ==========
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            
            # KORIGUJTE OVAJ DEO: 'datum' umesto 'datum_narucivanja'
            email_context = {
                'order_id': porudzbina.id,
                'order_date': porudzbina.datum.strftime('%d.%m.%Y %H:%M'),  # ← OVO JE ISPRAVLJENO
                'customer': {
                    'username': korisnik.korisnicko_ime,
                    'email': korisnik.email,
                    'id': korisnik.id,
                },
                'items': artikli_lista,
                'total': ukupno,
            }
            
            # HTML verzija iz template-a (ako ga koristite)
            # Ako nemate template, koristite inline HTML kao što je u prethodnom odgovoru
            try:
                html_content = render_to_string('emails/order_confirmation_admin.html', email_context)
            except:
                # Fallback ako template ne postoji - koristite inline HTML
                html_content = f"""
                <html>
                <body>
                    <h2>🚀 Nova porudžbina #{porudzbina.id}</h2>
                    <p><strong>Datum:</strong> {email_context['order_date']}</p>
                    <p><strong>Korisnik:</strong> {korisnik.korisnicko_ime}</p>
                    <p><strong>Email:</strong> {korisnik.email}</p>
                    
                    <h3>Stavke:</h3>
                    <table border="1" cellpadding="8" style="border-collapse: collapse;">
                        <tr>
                            <th>Proizvod</th><th>Brend</th><th>Cena</th><th>Količina</th><th>Ukupno</th>
                        </tr>
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
                    <hr>
                    <p><em>Porudžbina je automatski sačuvana u sistemu.</em></p>
                </body>
                </html>
                """
            
            text_content = strip_tags(html_content)
            subject = f'🚀 Nova porudžbina #{porudzbina.id} - {korisnik.korisnicko_ime}'
            
            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=['Kamm1997@gmail.com'],
                    reply_to=[korisnik.email],
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=True)
                print(f"✅ Email porudžbine #{porudzbina.id} poslat na cloockot.probniemail@gmail.com")
            except Exception as e:
                print(f"⚠️ Email nije poslat za porudžbinu #{porudzbina.id}: {e}")
            # ========== KRAJ EMAIL DELA ==========
            
            return JsonResponse({
                'success': True, 
                'message': 'Porudžbina je uspešno kreirana.',
                'order_id': porudzbina.id,
                'total': ukupno
            })
            
        except Exception as e:
            print(f"Greška u checkout: {e}")  # Dodajte za debugging
            return JsonResponse({'error': f'Greška: {str(e)}'}, status=400)
    else:
        return JsonResponse({'error': 'Zahtev mora biti POST.'}, status=405)
