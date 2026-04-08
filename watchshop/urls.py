from django.contrib import admin
from django.urls import path, include

from cloockot_watches.views import posalji_email  # uvezi funkciju
urlpatterns = [
    path('admin/', admin.site.urls),
    path('posalji-email/', posalji_email, name='posalji_email'),
    path('', include('cloockot_watches.urls'))
]




