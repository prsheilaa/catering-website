from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Menu, KategoriMenu, JenisCatering, PengaturanPemesanan, PengaturanDP

User = get_user_model()


class KategoriMenuForm(forms.ModelForm):
    class Meta:
        model = KategoriMenu
        fields = ['nama', 'deskripsi', 'is_active']


class JenisCateringForm(forms.ModelForm):
    class Meta:
        model = JenisCatering
        fields = ['nama', 'deskripsi', 'is_active']


class MenuForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = [
            'kategori', 'nama_paket', 'deskripsi',
            'harga_per_porsi', 'foto', 'status_stok',
        ]
        widgets = {
            'deskripsi': forms.Textarea(attrs={'rows': 3}),
        }
        
class PengaturanForm(forms.ModelForm):
    class Meta:
        model = PengaturanPemesanan
        fields = "__all__"


class AkunForm(forms.ModelForm):
    """
    Form untuk administrator membuat/mengedit akun petugas & pelanggan.
    - Saat tambah baru: password1 & password2 wajib diisi.
    - Saat edit: password boleh dikosongkan (artinya password tidak diubah).
    """
    password1 = forms.CharField(
        label="Kata sandi",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'placeholder': 'Minimal 8 karakter'}),
        required=False,
        help_text="Kosongkan jika tidak ingin mengubah kata sandi.",
    )
    password2 = forms.CharField(
        label="Ulangi kata sandi",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'placeholder': 'Ulangi kata sandi'}),
        required=False,
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'no_telepon', 'alamat', 'is_active', 'is_approved']
        widgets = {
            'alamat': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Administrator hanya boleh membuat/mengedit akun petugas & pelanggan
        self.fields['role'].choices = [
            (User.Role.petugas, 'Petugas'),
            (User.Role.PELANGGAN, 'Pelanggan'),
        ]
        if not self.instance.pk:
            self.fields['password1'].required = True
            self.fields['password2'].required = True
            self.fields['password1'].help_text = ""

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Username sudah digunakan, pilih username lain.")
        return username

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')

        if password1 or password2:
            if password1 != password2:
                raise ValidationError("Kata sandi dan ulangi kata sandi tidak cocok.")
            try:
                validate_password(password1, user=self.instance)
            except ValidationError as e:
                self.add_error('password1', e)

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get('password1')
        if password1:
            user.set_password(password1)
        if commit:
            user.save()
        return user
    
class PengaturanPemesananForm(forms.ModelForm):
    """
    Form pengaturan minimal jeda waktu (H-) pemesanan.
    Bisa manual (nilai H- tetap) atau otomatis (naik sesuai kepadatan pesanan aktif).
    """
    class Meta:
        model = PengaturanPemesanan
        fields = [
            'mode_otomatis',
            'minimal_hari_manual',
            'batas_pesanan_sedang',
            'hari_saat_sedang',
            'batas_pesanan_padat',
            'hari_saat_padat',
        ]

    def clean(self):
        cleaned = super().clean()
        batas_sedang = cleaned.get('batas_pesanan_sedang')
        batas_padat = cleaned.get('batas_pesanan_padat')
        hari_manual = cleaned.get('minimal_hari_manual')
        hari_sedang = cleaned.get('hari_saat_sedang')
        hari_padat = cleaned.get('hari_saat_padat')

        if batas_sedang is not None and batas_padat is not None and batas_padat <= batas_sedang:
            self.add_error(
                'batas_pesanan_padat',
                "Ambang batas 'padat' harus lebih besar dari ambang batas 'sedang'."
            )

        if hari_manual is not None and hari_sedang is not None and hari_sedang < hari_manual:
            self.add_error(
                'hari_saat_sedang',
                "Minimal H- saat sedang ramai sebaiknya tidak lebih kecil dari H- normal."
            )

        if hari_sedang is not None and hari_padat is not None and hari_padat < hari_sedang:
            self.add_error(
                'hari_saat_padat',
                "Minimal H- saat padat sebaiknya tidak lebih kecil dari H- saat sedang ramai."
            )

        return cleaned

class PengaturanDPForm(forms.ModelForm):
    """
    Form pengaturan wajib DP (uang muka) untuk admin.
    - wajib_dp: saklar on/off.
    - persen_dp: persentase yang wajib dibayar di muka (default 50%), bebas diubah admin.
    """
    class Meta:
        model = PengaturanDP
        fields = ['wajib_dp', 'persen_dp']
        labels = {
            'wajib_dp': 'Wajibkan DP untuk pesanan baru',
            'persen_dp': 'Persentase DP (%)',
        }