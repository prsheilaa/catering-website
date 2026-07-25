from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.utils import timezone

from administrator.decorators import role_required
from administrator.models import Pesanan, Pembayaran
from .forms import VerifikasiPembayaranForm

User = get_user_model()


# ==========================================================
# DASHBOARD OPERATOR
# ==========================================================
@role_required('petugas')
def dashboard(request):
    context = {
        'pelanggan_pending': User.objects.filter(role=User.Role.PELANGGAN, is_approved=False).count(),
        'pembayaran_menunggu': Pembayaran.objects.filter(status_verifikasi=Pembayaran.StatusVerifikasi.MENUNGGU).count(),
        'pesanan_diproses': Pesanan.objects.filter(status=Pesanan.StatusPesanan.DIPROSES).count(),
        'pesanan_terbaru': Pesanan.objects.select_related('pelanggan', 'menu').order_by('-created_at')[:6],
    }
    return render(request, 'petugas/dashboard.html', context)


# ==========================================================
# APPROVAL REGISTRASI PELANGGAN
# ==========================================================
@role_required('petugas')
def daftar_pelanggan_pending(request):
    pelanggan = User.objects.filter(role=User.Role.PELANGGAN, is_approved=False).order_by('-date_joined')
    paginator = Paginator(pelanggan, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'petugas/pelanggan_pending.html', {'page_obj': page_obj})


@role_required('petugas')
def approve_pelanggan(request, pk):
    pelanggan = get_object_or_404(User, pk=pk, role=User.Role.PELANGGAN)
    pelanggan.is_approved = True
    pelanggan.approved_by = request.user
    pelanggan.approved_at = timezone.now()
    pelanggan.save(update_fields=['is_approved', 'approved_by', 'approved_at'])
    messages.success(request, f"Registrasi {pelanggan.username} berhasil disetujui.")
    return redirect('petugas:pelanggan_pending')


@role_required('petugas')
def tolak_pelanggan(request, pk):
    pelanggan = get_object_or_404(User, pk=pk, role=User.Role.PELANGGAN)
    pelanggan.delete()
    messages.success(request, "Registrasi pelanggan ditolak dan data dihapus.")
    return redirect('petugas:pelanggan_pending')


# ==========================================================
# VERIFIKASI PEMBAYARAN
# ==========================================================
@role_required('petugas')
def daftar_pembayaran_pending(request):
    pembayaran = Pembayaran.objects.filter(
        status_verifikasi=Pembayaran.StatusVerifikasi.MENUNGGU
    ).select_related('pesanan', 'pesanan__pelanggan').order_by('created_at')
    paginator = Paginator(pembayaran, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'petugas/pembayaran_pending.html', {'page_obj': page_obj})


@role_required('petugas')
def verifikasi_pembayaran(request, pk):
    pembayaran = get_object_or_404(Pembayaran, pk=pk)

    if request.method == 'POST':
        form = VerifikasiPembayaranForm(request.POST, instance=pembayaran)
        if form.is_valid():
            pembayaran = form.save(commit=False)
            pembayaran.diverifikasi_oleh = request.user
            pembayaran.tanggal_verifikasi = timezone.now()
            pembayaran.save()

            pesanan = pembayaran.pesanan
            if pembayaran.status_verifikasi == Pembayaran.StatusVerifikasi.VALID:
                pesanan.status = Pesanan.StatusPesanan.DIPROSES
                pesanan.diproses_oleh = request.user
                messages.success(request, "Pembayaran valid. Status pesanan diubah menjadi Diproses.")
            elif pembayaran.status_verifikasi == Pembayaran.StatusVerifikasi.TIDAK_VALID:
                pesanan.status = Pesanan.StatusPesanan.MENUNGGU_PEMBAYARAN
                messages.warning(request, "Pembayaran tidak valid. Pelanggan diminta mengulang pembayaran.")
            pesanan.save(update_fields=['status', 'diproses_oleh'])

            return redirect('petugas:pembayaran_pending')
    else:
        form = VerifikasiPembayaranForm(instance=pembayaran)

    return render(request, 'petugas/verifikasi_pembayaran.html', {
        'form': form,
        'pembayaran': pembayaran,
        'pesanan': pembayaran.pesanan,
    })


# ==========================================================
# KELOLA STATUS PESANAN YANG SEDANG DIPROSES
# ==========================================================
@role_required('petugas')
def daftar_pesanan_diproses(request):
    pesanan = Pesanan.objects.filter(
        status=Pesanan.StatusPesanan.DIPROSES
    ).select_related('pelanggan', 'menu').order_by('waktu_acara')
    paginator = Paginator(pesanan, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'petugas/pesanan_diproses.html', {'page_obj': page_obj})


@role_required('petugas')
def selesaikan_pesanan(request, pk):
    pesanan = get_object_or_404(Pesanan, pk=pk, status=Pesanan.StatusPesanan.DIPROSES)
    pesanan.status = Pesanan.StatusPesanan.SELESAI
    pesanan.save(update_fields=['status'])
    messages.success(request, f"Pesanan {pesanan.kode_pesanan} ditandai selesai.")
    return redirect('petugas:pesanan_diproses')

# ==========================================================
# RIWAYAT PEMBAYARAN
# ==========================================================
@role_required('petugas')
def riwayat_pembayaran(request):
    pembayaran = Pembayaran.objects.select_related(
        'pesanan',
        'pesanan__pelanggan'
    ).order_by('-created_at')

    paginator = Paginator(pembayaran, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'petugas/riwayat_pembayaran.html',
        {
            'page_obj': page_obj
        }
    )


# ==========================================================
# DETAIL PEMBAYARAN
# ==========================================================
@role_required('petugas')
def detail_pembayaran(request, pk):

    pembayaran = get_object_or_404(
        Pembayaran,
        pk=pk
    )

    return render(
        request,
        'petugas/detail_pembayaran.html',
        {
            'pembayaran': pembayaran,
            'pesanan': pembayaran.pesanan,
        }
    )