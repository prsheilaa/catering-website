from django import forms
from administrator.models import Pembayaran


class VerifikasiPembayaranForm(forms.ModelForm):
    class Meta:
        model = Pembayaran
        fields = ['status_verifikasi', 'catatan_verifikasi']
        widgets = {
            'catatan_verifikasi': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Opsional, misal alasan pembayaran tidak valid'}),
        }