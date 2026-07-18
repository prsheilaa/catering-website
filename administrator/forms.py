from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Menu, KategoriMenu, JenisCatering

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
            'kategori', 'jenis_catering', 'nama_paket', 'deskripsi',
            'harga_per_porsi', 'foto', 'status_stok',
        ]
        widgets = {
            'deskripsi': forms.Textarea(attrs={'rows': 3}),
        }


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