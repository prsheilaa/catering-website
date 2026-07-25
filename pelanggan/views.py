from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator

from administrator.decorators import role_required
from administrator.models import Menu, KategoriMenu, JenisCatering, Pesanan, Pembayaran, ItemPesanan, BANK_NAME, EWALLET_PROVIDER, EWALLET_NUMBER, EWALLET_ACCOUNT_NAME, QRIS_MERCHANT_NAME
from .forms import RegistrasiPelangganForm, PembayaranForm

PAKET_PORSI_CHOICES = [
    (50, "Paket 50 Pax"),
    (75, "Paket 75 Pax"),
    (100, "Paket 100 Pax"),
    (150, "Paket 150 Pax"),
    (200, "Paket 200 Pax"),
    (250, "Paket 250 Pax"),
    (300, "Paket 300 Pax"),
    (500, "Paket 500 Pax"),
]
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
        'rekomendasi_menu': Menu.objects.filter(
            status_stok=Menu.StatusStok.TERSEDIA
        ).select_related('kategori').order_by('-id')[:3],
    }
    return render(request, 'pelanggan/dashboard.html', context)


# ==========================================================
# KATALOG MENU (daftar & detail)
# ==========================================================
@role_required('pelanggan')
def menu_list(request):
    menu_qs = Menu.objects.filter(
        status_stok=Menu.StatusStok.TERSEDIA
    ).select_related('kategori', 'jenis_catering').order_by('kategori__nama', 'nama_paket')

    kategori_id = request.GET.get('kategori', '')
    jenis_id = request.GET.get('jenis', '')
    q = request.GET.get('q', '').strip()

    if kategori_id:
        menu_qs = menu_qs.filter(kategori_id=kategori_id)
    if jenis_id:
        menu_qs = menu_qs.filter(jenis_catering_id=jenis_id)
    if q:
        menu_qs = menu_qs.filter(nama_paket__icontains=q)

    paginator = Paginator(menu_qs, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'pelanggan/menu_list.html', {
        'page_obj': page_obj,
        'kategori_list': KategoriMenu.objects.filter(is_active=True),
        'jenis_list': JenisCatering.objects.filter(is_active=True),
        'kategori_id': kategori_id,
        'jenis_id': jenis_id,
        'q': q,
    })


@role_required('pelanggan')
def menu_detail(request, menu_id):
    menu = get_object_or_404(
        Menu.objects.select_related('kategori', 'jenis_catering'), pk=menu_id
    )
    menu_terkait = Menu.objects.filter(
        kategori=menu.kategori, status_stok=Menu.StatusStok.TERSEDIA
    ).exclude(pk=menu.pk).select_related('kategori')[:3]

    return render(request, 'pelanggan/menu_detail.html', {
        'menu': menu,
        'menu_terkait': menu_terkait,
        'paket_pilihan': PAKET_PORSI_CHOICES,
    })


# ==========================================================
# 3. FORM PEMESANAN (total harga dihitung otomatis)
# ==========================================================
@role_required('pelanggan')
def buat_pesanan(request):
    menu_tersedia = Menu.objects.filter(
        status_stok=Menu.StatusStok.TERSEDIA
    ).select_related('kategori')

    if request.method == 'POST':
        menu_ids = request.POST.getlist('item_menu')
        if not menu_ids:
            messages.error(request, "Pilih minimal satu menu.")
            return redirect('pelanggan:buat_pesanan')

        jenis_catering_id = request.POST.get('jenis_catering')
        nama_pemesan = request.POST.get('nama_pemesan', '').strip()
        alamat = request.POST.get('alamat', '').strip()
        no_telepon = request.POST.get('no_telepon', '').strip()
        waktu_acara = request.POST.get('waktu_acara')
        catatan_tambahan = request.POST.get('catatan_tambahan', '').strip()

        if not all([jenis_catering_id, nama_pemesan, alamat, no_telepon, waktu_acara]):
            messages.error(request, "Semua field wajib diisi.")
            return redirect('pelanggan:buat_pesanan')

        paket_valid = [nilai for nilai, _ in PAKET_PORSI_CHOICES]
        item_data = []  # akan diisi list (menu, jumlah_porsi)

        for menu_id in menu_ids:
            menu = menu_tersedia.filter(pk=menu_id).first()
            if not menu:
                messages.error(request, "Salah satu menu yang dipilih sudah tidak tersedia. Silakan pilih ulang.")
                return redirect('pelanggan:buat_pesanan')

            try:
                jumlah_porsi = int(request.POST.get(f'paket_{menu_id}', 0))
                if jumlah_porsi not in paket_valid:
                    raise ValueError
            except (TypeError, ValueError):
                messages.error(request, f"Paket porsi untuk {menu.nama_paket} belum dipilih dengan benar.")
                return redirect('pelanggan:buat_pesanan')

            item_data.append((menu, jumlah_porsi))

        # ----- HITUNG TOTAL HARGA OTOMATIS (dari semua menu yang dipilih) -----
        total_harga = sum(menu.harga_per_porsi * jumlah for menu, jumlah in item_data)

        pesanan = Pesanan.objects.create(
            kode_pesanan=f"ORD-{request.user.id}-{Pesanan.objects.count() + 1:05d}",
            pelanggan=request.user,
            menu=item_data[0][0],           # menu utama, untuk kompatibilitas fitur lama
            jenis_catering_id=jenis_catering_id,
            nama_pemesan=nama_pemesan,
            alamat=alamat,
            no_telepon=no_telepon,
            waktu_acara=waktu_acara,
            jumlah_porsi=item_data[0][1],   # untuk kompatibilitas fitur lama
            catatan_tambahan=catatan_tambahan,
            total_harga=total_harga,
        )

        for menu, jumlah in item_data:
            ItemPesanan.objects.create(
                pesanan=pesanan,
                menu=menu,
                jumlah_porsi=jumlah,
                subtotal=menu.harga_per_porsi * jumlah,
            )

        messages.success(request, "Pesanan berhasil dibuat. Silakan lanjutkan pembayaran.")
        return redirect('pelanggan:upload_pembayaran', pesanan_id=pesanan.id)

    try:
        preselect_menu_id = int(request.GET.get('menu', 0))
    except (TypeError, ValueError):
        preselect_menu_id = 0

    return render(request, 'pelanggan/pesanan_form.html', {
        'kategori_list': KategoriMenu.objects.filter(is_active=True),
        'menu_tersedia': menu_tersedia,
        'jenis_list': JenisCatering.objects.filter(is_active=True),
        'paket_pilihan': PAKET_PORSI_CHOICES,
        'default_nama': request.user.get_full_name() or request.user.username,
        'default_telepon': request.user.no_telepon,
        'default_alamat': request.user.alamat,
        'preselect_menu_id': preselect_menu_id,
    })

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

    return render(request, 'pelanggan/upload_pembayaran.html', {
        'form': form,
        'pesanan': pesanan,
        'bank_name': BANK_NAME,
        'ewallet_provider': EWALLET_PROVIDER,
        'ewallet_number': EWALLET_NUMBER,
        'ewallet_account_name': EWALLET_ACCOUNT_NAME,
        'qris_merchant_name': QRIS_MERCHANT_NAME,
    })


# ==========================================================
# 4. RIWAYAT PESANAN PELANGGAN
# ==========================================================
@role_required('pelanggan')
def riwayat_pesanan(request):
    pesanan_qs = Pesanan.objects.filter(pelanggan=request.user).select_related('menu').order_by('-created_at')

    status = request.GET.get('status')
    if status:
        pesanan_qs = pesanan_qs.filter(status=status)

    paginator = Paginator(pesanan_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'pelanggan/riwayat_pesanan.html', {
        'page_obj': page_obj,
        'status_choices': Pesanan.StatusPesanan.choices,
        'status': status or '',
        'bank_name': BANK_NAME,
        'ewallet_provider': EWALLET_PROVIDER,
        'ewallet_number': EWALLET_NUMBER,
        'qris_merchant_name': QRIS_MERCHANT_NAME,
    })


# ==========================================================
# 5. DETAIL & STATUS PESANAN
# ==========================================================
@role_required('pelanggan')
def detail_pesanan(request, pesanan_id):
    pesanan = get_object_or_404(
        Pesanan.objects.select_related('menu', 'jenis_catering').prefetch_related('item_list__menu'),
        pk=pesanan_id, pelanggan=request.user
    )
    pembayaran = getattr(pesanan, 'pembayaran', None)
    return render(request, 'pelanggan/detail_pesanan.html', {
        'pesanan': pesanan,
        'pembayaran': pembayaran,
        'bank_name': BANK_NAME,
        'ewallet_provider': EWALLET_PROVIDER,
        'ewallet_number': EWALLET_NUMBER,
        'qris_merchant_name': QRIS_MERCHANT_NAME,
    })

@role_required('pelanggan')
def batalkan_pesanan(request, pesanan_id):
    pesanan = get_object_or_404(Pesanan, pk=pesanan_id, pelanggan=request.user)

    if request.method != 'POST':
        return redirect('pelanggan:detail_pesanan', pesanan_id=pesanan.id)

    if pesanan.status not in [Pesanan.StatusPesanan.MENUNGGU_PEMBAYARAN, Pesanan.StatusPesanan.DIPROSES]:
        messages.error(request, "Pesanan ini sudah tidak bisa dibatalkan.")
        return redirect('pelanggan:detail_pesanan', pesanan_id=pesanan.id)

    pesanan.status = Pesanan.StatusPesanan.DIBATALKAN
    pesanan.save(update_fields=['status'])
    messages.success(request, f"Pesanan {pesanan.kode_pesanan} berhasil dibatalkan.")
    return redirect('pelanggan:detail_pesanan', pesanan_id=pesanan.id)