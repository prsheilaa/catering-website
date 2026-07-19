from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q

from .decorators import role_required
from .models import Menu, KategoriMenu, JenisCatering, Pesanan, Pembayaran
from .forms import MenuForm, KategoriMenuForm, JenisCateringForm, AkunForm

User = get_user_model()


# ==========================================================
# DASHBOARD
# ==========================================================
@role_required('administrator')
def dashboard(request):
    context = {
        'total_menu': Menu.objects.count(),
        'total_pesanan': Pesanan.objects.count(),
        'pesanan_menunggu': Pesanan.objects.filter(status=Pesanan.StatusPesanan.MENUNGGU_PEMBAYARAN).count(),
        'pesanan_diproses': Pesanan.objects.filter(status=Pesanan.StatusPesanan.DIPROSES).count(),
        'pesanan_selesai': Pesanan.objects.filter(status=Pesanan.StatusPesanan.SELESAI).count(),
        'total_pelanggan': User.objects.filter(role=User.Role.PELANGGAN).count(),
        'pelanggan_pending': User.objects.filter(role=User.Role.PELANGGAN, is_approved=False).count(),
    }
    return render(request, 'administrator/dashboard.html', context)


# ==========================================================
# KELOLA KATEGORI MENU
# ==========================================================
@role_required('administrator')
def kategori_list(request):
    kategori = KategoriMenu.objects.all().order_by('nama')

    q = request.GET.get('q')
    if q:
        kategori = kategori.filter(
            Q(nama__icontains=q) |
            Q(deskripsi__icontains=q)
        )

    paginator = Paginator(kategori, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'administrator/kategori_list.html',
        {
            'page_obj': page_obj,
            'q': q or ''
        }
    )


@role_required('administrator')
def kategori_form(request, pk=None):
    instance = get_object_or_404(KategoriMenu, pk=pk) if pk else None
    if request.method == 'POST':
        form = KategoriMenuForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kategori berhasil disimpan.')
            return redirect('administrator:kategori_list')
    else:
        form = KategoriMenuForm(instance=instance)
    return render(request, 'administrator/kategori_form.html', {'form': form})


@role_required('administrator')
def kategori_delete(request, pk):
    kategori = get_object_or_404(KategoriMenu, pk=pk)
    kategori.delete()
    messages.success(request, 'Kategori berhasil dihapus.')
    return redirect('administrator:kategori_list')


# ==========================================================
# KELOLA JENIS CATERING
# ==========================================================
@role_required('administrator')
def jenis_catering_list(request):
    jenis = JenisCatering.objects.all().order_by('nama')

    q = request.GET.get('q')
    if q:
        jenis = jenis.filter(
            Q(nama__icontains=q) |
            Q(deskripsi__icontains=q)
        )

    paginator = Paginator(jenis, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'administrator/jenis_catering_list.html',
        {
            'page_obj': page_obj,
            'q': q or ''
        }
    )

@role_required('administrator')
def jenis_catering_form(request, pk=None):
    instance = get_object_or_404(JenisCatering, pk=pk) if pk else None
    if request.method == 'POST':
        form = JenisCateringForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Jenis catering berhasil disimpan.')
            return redirect('administrator:jenis_catering_list')
    else:
        form = JenisCateringForm(instance=instance)
    return render(request, 'administrator/jenis_catering_form.html', {'form': form})


@role_required('administrator')
def jenis_catering_delete(request, pk):
    jenis = get_object_or_404(JenisCatering, pk=pk)
    jenis.delete()
    messages.success(request, 'Jenis catering berhasil dihapus.')
    return redirect('administrator:jenis_catering_list')


# ==========================================================
# KELOLA MENU
# ==========================================================
@role_required('administrator')
def menu_list(request):
    menu = Menu.objects.select_related('kategori', 'jenis_catering').order_by('-created_at')
    q = request.GET.get('q')
    if q:
        menu = menu.filter(Q(nama_paket__icontains=q) | Q(kategori__nama__icontains=q))
    paginator = Paginator(menu, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'administrator/menu_list.html', {'page_obj': page_obj, 'q': q or ''})


@role_required('administrator')
def menu_form(request, pk=None):
    instance = get_object_or_404(Menu, pk=pk) if pk else None
    if request.method == 'POST':
        form = MenuForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            menu = form.save(commit=False)
            if not pk:
                menu.dibuat_oleh = request.user
            menu.save()
            messages.success(request, 'Menu berhasil disimpan.')
            return redirect('administrator:menu_list')
    else:
        form = MenuForm(instance=instance)
    return render(request, 'administrator/menu_form.html', {'form': form})


@role_required('administrator')
def menu_delete(request, pk):
    menu = get_object_or_404(Menu, pk=pk)
    menu.delete()
    messages.success(request, 'Menu berhasil dihapus.')
    return redirect('administrator:menu_list')


# ==========================================================
# KELOLA AKUN (petugas & PELANGGAN)
# ==========================================================
@role_required('administrator')
def akun_list(request):
    role_filter = request.GET.get('role', '')
    akun = User.objects.exclude(role=User.Role.ADMINISTRATOR).order_by('-date_joined')
    if role_filter:
        akun = akun.filter(role=role_filter)
    paginator = Paginator(akun, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'administrator/akun_list.html', {'page_obj': page_obj, 'role_filter': role_filter})


@role_required('administrator')
def akun_form(request, pk=None):
    instance = get_object_or_404(User, pk=pk) if pk else None
    if instance and instance.role == User.Role.ADMINISTRATOR:
        messages.error(request, "Akun administrator tidak bisa diedit lewat halaman ini.")
        return redirect('administrator:akun_list')

    if request.method == 'POST':
        form = AkunForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Akun berhasil disimpan.")
            return redirect('administrator:akun_list')
    else:
        form = AkunForm(instance=instance)

    return render(request, 'administrator/akun_form.html', {'form': form, 'instance': instance})


@role_required('administrator')
def akun_toggle_active(request, pk):
    """Aktifkan / nonaktifkan akun petugas atau pelanggan."""
    akun = get_object_or_404(User, pk=pk)
    akun.is_active = not akun.is_active
    akun.save(update_fields=['is_active'])
    messages.success(request, f"Akun {akun.username} berhasil {'diaktifkan' if akun.is_active else 'dinonaktifkan'}.")
    return redirect('administrator:akun_list')


@role_required('administrator')
def akun_delete(request, pk):
    akun = get_object_or_404(User, pk=pk)
    akun.delete()
    messages.success(request, 'Akun berhasil dihapus.')
    return redirect('administrator:akun_list')


# ==========================================================
# SELURUH TRANSAKSI
# ==========================================================
@role_required('administrator')
def transaksi_list(request):
    status_filter = request.GET.get('status', '')
    pesanan = Pesanan.objects.select_related('pelanggan', 'menu', 'pembayaran').order_by('-created_at')
    if status_filter:
        pesanan = pesanan.filter(status=status_filter)
    paginator = Paginator(pesanan, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'administrator/transaksi_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': Pesanan.StatusPesanan.choices,
    })


@role_required('administrator')
def transaksi_detail(request, pk):
    pesanan = get_object_or_404(Pesanan.objects.select_related('pelanggan', 'menu'), pk=pk)
    pembayaran = getattr(pesanan, 'pembayaran', None)
    return render(request, 'administrator/transaksi_detail.html', {
        'pesanan': pesanan,
        'pembayaran': pembayaran,
    })


# ==========================================================
# LAPORAN
# ==========================================================
@role_required('administrator')
def laporan(request):
    tanggal_awal = request.GET.get('tanggal_awal')
    tanggal_akhir = request.GET.get('tanggal_akhir')
    status_filter = request.GET.get('status', '')

    pesanan = Pesanan.objects.select_related('pelanggan', 'menu').order_by('-created_at')
    if tanggal_awal:
        pesanan = pesanan.filter(created_at__date__gte=tanggal_awal)
    if tanggal_akhir:
        pesanan = pesanan.filter(created_at__date__lte=tanggal_akhir)
    if status_filter:
        pesanan = pesanan.filter(status=status_filter)

    total_pendapatan = sum(
        p.total_harga for p in pesanan if p.status == Pesanan.StatusPesanan.SELESAI
    )

    return render(request, 'administrator/laporan.html', {
        'pesanan': pesanan,
        'total_pendapatan': total_pendapatan,
        'tanggal_awal': tanggal_awal or '',
        'tanggal_akhir': tanggal_akhir or '',
        'status_filter': status_filter,
        'status_choices': Pesanan.StatusPesanan.choices,
    })


@role_required('administrator')
def laporan_download_pdf(request):
    """
    Placeholder export PDF. Nanti diisi pakai library seperti WeasyPrint / ReportLab,
    ambil queryset yang sama seperti view laporan() di atas.
    """
    # TODO: implementasi export PDF
    return redirect('administrator:laporan')


@role_required('administrator')
def laporan_download_excel(request):
    """
    Placeholder export Excel. Nanti diisi pakai openpyxl.
    """
    # TODO: implementasi export Excel
    return redirect('administrator:laporan')