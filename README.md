# Meja Nusantara — Aplikasi Web Katering

Meja Nusantara adalah aplikasi web pemesanan katering berbasis Django dengan tiga
peran pengguna: **Administrator**, **Petugas**, dan **Pelanggan**. Pelanggan dapat
menjelajahi katalog menu, membuat pesanan, mengunggah bukti pembayaran, memantau
riwayat pesanan, hingga mengunduh struk pesanan. Administrator mengelola data
menu, kategori, dan jenis katering, sedangkan Petugas menangani persetujuan
registrasi pelanggan, verifikasi pembayaran, dan pemrosesan pesanan.

## Daftar Anggota Kelompok

| Nama                      | NIM          |   Username GitHub     |
|---------------------------|--------------|-----------------------|
| Lisa Aprilia Pramysheila  | [2421400107] |       prsheilaa       |
|      Nur Hidayati         | [2421400146] |     nurhidayati146    |
|     Tatiatun Sadiah       | [2421400111] |   tatiatunsadiah-bit  |
|  Naylah Zakiyatur Rohmah  | [2421400107] | NaylahZakiyaturRohmah |
|  Zulfiana Naila Rofikoh   | [2421400078] | zulfiananailarofikoh  |

## Pembagian Tugas

1. Lisa Aprilia Pramysheila (Project Leader)
Setup awal proyek Django (struktur project & apps), desain UI/UX login & dashboard, pengembangan modul pemesanan & riwayat pemesanan pelanggan, pengembangan fitur opsi/metode pembayaran, serta penggabungan (merge) pekerjaan seluruh anggota ke branch utama.
2. Nur Hidayati
Pengembangan modul CRUD Administrator, Kelola kategori menu, jenis catering, dan menu catering,Tampilan filter verdasarkan kategori/jenis
3. Tatiatun Sadiah
Pengembangan modul pembayaran pada sisi petugas, Membuat halaman verifikasi pembayaran, Membuat halaman Riwayat pembayaran
4. Naylah Zakiyatur Rohmah
Membuat laporan penjualan di administrator
Membuat transaksi di administrator
Menbahkan navbar dan footer
testing
5. Zulfiana
Membuat daftar menu pada sisi pelanggan
Membuatkan detail menu

## Teknologi yang Digunakan

- **Bahasa & Framework**: Python 3, Django 6
- **Database**: SQLite (default, untuk pengembangan lokal)
- **Frontend**: HTML, CSS (kustom, tanpa framework CSS pihak ketiga), JavaScript vanilla
- **Font**: Fraunces, Plus Jakarta Sans (Google Fonts)
- **Library tambahan**:
  - `Pillow` — pemrosesan gambar (foto menu, bukti pembayaran)
  - `reportlab` — pembuatan struk pesanan dalam format PDF

## Fitur Utama

**Pelanggan**
- Registrasi & login (dengan persetujuan petugas)
- Jelajahi katalog menu dengan filter kategori
- Buat pesanan multi-menu dengan ringkasan harga otomatis
- Upload bukti pembayaran (Transfer Bank/VA, E-Wallet, QRIS, atau Tunai)
- Riwayat pesanan dengan filter status dan detail tujuan pembayaran
- Unduh struk pesanan dalam format PDF

**Petugas**
- Approval registrasi pelanggan baru
- Verifikasi bukti pembayaran
- Pemrosesan status pesanan

**Administrator**
- CRUD menu, kategori menu, dan jenis catering
- Manajemen akun pengguna
- Dashboard ringkasan pesanan & pembayaran
- Laporan penjualan (export PDF atau Excell)
- pengaturan (mengatur jeda waktu pemesanan dan Dp)

## Cara Instalasi

1. Clone repository:
   '''bash
   git clone https://github.com/prsheilaa/catering-website.git

2. masuk ke folder
   cd catering-website

3. Buat dan aktifkan virtual environment (opsional tapi disarankan):
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
   ```
4. Install seluruh dependency:
   ```bash
   pip install -r requirements.txt

## Cara Menjalankan Aplikasi

1. Jalankan migrasi database:
   ```bash
   python manage.py migrate
   ```
2. (Opsional) Buat akun superuser untuk login ke Django admin bawaan:
   ```bash
   python manage.py createsuperuser
   ```
3. Jalankan server pengembangan:
   ```bash
   python manage.py runserver
   ```
4. Buka browser ke `http://127.0.0.1:8000/`

## Akun Pengujian

|     Peran     |    Username   |    Password    |
|---------------|---------------|----------------|
| Administrator | administrator | kacanghijau31  |
|   Petugas     |    petugas    | kacanghijau31  |
|   Pelanggan   |   lisaprams   | KacangHijau31* |