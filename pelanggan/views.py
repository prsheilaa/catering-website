from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

from administrator.decorators import role_required
from administrator.models import (
    Menu, KategoriMenu, JenisCatering, Pesanan, Pembayaran, ItemPesanan, PengaturanPemesanan, PengaturanDP,
    BANK_NAME, EWALLET_PROVIDER, EWALLET_NUMBER, EWALLET_ACCOUNT_NAME, QRIS_MERCHANT_NAME,
)
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

         # ----- VALIDASI JEDA WAKTU MINIMAL (H-) PEMESANAN -----
        waktu_acara_dt = parse_datetime(waktu_acara)
        if waktu_acara_dt is None:
            messages.error(request, "Format waktu acara tidak valid.")
            return redirect('pelanggan:buat_pesanan')
        if timezone.is_naive(waktu_acara_dt):
            waktu_acara_dt = timezone.make_aware(waktu_acara_dt, timezone.get_current_timezone())

        pengaturan = PengaturanPemesanan.get_settings()
        minimal_hari = pengaturan.get_minimal_hari()
        batas_tercepat = pengaturan.batas_waktu_tercepat()

        if waktu_acara_dt < batas_tercepat:
            messages.error(
                request,
                f"Mohon maaf, saat ini kami membutuhkan waktu persiapan minimal H-{minimal_hari} "
                f"({'karena banyak pesanan yang harus kami proses' if pengaturan.mode_otomatis else 'sesuai ketentuan yang berlaku'}). "
                f"Silakan pilih waktu acara mulai {timezone.localtime(batas_tercepat).strftime('%d %b %Y, %H:%M')} atau setelahnya."
            )
            return redirect('pelanggan:buat_pesanan')
        paket_valid = [nilai for nilai, _ in PAKET_PORSI_CHOICES]

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

        # ----- SNAPSHOT PENGATURAN DP SAAT INI -----
        pengaturan_dp = PengaturanDP.get_settings()

        pesanan = Pesanan.objects.create(
            kode_pesanan=f"ORD-{request.user.id}-{Pesanan.objects.count() + 1:05d}",
            pelanggan=request.user,
            menu=item_data[0][0],           # menu utama, untuk kompatibilitas fitur lama
            jenis_catering_id=jenis_catering_id,
            nama_pemesan=nama_pemesan,
            alamat=alamat,
            no_telepon=no_telepon,
            waktu_acara=waktu_acara_dt,
            jumlah_porsi=item_data[0][1],   # untuk kompatibilitas fitur lama
            catatan_tambahan=catatan_tambahan,
            total_harga=total_harga,
            wajib_dp=pengaturan_dp.wajib_dp,
            persen_dp=pengaturan_dp.persen_dp if pengaturan_dp.wajib_dp else None,
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

    pengaturan = PengaturanPemesanan.get_settings()
    minimal_hari = pengaturan.get_minimal_hari()
    batas_tercepat = pengaturan.batas_waktu_tercepat()

    return render(request, 'pelanggan/pesanan_form.html', {
        'kategori_list': KategoriMenu.objects.filter(is_active=True),
        'menu_tersedia': menu_tersedia,
        'jenis_list': JenisCatering.objects.filter(is_active=True),
        'paket_pilihan': PAKET_PORSI_CHOICES,
        'default_nama': request.user.get_full_name() or request.user.username,
        'default_telepon': request.user.no_telepon,
        'minimal_hari_pemesanan': minimal_hari,
        'batas_waktu_tercepat': timezone.localtime(batas_tercepat).strftime('%Y-%m-%dT%H:%M'),
    })

# ==========================================================
# UPLOAD BUKTI PEMBAYARAN
# ==========================================================
@role_required('pelanggan')
def upload_pembayaran(request, pesanan_id):
    pesanan = get_object_or_404(Pesanan, pk=pesanan_id, pelanggan=request.user)

    info = pesanan.pembayaran_yang_diperlukan()

    if info is None:
        if pesanan.is_lunas:
            messages.info(request, "Pesanan ini sudah lunas. Tidak perlu unggah pembayaran lagi.")
        else:
            messages.info(request, "Bukti pembayaran Anda sedang menunggu verifikasi petugas.")
        return redirect('pelanggan:detail_pesanan', pesanan_id=pesanan.id)

    if request.method == 'POST':
        form = PembayaranForm(request.POST, request.FILES, jumlah_minimal=info['jumlah'])
        if form.is_valid():
            pembayaran = form.save(commit=False)
            pembayaran.pesanan = pesanan
            pembayaran.jenis = info['jenis']
            pembayaran.save()

            if info['jenis'] == Pembayaran.JenisPembayaran.DP:
                pesanan.status_pembayaran = Pesanan.StatusPembayaran.DP_MENUNGGU_VERIFIKASI
            else:
                pesanan.status_pembayaran = Pesanan.StatusPembayaran.PELUNASAN_MENUNGGU_VERIFIKASI
            pesanan.save(update_fields=['status_pembayaran'])

            messages.success(request, "Bukti pembayaran berhasil diunggah, menunggu verifikasi petugas.")
            return redirect('pelanggan:detail_pesanan', pesanan_id=pesanan.id)
    else:
        form = PembayaranForm(initial={'jumlah_bayar': info['jumlah']}, jumlah_minimal=info['jumlah'])

    return render(request, 'pelanggan/upload_pembayaran.html', {
        'form': form,
        'pesanan': pesanan,
        'info_pembayaran': info,
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
    pesanan_qs = Pesanan.objects.filter(pelanggan=request.user).select_related(
        'menu', 'jenis_catering'
    ).prefetch_related('item_list__menu', 'pembayaran_list').order_by('-created_at')

    status = request.GET.get('status')
    if status:
        pesanan_qs = pesanan_qs.filter(status=status)

    paginator = Paginator(pesanan_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    semua_pesanan = Pesanan.objects.filter(pelanggan=request.user)
    status_tabs = [
        (value, label, semua_pesanan.filter(status=value).count())
        for value, label in Pesanan.StatusPesanan.choices
    ]

    return render(request, 'pelanggan/riwayat_pesanan.html', {
        'page_obj': page_obj,
        'status_choices': Pesanan.StatusPesanan.choices,
        'status': status or '',
        'status_tabs': status_tabs,
        'total_pesanan_count': semua_pesanan.count(),
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
        Pesanan.objects.select_related('menu', 'jenis_catering').prefetch_related(
            'item_list__menu', 'pembayaran_list'
        ),
        pk=pesanan_id, pelanggan=request.user
    )
    riwayat_pembayaran = pesanan.pembayaran_list.all().order_by('-created_at')
    info_pembayaran = pesanan.pembayaran_yang_diperlukan()
    return render(request, 'pelanggan/detail_pesanan.html', {
        'pesanan': pesanan,
        'riwayat_pembayaran': riwayat_pembayaran,
        'info_pembayaran': info_pembayaran,
        'bank_name': BANK_NAME,
        'ewallet_provider': EWALLET_PROVIDER,
        'ewallet_number': EWALLET_NUMBER,
        'qris_merchant_name': QRIS_MERCHANT_NAME,
    })


@role_required('pelanggan')
def unduh_struk(request, pesanan_id):
    """Membuat & mengunduh struk pesanan dalam bentuk PDF."""
    pesanan = get_object_or_404(
        Pesanan.objects.select_related('menu', 'jenis_catering').prefetch_related(
            'item_list__menu', 'pembayaran_list'
        ),
        pk=pesanan_id, pelanggan=request.user
    )
    daftar_pembayaran = list(pesanan.pembayaran_list.all().order_by('created_at'))
    pembayaran = getattr(pesanan, 'pembayaran', None)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=22 * mm, bottomMargin=18 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BrandTitle', fontSize=18, leading=22, textColor=colors.HexColor('#B23A24'), fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='StrukSub', fontSize=10, textColor=colors.HexColor('#6E6455')))
    styles.add(ParagraphStyle(name='SectionHead', fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#241A10'), spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle(name='Right', parent=styles['Normal'], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='CenterMuted', parent=styles['Normal'], alignment=TA_CENTER, textColor=colors.HexColor('#6E6455'), fontSize=9))

    story = []
    story.append(Paragraph("Meja Nusantara", styles['BrandTitle']))
    story.append(Paragraph("Struk Pesanan Katering", styles['StrukSub']))
    story.append(Spacer(1, 10))

    status_label = pesanan.get_status_display()
    header_data = [
        ["Kode Pesanan", pesanan.kode_pesanan, "Status", status_label],
        ["Tanggal Pesan", pesanan.created_at.strftime('%d %b %Y, %H:%M'), "Waktu Acara", pesanan.waktu_acara.strftime('%d %b %Y, %H:%M')],
    ]
    header_table = Table(header_data, colWidths=[85, 140, 70, 140])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6E6455')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#6E6455')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)

    story.append(Paragraph("Detail Pemesan", styles['SectionHead']))
    pemesan_data = [
        ["Nama Pemesan", pesanan.nama_pemesan],
        ["No. Telepon", pesanan.no_telepon],
        ["Alamat", pesanan.alamat],
        ["Jenis Catering", pesanan.jenis_catering.nama],
    ]
    pemesan_table = Table(pemesan_data, colWidths=[110, 335])
    pemesan_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(pemesan_table)

    story.append(Paragraph("Rincian Menu", styles['SectionHead']))
    item_rows = [["Menu", "Porsi", "Subtotal"]]
    items = pesanan.item_list.all()
    if items:
        for item in items:
            item_rows.append([item.menu.nama_paket, str(item.jumlah_porsi), f"Rp{item.subtotal:,.0f}".replace(',', '.')])
    else:
        item_rows.append([pesanan.menu.nama_paket, str(pesanan.jumlah_porsi), f"Rp{pesanan.total_harga:,.0f}".replace(',', '.')])

    item_table = Table(item_rows, colWidths=[280, 60, 105])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#241A10')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FBF4EA')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E7DCC9')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(item_table)

    total_data = [["Total Pembayaran", f"Rp{pesanan.total_harga:,.0f}".replace(',', '.')]]
    if pesanan.wajib_dp:
        total_data.append([f"DP ({pesanan.persen_dp}%)", f"Rp{pesanan.jumlah_dp:,.0f}".replace(',', '.')])
    total_table = Table(total_data, colWidths=[340, 105])
    total_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#B23A24')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#241A10')),
    ]))
    story.append(total_table)

    story.append(Paragraph("Informasi Pembayaran", styles['SectionHead']))
    if daftar_pembayaran:
        bayar_data = [["Jenis", "Metode", "Jumlah", "Status"]]
        for p in daftar_pembayaran:
            bayar_data.append([
                p.get_jenis_display(),
                p.get_metode_display(),
                f"Rp{p.jumlah_bayar:,.0f}".replace(',', '.'),
                p.get_status_verifikasi_display(),
            ])
        bayar_table = Table(bayar_data, colWidths=[110, 110, 110, 115])
        bayar_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#241A10')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E7DCC9')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(bayar_table)
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"Total dibayar (terverifikasi): Rp{pesanan.total_dibayar:,.0f}".replace(',', '.') +
            f" | Sisa: Rp{pesanan.sisa_bayar:,.0f}".replace(',', '.'),
            styles['StrukSub']
        ))
    else:
        bayar_data = [["Status", "Belum ada pembayaran tercatat untuk pesanan ini."]]
        bayar_table = Table(bayar_data, colWidths=[110, 335])
        bayar_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9.5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(bayar_table)
    if pembayaran:
        metode = pembayaran.get_metode_display()
        if pembayaran.metode == 'transfer_bank':
            tujuan = f"VA {pesanan.virtual_account_number} — {BANK_NAME}"
        elif pembayaran.metode == 'e_wallet':
            tujuan = f"{EWALLET_PROVIDER} {EWALLET_NUMBER}"
        elif pembayaran.metode == 'qris':
            tujuan = f"QRIS — {QRIS_MERCHANT_NAME}"
        else:
            tujuan = "Dibayar tunai di tempat"

        bayar_data = [
            ["Metode Pembayaran", metode],
            ["Tujuan Pembayaran", tujuan],
            ["Status Verifikasi", pembayaran.get_status_verifikasi_display()],
            ["Jumlah Dibayar", f"Rp{pembayaran.jumlah_bayar:,.0f}".replace(',', '.')],
        ]
    else:
        bayar_data = [["Status", "Belum ada pembayaran tercatat untuk pesanan ini."]]

    bayar_table = Table(bayar_data, colWidths=[110, 335])
    bayar_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(bayar_table)

    story.append(Spacer(1, 22))
    story.append(Paragraph(
        "Struk ini dibuat otomatis oleh sistem Meja Nusantara dan sah tanpa tanda tangan basah.",
        styles['CenterMuted']
    ))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="struk-{pesanan.kode_pesanan}.pdf"'
    return response


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