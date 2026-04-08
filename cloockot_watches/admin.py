from django.contrib import admin
from .models import Korisnik, Porudzbina, Sat

class KorisnikAdmin(admin.ModelAdmin):
    list_display = ('id', 'korisnicko_ime', 'ime', 'prezime', 'email', 'telefon', 'broj_porudzbina')
    search_fields = ('korisnicko_ime', 'ime', 'prezime', 'email', 'telefon')
    list_filter = ('ime', 'prezime')
    list_per_page = 20
    ordering = ('-id',)
    
    def broj_porudzbina(self, obj):
        try:
            return obj.porudzbine.count()
        except Exception:
            return 0
    broj_porudzbina.short_description = 'Broj porudžbina'

class PorudzbinaAdmin(admin.ModelAdmin):
    list_display = ('id', 'naziv', 'korisnik_info', 'korisnik_email', 'datum', 'ukupno_display', 'broj_artikala')
    search_fields = ('naziv', 'korisnik__korisnicko_ime', 'korisnik__ime', 'korisnik__prezime', 'korisnik__email')
    list_filter = ('datum',)
    readonly_fields = ('datum', 'artikli_display')
    fields = ('korisnik', 'naziv', 'datum', 'artikli_display', 'ukupno')
    list_per_page = 20
    ordering = ('-datum',)
    
    def korisnik_info(self, obj):
        try:
            return f"{obj.korisnik.korisnicko_ime} ({obj.korisnik.ime} {obj.korisnik.prezime})"
        except Exception:
            return "Nepoznat"
    korisnik_info.short_description = 'Korisnik'
    korisnik_info.admin_order_field = 'korisnik__korisnicko_ime'
    
    def korisnik_email(self, obj):
        try:
            return obj.korisnik.email
        except Exception:
            return "Nepoznat"
    korisnik_email.short_description = 'Email'
    korisnik_email.admin_order_field = 'korisnik__email'
    
    def korisnik_telefon(self, obj):
        try:
            return obj.korisnik.telefon
        except Exception:
            return "Nepoznat"
    korisnik_telefon.short_description = 'Telefon'
    korisnik_telefon.admin_order_field = 'korisnik__telefon'
    
    def ukupno_display(self, obj):
        try:
            return f"{obj.ukupno:,} RSD".replace(",", ".")
        except Exception:
            return f"{obj.ukupno} RSD"
    ukupno_display.short_description = 'Ukupno'
    ukupno_display.admin_order_field = 'ukupno'
    
    def broj_artikala(self, obj):
        if obj.artikli:
            try:
                return sum(art.get('kolicina', 1) for art in obj.artikli)
            except Exception:
                return 0
        return 0
    broj_artikala.short_description = 'Broj artikala'
    
    def artikli_display(self, obj):
        """Prikazuje artikle u lepoj tabeli"""
        if not obj.artikli:
            return "Nema artikala"
        
        try:
            html = '<div style="max-height: 400px; overflow-y: auto;">'
            html += '<table style="width:100%; border-collapse: collapse; font-size: 13px;">'
            html += '<thead>'
            html += '<tr style="background: #f0f0f0; border-bottom: 2px solid #ddd;">'
            html += '<th style="padding: 8px; text-align: left;">Brend</th>'
            html += '<th style="padding: 8px; text-align: left;">Naziv</th>'
            html += '<th style="padding: 8px; text-align: right;">Cena (RSD)</th>'
            html += '<th style="padding: 8px; text-align: center;">Količina</th>'
            html += '<th style="padding: 8px; text-align: right;">Ukupno (RSD)</th>'
            html += '</tr>'
            html += '</thead>'
            html += '<tbody>'
            
            for art in obj.artikli:
                cena = art.get('cena', 0)
                kolicina = art.get('kolicina', 1)
                ukupno_art = art.get('ukupno_za_artikal', cena * kolicina)
                
                html += f'''
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 8px; text-align: left;"><strong>{art.get('brend', '')}</strong></td>
                        <td style="padding: 8px; text-align: left;">{art.get('naziv', '')}</td>
                        <td style="padding: 8px; text-align: right;">{cena:,}</td>
                        <td style="padding: 8px; text-align: center;">{kolicina}</td>
                        <td style="padding: 8px; text-align: right;">{ukupno_art:,} RSD</td>
                    </tr>
                '''
            
            html += '</tbody>'
            html += '<tfoot>'
            html += f'''
                <tr style="background: #f9f9f9; font-weight: bold; border-top: 2px solid #ddd;">
                    <td colspan="4" style="padding: 8px; text-align: right;">UKUPNO ZA PORUDŽBINU:</td>
                    <td style="padding: 8px; text-align: right;">{obj.ukupno:,} RSD</td>
                </tr>
            '''
            html += '</tfoot>'
            html += '</table>'
            html += '</div>'
            return html
        except Exception:
            return obj.formatirani_artikli()
    
    artikli_display.short_description = 'Artikli'
    artikli_display.allow_tags = True


# Registracija modela u admin panel
admin.site.register(Korisnik, KorisnikAdmin)
admin.site.register(Porudzbina, PorudzbinaAdmin)
