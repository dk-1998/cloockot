from django.contrib import admin
from .models import Korisnik, Porudzbina

class KorisnikAdmin(admin.ModelAdmin):
    list_display = ('id', 'korisnicko_ime', 'ime', 'prezime', 'email', 'telefon', 'broj_porudzbina')
    search_fields = ('korisnicko_ime', 'ime', 'prezime', 'email', 'telefon')
    list_filter = ('ime', 'prezime')
    
    def broj_porudzbina(self, obj):
        try:
            return obj.porudzbine.count()
        except Exception:
            return 0
    broj_porudzbina.short_description = 'Broj porudžbina'

class PorudzbinaAdmin(admin.ModelAdmin):
    list_display = ('id', 'korisnik_info', 'datum', 'ukupno_display')
    search_fields = ('korisnik__korisnicko_ime', 'korisnik__ime', 'korisnik__prezime')
    list_filter = ('datum',)
    readonly_fields = ('datum',)
    
    def korisnik_info(self, obj):
        try:
            return f"{obj.korisnik.korisnicko_ime} ({obj.korisnik.ime} {obj.korisnik.prezime})"
        except Exception:
            return "Nepoznat"
    korisnik_info.short_description = 'Korisnik'
    
    def ukupno_display(self, obj):
        try:
            return f"{obj.ukupno:,} RSD".replace(",", ".")
        except Exception:
            return f"{obj.ukupno} RSD"
    ukupno_display.short_description = 'Ukupno'
    
    # Izbacujemo formatirani_artikli_display jer nije neophodan i može praviti problem

admin.site.register(Korisnik, KorisnikAdmin)
admin.site.register(Porudzbina, PorudzbinaAdmin)