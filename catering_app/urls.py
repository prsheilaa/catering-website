from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('django-admin/', admin.site.urls),   # admin bawaan Django (beda dari app 'administrator')

    path('', RedirectView.as_view(pattern_name='pelanggan:login', permanent=False)),

    path('', include('pelanggan.urls')),           # root -> pelanggan (register, login, menu, dst)
    path('admin-panel/', include('administrator.urls')),
    path('petugas/', include('petugas.urls')),
]

# Untuk serving file upload (foto menu, bukti pembayaran) saat development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)