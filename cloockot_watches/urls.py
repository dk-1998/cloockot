from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),           # ← DODAJ OVO (root URL)
    path('index/', views.index, name='index'),
    path('onama/', views.onama, name='onama'),
    path('satovi/', views.satovi, name='satovi'),
    path('kontakt/', views.kontakt, name='kontakt'),
    path('registracija/', views.registracija, name='registracija'),
    path('prijava/', views.prijava, name='prijava'),
    path('odjava/', views.odjava, name='odjava'),
    path('checkout/', views.checkout, name='checkout'),
    path("posalji_email/", views.posalji_email, name="posalji_email"),
    path('test-email/', views.test_email, name='test_email')
]