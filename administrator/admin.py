from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User,
    KategoriMenu,
    JenisCatering,
    Menu,
    Pesanan,
    Pembayaran,
)


# ==========================================================
# USER (custom, extend UserAdmin bawaan Django)
# ==========================================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'role', 'is_approved', 'is_active', 'date_joined',
    )
    list_filter = ('role', 'is_approved', 'is_active')
    search_fields = ('username', 'email', 'no_telepon')
    ordering = ('-date_joined',)

    # tambahkan field custom ke form edit user di admin
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Info Tambahan', {
            'fields': ('role', 'is_approved', 'approved_by', 'approved_at', 'no_telepon', 'alamat')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Info Tambahan', {
            'fields': ('role', 'email', 'no_telepon', 'alamat')
        }),
    )

    actions = ['approve_selected']

    @admin.action(description="Setujui pelanggan yang dipilih")
    def approve_selected(self, request, queryset):
        updated = queryset.filter(role=User.Role.PELANGGAN).update(is_approved=True)
        self.message_user(request, f"{updated} akun pelanggan berhasil disetujui.")


# ==========================================================
# KATEGORI & JENIS CATERING
# ==========================================================
@admin.register(KategoriMenu)
class KategoriMenuAdmin(admin.ModelAdmin):
    list_display = ('nama', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('nama',)


@admin.register(JenisCatering)
class JenisCateringAdmin(admin.ModelAdmin):
    list_display = ('nama', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('nama',)


# ==========================================================
# MENU
# ==========================================================
@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('nama_paket', 'kategori', 'jenis_catering', 'harga_per_porsi', 'status_stok', 'created_at')
    list_filter = ('kategori', 'jenis_catering', 'status_stok')
    search_fields = ('nama_paket',)
    list_editable = ('status_stok',)
    autocomplete_fields = ('kategori', 'jenis_catering')


# ==========================================================
# PESANAN (inline Pembayaran biar bisa dilihat sekaligus)
# ==========================================================
class PembayaranInline(admin.StackedInline):
    model = Pembayaran
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Pesanan)
class PesananAdmin(admin.ModelAdmin):
    list_display = (
        'kode_pesanan', 'pelanggan', 'menu', 'jenis_catering',
        'jumlah_porsi', 'total_harga', 'status', 'waktu_acara', 'created_at',
    )
    list_filter = ('status', 'jenis_catering', 'waktu_acara')
    search_fields = ('kode_pesanan', 'nama_pemesan', 'no_telepon', 'pelanggan__username')
    readonly_fields = ('kode_pesanan', 'total_harga', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [PembayaranInline]
    autocomplete_fields = ('pelanggan', 'menu', 'jenis_catering')


# ==========================================================
# PEMBAYARAN (juga didaftarkan terpisah untuk memudahkan verifikasi cepat)
# ==========================================================
@admin.register(Pembayaran)
class PembayaranAdmin(admin.ModelAdmin):
    list_display = (
        'pesanan', 'metode', 'jumlah_bayar', 'status_verifikasi',
        'diverifikasi_oleh', 'tanggal_verifikasi', 'created_at',
    )
    list_filter = ('status_verifikasi', 'metode')
    search_fields = ('pesanan__kode_pesanan',)
    readonly_fields = ('created_at',)
    autocomplete_fields = ('pesanan', 'diverifikasi_oleh')