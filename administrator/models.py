from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils import timezone

BANK_NAME = "Bank Nusantara Sejahtera"
BANK_VA_PREFIX = "8807"
EWALLET_PROVIDER = "DANA"
EWALLET_NUMBER = "0812-3456-7890"
EWALLET_ACCOUNT_NAME = "Meja Nusantara Catering"
QRIS_MERCHANT_NAME = "MEJA NUSANTARA CATERING"

# ==========================================================
# USER & ROLE
# ==========================================================
class User(AbstractUser):
    """
    Custom User dengan 3 hak akses: administrator, petugas, pelanggan.
    Field bawaan AbstractUser (username, email, password, dll) tetap dipakai.
    """
    class Role(models.TextChoices):
        ADMINISTRATOR = 'administrator', 'Administrator'
        petugas = 'petugas', 'petugas'
        PELANGGAN = 'pelanggan', 'Pelanggan'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PELANGGAN)

    is_approved = models.BooleanField(
        default=False,
        help_text="Khusus role pelanggan. True jika registrasi sudah disetujui petugas."
    )
    approved_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_users', limit_choices_to={'role': 'petugas'}
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    no_telepon = models.CharField(max_length=20, blank=True)
    alamat = models.TextField(blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def status_akun(self):
        """Label status akun sesuai alur bisnis: Menunggu Persetujuan / Aktif / Nonaktif."""
        if self.role == self.Role.PELANGGAN and not self.is_approved:
            return "Menunggu Persetujuan"
        return "Aktif" if self.is_active else "Nonaktif"

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMINISTRATOR
            self.is_approved = True
        super().save(*args, **kwargs)

    @property
    def virtual_account_number(self):
        """Nomor Virtual Account tujuan transfer bank untuk pesanan ini."""
        return f"{BANK_VA_PREFIX}{self.id:010d}"


# ==========================================================
# KATEGORI & JENIS CATERING (dikelola administrator)
# ==========================================================
class KategoriMenu(models.Model):
    """
    Kategori paket masakan: Nusantara, Korea, Thailand, Chinese, dst.
    Dibuat sebagai model (bukan choices) agar admin bisa CRUD kategori.
    """
    nama = models.CharField(max_length=100, unique=True)
    deskripsi = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Kategori Menu"

    def __str__(self):
        return self.nama


class JenisCatering(models.Model):
    """
    Jenis layanan catering: Prasmanan, Nasi Box, Snack Box, dll.
    """
    nama = models.CharField(max_length=100, unique=True)
    deskripsi = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Jenis Catering"

    def __str__(self):
        return self.nama


# ==========================================================
# MENU / PAKET
# ==========================================================
class Menu(models.Model):
    """
    Paket menu yang dipilih pelanggan saat memesan.
    Status stok menentukan tampilan (hitam putih + keterangan 'Kosong').
    """
    class StatusStok(models.TextChoices):
        TERSEDIA = 'tersedia', 'Tersedia'
        KOSONG = 'kosong', 'Kosong'

    kategori = models.ForeignKey(KategoriMenu, on_delete=models.PROTECT, related_name='menu_list')
    jenis_catering = models.ForeignKey(
        JenisCatering, on_delete=models.SET_NULL, related_name='menu_list',
        null=True, blank=True,
    )

    nama_paket = models.CharField(max_length=150)
    deskripsi = models.TextField(blank=True)
    harga_per_porsi = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    foto = models.ImageField(upload_to='menu/', blank=True, null=True)

    status_stok = models.CharField(max_length=20, choices=StatusStok.choices, default=StatusStok.TERSEDIA)

    dibuat_oleh = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='menu_dibuat', limit_choices_to={'role': 'administrator'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Menu"

    def __str__(self):
        return f"{self.nama_paket} - {self.kategori.nama}"

    @property
    def is_kosong(self):
        return self.status_stok == self.StatusStok.KOSONG


# ==========================================================
# PESANAN
# ==========================================================
class Pesanan(models.Model):
    """
    Data pesanan yang diisi pelanggan pada form pemesanan.
    """
    class StatusPesanan(models.TextChoices):
        MENUNGGU_PEMBAYARAN = 'menunggu_pembayaran', 'Menunggu Pembayaran'
        DIPROSES = 'diproses', 'Diproses'
        SELESAI = 'selesai', 'Selesai'
        DIBATALKAN = 'dibatalkan', 'Dibatalkan'

    kode_pesanan = models.CharField(max_length=30, unique=True, editable=False)

    pelanggan = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='pesanan_list',
        limit_choices_to={'role': 'pelanggan'}
    )
    menu = models.ForeignKey(Menu, on_delete=models.PROTECT, related_name='pesanan_list')
    jenis_catering = models.ForeignKey(JenisCatering, on_delete=models.PROTECT, related_name='pesanan_list')

    # Detail form pemesanan
    nama_pemesan = models.CharField(max_length=150)
    alamat = models.TextField()
    no_telepon = models.CharField(max_length=20)
    waktu_acara = models.DateTimeField()
    jumlah_porsi = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    catatan_tambahan = models.TextField(blank=True)

    total_harga = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=30, choices=StatusPesanan.choices, default=StatusPesanan.MENUNGGU_PEMBAYARAN
    )

    diproses_oleh = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pesanan_diproses', limit_choices_to={'role': 'petugas'}
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Pesanan"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.kode_pesanan} - {self.nama_pemesan}"

    def save(self, *args, **kwargs):
        if not self.total_harga:
            self.total_harga = self.menu.harga_per_porsi * self.jumlah_porsi
        super().save(*args, **kwargs)
    @property
    def virtual_account_number(self):
                                                                                                                return f"{BANK_VA_PREFIX}{self.id:010d}"

class ItemPesanan(models.Model):
    """
    Detail menu di dalam satu pesanan (satu pesanan bisa berisi banyak menu).
    """
    pesanan = models.ForeignKey(Pesanan, on_delete=models.CASCADE, related_name='item_list')
    menu = models.ForeignKey(Menu, on_delete=models.PROTECT, related_name='item_pesanan_list')
    jumlah_porsi = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        verbose_name_plural = "Item Pesanan"

    def save(self, *args, **kwargs):
        if not self.subtotal:
            self.subtotal = self.menu.harga_per_porsi * self.jumlah_porsi
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.menu.nama_paket} x{self.jumlah_porsi}"


# ==========================================================
# PEMBAYARAN
# ==========================================================
class Pembayaran(models.Model):
    """
    Bukti & verifikasi pembayaran oleh petugas.
    Valid -> status pesanan jadi 'diproses'.
    Tidak valid -> status pesanan tetap/kembali 'menunggu_pembayaran'.
    """
    class MetodePembayaran(models.TextChoices):
        TRANSFER_BANK = 'transfer_bank', 'Transfer Bank'
        E_WALLET = 'e_wallet', 'E-Wallet'
        QRIS = 'qris', 'QRIS'
        TUNAI = 'tunai', 'Tunai'

    class StatusVerifikasi(models.TextChoices):
        MENUNGGU = 'menunggu', 'Menunggu Verifikasi'
        VALID = 'valid', 'Valid'
        TIDAK_VALID = 'tidak_valid', 'Tidak Valid'

    pesanan = models.OneToOneField(Pesanan, on_delete=models.CASCADE, related_name='pembayaran')

    metode = models.CharField(max_length=20, choices=MetodePembayaran.choices)
    jumlah_bayar = models.DecimalField(max_digits=14, decimal_places=2)
    bukti_bayar = models.ImageField(upload_to='bukti_pembayaran/', blank=True, null=True)

    status_verifikasi = models.CharField(
        max_length=20, choices=StatusVerifikasi.choices, default=StatusVerifikasi.MENUNGGU
    )
    catatan_verifikasi = models.TextField(blank=True)
    diverifikasi_oleh = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pembayaran_diverifikasi', limit_choices_to={'role': 'petugas'}
    )
    tanggal_verifikasi = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Pembayaran"

    def __str__(self):
        return f"Pembayaran {self.pesanan.kode_pesanan} - {self.get_status_verifikasi_display()}"
    
# ==========================================================
# PENGATURAN JEDA WAKTU PEMESANAN (Minimal H- Pemesanan)
# ==========================================================
class PengaturanPemesanan(models.Model):
    """
    Pengaturan minimal jeda waktu (H-) antara tanggal pesan dan waktu acara.

    - Mode manual: admin menentukan langsung minimal H- berapa hari.
    - Mode otomatis: minimal H- menyesuaikan jumlah pesanan aktif saat itu
      (menunggu_pembayaran + diproses). Semakin banyak pesanan aktif,
      semakin panjang jeda waktu minimal yang diberlakukan, supaya dapur
      tidak kewalahan menerima pesanan mendadak.

    Disimpan sebagai singleton (selalu pk=1) agar mudah diatur dari 1 halaman.
    """

    mode_otomatis = models.BooleanField(
        default=False,
        help_text="Jika aktif, minimal H- pemesanan otomatis menyesuaikan jumlah pesanan aktif."
    )

    minimal_hari_manual = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(0)],
        help_text="Minimal H- pemesanan yang dipakai saat mode otomatis dimatikan. Contoh: 3 = pesanan minimal 3 hari sebelum acara."
    )

    # ----- Ambang batas untuk mode otomatis -----
    batas_pesanan_sedang = models.PositiveIntegerField(
        default=10,
        help_text="Jika jumlah pesanan aktif mencapai angka ini, minimal H- dinaikkan ke 'H- saat sedang ramai'."
    )
    hari_saat_sedang = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(0)],
        help_text="Minimal H- pemesanan saat jumlah pesanan aktif tergolong sedang ramai."
    )

    batas_pesanan_padat = models.PositiveIntegerField(
        default=20,
        help_text="Jika jumlah pesanan aktif mencapai angka ini, minimal H- dinaikkan ke 'H- saat padat'."
    )
    hari_saat_padat = models.PositiveIntegerField(
        default=7,
        validators=[MinValueValidator(0)],
        help_text="Minimal H- pemesanan saat jumlah pesanan aktif tergolong padat/kewalahan."
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pengaturan Pemesanan"
        verbose_name_plural = "Pengaturan Pemesanan"

    def __str__(self):
        return "Pengaturan Jeda Waktu Pemesanan"

    def save(self, *args, **kwargs):
        # Singleton: paksa selalu pk=1 supaya hanya ada 1 baris pengaturan.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Ambil (atau buat default jika belum ada) baris pengaturan singleton."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @staticmethod
    def jumlah_pesanan_aktif():
        """Jumlah pesanan yang masih membutuhkan kapasitas dapur saat ini."""
        return Pesanan.objects.filter(
            status__in=[
                Pesanan.StatusPesanan.MENUNGGU_PEMBAYARAN,
                Pesanan.StatusPesanan.DIPROSES,
            ]
        ).count()

    def get_minimal_hari(self, jumlah_aktif=None):
        """
        Hitung minimal H- pemesanan yang berlaku saat ini.
        Jika mode_otomatis mati -> pakai minimal_hari_manual.
        Jika mode_otomatis aktif -> naik berjenjang sesuai jumlah pesanan aktif.
        """
        if not self.mode_otomatis:
            return self.minimal_hari_manual

        if jumlah_aktif is None:
            jumlah_aktif = self.jumlah_pesanan_aktif()

        if jumlah_aktif >= self.batas_pesanan_padat:
            return self.hari_saat_padat
        if jumlah_aktif >= self.batas_pesanan_sedang:
            return self.hari_saat_sedang
        return self.minimal_hari_manual

    def batas_waktu_tercepat(self, jumlah_aktif=None):
        """Waktu acara paling cepat yang masih boleh dipesan sekarang."""
        minimal_hari = self.get_minimal_hari(jumlah_aktif)
        return timezone.now() + timezone.timedelta(days=minimal_hari)