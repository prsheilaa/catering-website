from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from administrator.models import Pesanan, Pembayaran

User = get_user_model()


class RegistrasiPelangganForm(UserCreationForm):
    """
    Form registrasi untuk pelanggan baru.
    Field sesuai alur bisnis: nama lengkap, username, email, nomor telepon, password, konfirmasi password.
    Role otomatis 'pelanggan' dan is_approved=False (status: Menunggu Persetujuan).
    """
    nama_lengkap = forms.CharField(
        label="Nama Lengkap",
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Nama lengkap sesuai identitas'}),
    )
    email = forms.EmailField(required=True)
    no_telepon = forms.CharField(max_length=20, required=True, label="Nomor Telepon")

    password1 = forms.CharField(
        label="Kata sandi",
        widget=forms.PasswordInput(attrs={'placeholder': 'Minimal 8 karakter'}),
    )
    password2 = forms.CharField(
        label="Konfirmasi kata sandi",
        widget=forms.PasswordInput(attrs={'placeholder': 'Ulangi kata sandi'}),
    )

    class Meta:
        model = User
        fields = ['nama_lengkap', 'username', 'email', 'no_telepon', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.PELANGGAN
        user.is_approved = False
        user.email = self.cleaned_data['email']
        user.no_telepon = self.cleaned_data['no_telepon']
        user.first_name = self.cleaned_data['nama_lengkap']
        if commit:
            user.save()
        return user

class PembayaranForm(forms.ModelForm):
    class Meta:
        model = Pembayaran
        fields = ['metode', 'jumlah_bayar', 'bukti_bayar']

    def clean(self):
        cleaned_data = super().clean()
        metode = cleaned_data.get('metode')
        bukti_bayar = cleaned_data.get('bukti_bayar')

        if metode != Pembayaran.MetodePembayaran.TUNAI and not bukti_bayar:
            self.add_error(
                'bukti_bayar',
                "Bukti pembayaran wajib diunggah untuk metode selain tunai."
            )
        return cleaned_data