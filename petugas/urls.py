from django.urls import path
from . import views

app_name = 'petugas'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Approval registrasi pelanggan
    path('pelanggan-pending/', views.daftar_pelanggan_pending, name='pelanggan_pending'),
    path('pelanggan/<int:pk>/approve/', views.approve_pelanggan, name='approve_pelanggan'),
    path('pelanggan/<int:pk>/tolak/', views.tolak_pelanggan, name='tolak_pelanggan'),

    # Verifikasi pembayaran
    path('pembayaran-pending/', views.daftar_pembayaran_pending, name='pembayaran_pending'),
    path('pembayaran/<int:pk>/verifikasi/', views.verifikasi_pembayaran, name='verifikasi_pembayaran'),

    # Pesanan diproses
    path('pesanan-diproses/', views.daftar_pesanan_diproses, name='pesanan_diproses'),
    path('pesanan/<int:pk>/selesai/', views.selesaikan_pesanan, name='selesaikan_pesanan'),
]