from django.urls import path
from . import views

app_name = 'administrator'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Kategori Menu
    path('kategori/', views.kategori_list, name='kategori_list'),
    path('kategori/tambah/', views.kategori_form, name='kategori_tambah'),
    path('kategori/<int:pk>/edit/', views.kategori_form, name='kategori_edit'),
    path('kategori/<int:pk>/hapus/', views.kategori_delete, name='kategori_hapus'),

    # Jenis Catering
    path('jenis-catering/', views.jenis_catering_list, name='jenis_catering_list'),
    path('jenis-catering/tambah/', views.jenis_catering_form, name='jenis_catering_tambah'),
    path('jenis-catering/<int:pk>/edit/', views.jenis_catering_form, name='jenis_catering_edit'),
    path('jenis-catering/<int:pk>/hapus/', views.jenis_catering_delete, name='jenis_catering_hapus'),

    # Menu
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/tambah/', views.menu_form, name='menu_tambah'),
    path('menu/<int:pk>/edit/', views.menu_form, name='menu_edit'),
    path('menu/<int:pk>/hapus/', views.menu_delete, name='menu_hapus'),

    # Kelola Akun
    path('akun/', views.akun_list, name='akun_list'),
    path('akun/tambah/', views.akun_form, name='akun_tambah'),
    path('akun/<int:pk>/edit/', views.akun_form, name='akun_edit'),
    path('akun/<int:pk>/toggle-aktif/', views.akun_toggle_active, name='akun_toggle_active'),
    path('akun/<int:pk>/hapus/', views.akun_delete, name='akun_hapus'),

    # Transaksi
    path('transaksi/', views.transaksi_list, name='transaksi_list'),
    path('transaksi/<int:pk>/', views.transaksi_detail, name='transaksi_detail'),

    # Update status
    path('transaksi/<int:pk>/update-status/',views.transaksi_update_status,name='transaksi_update_status'),

    # Hapus transaksi
    path('transaksi/<int:pk>/hapus/',views.transaksi_delete,name='transaksi_hapus'),

    # Verifikasi pembayaran
    path('pembayaran/<int:pk>/verifikasi/',views.verifikasi_pembayaran,name='verifikasi_pembayaran'),

    # Laporan
    path('laporan/', views.laporan, name='laporan'),
    path('laporan/download/pdf/', views.laporan_download_pdf, name='laporan_pdf'),
    path('laporan/download/excel/', views.laporan_download_excel, name='laporan_excel'),

    #Riwayat Pesanan
    path("riwayat-pesanan/",views.riwayat_pesanan,name="riwayat_pesanan",),

    #Menu Pelanggan
    path("menu/<int:pk>/",views.menu_detail,name="menu_detail",),
    
]