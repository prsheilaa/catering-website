from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator

from administrator.decorators import role_required
from administrator.models import Menu, KategoriMenu, JenisCatering, Pesanan, Pembayaran
from .forms import RegistrasiPelangganForm, PemesananForm, PembayaranForm


# ==========================================================
# REGISTRASI & LOGIN
# ==========================================================
def register(request):
    if request.method == 'POST':
        form = RegistrasiPelangganForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Akun berhasil dibuat! Akun Anda menunggu persetujuan petugas sebelum bisa login."
            )
            return redirect('pelanggan:login')
    else:
        form = RegistrasiPelangganForm()
    return render(request, 'pelanggan/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # cek approval khusus role pelanggan
            if user.role == user.Role.PELANGGAN and not user.is_approved:
                messages.error(request, "Akun Anda belum disetujui petugas. Silakan tunggu konfirmasi.")
                return redirect('pelanggan:login')
            login(request, user)
            messages.success(request, f"Selamat datang kembali, {user.username}.")
            return _redirect_by_role(user)
        else:
            messages.error(request, "Username atau kata sandi salah.")
    else:
        form = AuthenticationForm()
    return render(request, 'pelanggan/login.html', {'form': form})


def _redirect_by_role(user):
    """Redirect ke dashboard sesuai role setelah login."""
    if user.role == user.Role.ADMINISTRATOR:
        return redirect('administrator:dashboard')
    elif user.role == user.Role.petugas:
        return redirect('petugas:dashboard')
    return redirect('pelanggan:dashboard')


def logout_view(request):
    logout(request)
    messages.success(request, "Anda berhasil keluar.")
    return redirect('pelanggan:login')


# ==========================================================
# DASHBOARD
# ==========================================================
@role_required('pelanggan')
def dashboard(request):
    pesanan_user = Pesanan.objects.filter(pelanggan=request.user)

    context = {
        'total_pesanan': pesanan_user.count(),
        'pesanan_menunggu': pesanan_user.filter(status=Pesanan.StatusPesanan.MENUNGGU_PEMBAYARAN).count(),
        'pesanan_diproses': pesanan_user.filter(status=Pesanan.StatusPesanan.DIPROSES).count(),
        'pesanan_selesai': pesanan_user.filter(status=Pesanan.StatusPesanan.SELESAI).count(),
        'pesanan_terbaru': pesanan_user.select_related('menu').order_by('-created_at')[:5],
        'kategori_list': KategoriMenu.objects.filter(is_active=True),
        'menu_tersedia': Menu.objects.filter(status_stok=Menu.StatusStok.TERSEDIA).select_related('kategori')[:6],
    }
    return render(request, 'pelanggan/dashboard.html', context)


# ==========================================================
# DAFTAR MENU
# ==========================================================
@role_required('pelanggan')
def menu_list(request):
    menu = Menu.objects.select_related('kategori', 'jenis_catering').order_by('kategori__nama', 'nama_paket')

    kategori_id = request.GET.get('kategori')
    jenis_id = request.GET.get('jenis')
    if kategori_id:
        menu = menu.filter(kategori_id=kategori_id)
    if jenis_id:
        menu = menu.filter(jenis_catering_id=jenis_id)

    paginator = Paginator(menu, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'pelanggan/menu_list.html', {
        'page_obj': page_obj,
        'kategori_list': KategoriMenu.objects.filter(is_active=True),
        'jenis_list': JenisCatering.objects.filter(is_active=True),
        'kategori_id': kategori_id or '',
        'jenis_id': jenis_id or '',
    })


# ==========================================================
# BUAT PESANAN
# ==========================================================
@role_required('pelanggan')
def buat_pesanan(request, menu_id):
    menu = get_object_or_404(Menu, pk=menu_id)
    if menu.is_kosong:
        messages.error(request, "Menu ini sedang kosong dan tidak bisa dipesan.")
        return redirect('pelanggan:menu_list')

    if request.method == 'POST':
        form = PemesananForm(request.POST)
        if form.is_valid():
            pesanan = form.save(commit=False)
            pesanan.pelanggan = request.user
            pesanan.menu = menu
            pesanan.kode_pesanan = f"ORD-{request.user.id}-{Pesanan.objects.count() + 1:05d}"
            pesanan.total_harga = menu.harga_per_porsi * pesanan.jumlah_porsi
            pesanan.save()
            messages.success(request, "Pesanan berhasil dibuat. Silakan lanjutkan pembayaran.")
            return redirect('pelanggan:upload_pembayaran', pesanan_id=pesanan.id)
    else:
        form = PemesananForm(initial={'menu': menu})

    return render(request, 'pelanggan/pesanan_form.html', {'form': form, 'menu': menu})


# ==========================================================
# UPLOAD BUKTI PEMBAYARAN
# ==========================================================
@role_required('pelanggan')
def upload_pembayaran(request, pesanan_id):
    pesanan = get_object_or_404(Pesanan, pk=pesanan_id, pelanggan=request.user)

    if hasattr(pesanan, 'pembayaran'):
        messages.info(request, "Anda sudah mengunggah bukti pembayaran untuk pesanan ini.")
        return redirect('pelanggan:detail_pesanan', pesanan_id=pesanan.id)

    if request.method == 'POST':
        form = PembayaranForm(request.POST, request.FILES)
        if form.is_valid():
            pembayaran = form.save(commit=False)
            pembayaran.pesanan = pesanan
            pembayaran.save()
            messages.success(request, "Bukti pembayaran berhasil diunggah, menunggu verifikasi petugas.")
            return redirect('pelanggan:detail_pesanan', pesanan_id=pesanan.id)
    else:
        form = PembayaranForm(initial={'jumlah_bayar': pesanan.total_harga})

    return render(request, 'pelanggan/upload_pembayaran.html', {'form': form, 'pesanan': pesanan})


# ==========================================================
# RIWAYAT & DETAIL PESANAN
# ==========================================================
@role_required('pelanggan')
def riwayat_pesanan(request):
    pesanan = Pesanan.objects.filter(pelanggan=request.user).select_related('menu').order_by('-created_at')
    paginator = Paginator(pesanan, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'pelanggan/riwayat_pesanan.html', {'page_obj': page_obj})


@role_required('pelanggan')
def detail_pesanan(request, pesanan_id):
    pesanan = get_object_or_404(
        Pesanan.objects.select_related('menu'), pk=pesanan_id, pelanggan=request.user
    )
    pembayaran = getattr(pesanan, 'pembayaran', None)
    return render(request, 'pelanggan/detail_pesanan.html', {'pesanan': pesanan, 'pembayaran': pembayaran})