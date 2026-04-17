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
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

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

# Checkout sa Brevo API-jem
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
        
        # Slanje email potvrde preko Brevo API-ja
        try:
            # Brevo API konfiguracija
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = os.environ.get('BREVO_API_KEY', '')
            
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
            
            # Generisanje HTML sadržaja za email
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
                <div style="max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; border-bottom: 3px solid #e11d48; padding-bottom: 15px;">
                        🚀 Nova porudžbina #{porudzbina.id}
                    </h2>
                    
                    <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>Datum:</strong> {porudzbina.datum.strftime('%d.%m.%Y %H:%M')}</p>
                        <p style="margin: 5px 0;"><strong>Korisnik:</strong> {korisnik.korisnicko_ime} ({korisnik.ime} {korisnik.prezime})</p>
                        <p style="margin: 5px 0;"><strong>Email:</strong> {korisnik.email}</p>
                        <p style="margin: 5px 0;"><strong>Telefon:</strong> {korisnik.telefon}</p>
                    </div>
                    
                    <h3 style="color: #555; margin-top: 30px;">Stavke porudžbine:</h3>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #ddd;">
                        <thead>
                            <tr style="background: #e11d48; color: white;">
                                <th style="padding: 12px; text-align: left;">Proizvod</th>
                                <th style="padding: 12px; text-align: left;">Brend</th>
                                <th style="padding: 12px; text-align: right;">Cena</th>
                                <th style="padding: 12px; text-align: center;">Količina</th>
                                <th style="padding: 12px; text-align: right;">Ukupno</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for item in artikli_lista:
                html_content += f"""
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 12px;">{item['naziv']}</td>
                                <td style="padding: 12px;">{item['brend']}</td>
                                <td style="padding: 12px; text-align: right;">{item['cena']:,} RSD</td>
                                <td style="padding: 12px; text-align: center;">{item['kolicina']}</td>
                                <td style="padding: 12px; text-align: right;">{item['ukupno_za_artikal']:,} RSD</td>
                            </tr>
                """
            
            html_content += f"""
                        </tbody>
                        <tfoot>
                            <tr style="background: #f5f5f5; font-weight: bold; border-top: 2px solid #ddd;">
                                <td colspan="4" style="padding: 15px; text-align: right; font-size: 16px;">UKUPNO:</td>
                                <td style="padding: 15px; text-align: right; font-size: 18px; color: #e11d48;">{ukupno:,} RSD</td>
                            </tr>
                        </tfoot>
                    </table>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                    
                    <p style="color: #666; font-style: italic;">Porudžbina je automatski sačuvana u sistemu.</p>
                    <p style="color: #333; font-weight: bold;">Hvala vam na poverenju! 🎉</p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #999; font-size: 12px;">
                        <p>Cloockot Watches - Vaš pouzdani partner za luksuzne satove</p>
                        <p>www.cloockot.com | cloockot@gmail.com</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Tekstualna verzija za email klijente koji ne podržavaju HTML
            text_content = f"""
NOVA PORUDŽBINA #{porudzbina.id}
==============================

Datum: {porudzbina.datum.strftime('%d.%m.%Y %H:%M')}
Korisnik: {korisnik.korisnicko_ime} ({korisnik.ime} {korisnik.prezime})
Email: {korisnik.email}
Telefon: {korisnik.telefon}

STAVKE PORUDŽBINE:
"""
            for item in artikli_lista:
                text_content += f"\n{item['naziv']} ({item['brend']}) - {item['cena']:,} RSD x {item['kolicina']} = {item['ukupno_za_artikal']:,} RSD"
            
            text_content += f"\n\nUKUPNO: {ukupno:,} RSD\n\nHvala vam na poverenju!\nwww.cloockot.com"
            
            # Kreiranje emaila za Brevo API
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": "cloockot@gmail.com", "name": "Cloockot Watches"}],
                reply_to={"email": korisnik.email, "name": f"{korisnik.ime} {korisnik.prezime}"},
                sender={"email": "cloockot@gmail.com", "name": "Cloockot Porudžbine"},
                subject=f'🚀 Nova porudžbina #{porudzbina.id} - {korisnik.korisnicko_ime}',
                html_content=html_content,
                text_content=text_content
            )
            
            # Slanje emaila
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Email porudžbine #{porudzbina.id} poslat uspešno preko Brevo API-ja. Message ID: {api_response.message_id}")
            
        except ApiException as e:
            logger.error(f"Brevo API greška pri slanju emaila za porudžbinu #{porudzbina.id}: {e}")
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


# Kontakt forma sa Brevo API-jem
@require_http_methods(["POST"])
@ensure_csrf_cookie
def posalji_email(request):
    try:
        # Priprema podataka o korisniku
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

        # Validacija
        if not email_korisnika:
            return JsonResponse({'error': 'Email adresa je obavezna.'}, status=400)
        if not poruka:
            return JsonResponse({'error': 'Poruka je obavezna.'}, status=400)

        # Brevo API konfiguracija
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.environ.get('BREVO_API_KEY', '')
        
        if not os.environ.get('BREVO_API_KEY'):
            logger.error("BREVO_API_KEY nije podešen u environment varijablama")
            return JsonResponse({'error': 'API ključ nije konfigurisan. Kontaktirajte administratora.'}, status=500)
        
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        
        # HTML sadržaj emaila
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #333; border-bottom: 3px solid #e11d48; padding-bottom: 15px;">
                    📧 Nova kontakt poruka
                </h2>
                
                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Od:</strong> {ime_korisnika}</p>
                    <p style="margin: 5px 0;"><strong>Email:</strong> <a href="mailto:{email_korisnika}" style="color: #e11d48;">{email_korisnika}</a></p>
                    <p style="margin: 5px 0;"><strong>Telefon:</strong> {telefon if telefon else 'Nije naveden'}</p>
                </div>
                
                <h3 style="color: #555; margin-top: 30px;">Poruka:</h3>
                <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; border-left: 4px solid #e11d48; margin: 20px 0;">
                    <p style="line-height: 1.6; color: #333; margin: 0;">{poruka}</p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="color: #666; font-style: italic; font-size: 14px;">
                    Ova poruka je poslata preko kontakt forme na sajtu Cloockot.com
                </p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #999; font-size: 12px;">
                    <p>Cloockot Watches - Vaš pouzdani partner za luksuzne satove</p>
                    <p>www.cloockot.com | cloockot@gmail.com | 064 016 6411</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Tekstualna verzija
        text_content = f"""
NOVA KONTAKT PORUKA
==================

Od: {ime_korisnika}
Email: {email_korisnika}
Telefon: {telefon if telefon else 'Nije naveden'}

PORUKA:
{poruka}

---
Ova poruka je poslata preko kontakt forme na sajtu Cloockot.com
www.cloockot.com | cloockot@gmail.com
        """
        
        # Kreiranje emaila
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": "cloockot@gmail.com", "name": "Cloockot Watches"}],
            reply_to={"email": email_korisnika, "name": ime_korisnika},
            sender={"email": "cloockot@gmail.com", "name": "Cloockot Kontakt"},
            subject=f"Kontakt poruka od {ime_korisnika}",
            html_content=html_content,
            text_content=text_content
        )
        
        # Slanje emaila
        api_response = api_instance.send_transac_email(send_smtp_email)
        
        logger.info(f"Kontakt email poslat uspešno preko Brevo API-ja. Message ID: {api_response.message_id}")
        
        return JsonResponse({'success': True, 'message': 'Poruka je uspešno poslata!'})
        
    except ApiException as e:
        logger.error(f"Brevo API greška: {e}")
        return JsonResponse({'error': f'Greška pri slanju emaila: {str(e)}'}, status=500)
    except Exception as e:
        logger.error(f"Opšta greška u posalji_email: {e}")
        return JsonResponse({'error': f'Došlo je do greške: {str(e)}'}, status=500)