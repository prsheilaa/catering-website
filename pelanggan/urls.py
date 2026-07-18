from django.urls import path
from . import views

app_name = 'pelanggan'

urlpatterns = [
    # Auth
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Menu
    path('menu/', views.menu_list, name='menu_list'),

    # Pemesanan
    path('pesan/<int:menu_id>/', views.buat_pesanan, name='buat_pesanan'),
    path('pesanan/<int:pesanan_id>/bayar/', views.upload_pembayaran, name='upload_pembayaran'),

    # Riwayat & detail
    path('riwayat/', views.riwayat_pesanan, name='riwayat_pesanan'),
    path('pesanan/<int:pesanan_id>/', views.detail_pesanan, name='detail_pesanan'),
]