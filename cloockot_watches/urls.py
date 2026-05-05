from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index/', views.index, name='index'),
    path('onama/', views.onama, name='onama'),
    path('satovi/', views.satovi, name='satovi'),
    path('kontakt/', views.kontakt, name='kontakt'),
    path('registracija/', views.registracija, name='registracija'),
    path('prijava/', views.prijava, name='prijava'),
    path('odjava/', views.odjava, name='odjava'),
    path('checkout/', views.checkout, name='checkout'),
    # path('posalji-email/', views.posalji_email, name='posalji_email'),  ← OBRiŠI OVU LINIJU
]