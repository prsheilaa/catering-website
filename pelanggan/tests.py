from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class RegistrasiTest(TestCase):
    def test_registrasi_berhasil_membuat_akun_pelanggan_belum_approved(self):
        response = self.client.post(reverse('pelanggan:register'), {
            'nama_lengkap': 'Budi Santoso',
            'username': 'budi123',
            'email': 'budi@example.com',
            'no_telepon': '08123456789',
            'password1': 'PasswordKuat123!',
            'password2': 'PasswordKuat123!',
        })
        self.assertEqual(response.status_code, 302)  # redirect ke login
        user = User.objects.get(username='budi123')
        self.assertEqual(user.role, User.Role.PELANGGAN)
        self.assertFalse(user.is_approved)
        self.assertEqual(user.first_name, 'Budi Santoso')
        self.assertEqual(user.status_akun, 'Menunggu Persetujuan')

    def test_registrasi_gagal_jika_password_tidak_cocok(self):
        response = self.client.post(reverse('pelanggan:register'), {
            'nama_lengkap': 'Budi Santoso',
            'username': 'budi456',
            'email': 'budi456@example.com',
            'no_telepon': '08123456789',
            'password1': 'PasswordKuat123!',
            'password2': 'PasswordBeda456!',
        })
        self.assertEqual(response.status_code, 200)  # tetap di halaman form (tidak redirect)
        self.assertFalse(User.objects.filter(username='budi456').exists())

    def test_registrasi_gagal_jika_username_sudah_dipakai(self):
        User.objects.create_user(username='sudahada', password='rahasia123', role=User.Role.PELANGGAN)
        response = self.client.post(reverse('pelanggan:register'), {
            'nama_lengkap': 'Budi Santoso',
            'username': 'sudahada',
            'email': 'baru@example.com',
            'no_telepon': '08123456789',
            'password1': 'PasswordKuat123!',
            'password2': 'PasswordKuat123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='sudahada').count(), 1)


class LoginLogoutTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.pelanggan_belum_approved = User.objects.create_user(
            username='pelanggan_baru', password='rahasia123', role=User.Role.PELANGGAN, is_approved=False
        )
        self.pelanggan_approved = User.objects.create_user(
            username='pelanggan_lama', password='rahasia123', role=User.Role.PELANGGAN, is_approved=True
        )
        self.petugas = User.objects.create_user(
            username='petugas1', password='rahasia123', role=User.Role.petugas
        )
        self.admin = User.objects.create_superuser(
            username='admin1', password='rahasia123', email='admin1@example.com'
        )

    def test_pelanggan_belum_approved_tidak_bisa_login(self):
        response = self.client.post(reverse('pelanggan:login'), {
            'username': 'pelanggan_baru', 'password': 'rahasia123',
        })
        self.assertRedirects(response, reverse('pelanggan:login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_pelanggan_approved_bisa_login_dan_redirect_ke_menu(self):
        response = self.client.post(reverse('pelanggan:login'), {
            'username': 'pelanggan_lama', 'password': 'rahasia123',
        })
        self.assertRedirects(response, reverse('pelanggan:menu_list'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_petugas_bisa_login_tanpa_approval_dan_redirect_ke_dashboard_petugas(self):
        response = self.client.post(reverse('pelanggan:login'), {
            'username': 'petugas1', 'password': 'rahasia123',
        })
        self.assertRedirects(response, reverse('petugas:dashboard'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_administrator_login_redirect_ke_dashboard_administrator(self):
        response = self.client.post(reverse('pelanggan:login'), {
            'username': 'admin1', 'password': 'rahasia123',
        })
        self.assertRedirects(response, reverse('administrator:dashboard'))

    def test_superuser_otomatis_role_administrator_dan_approved(self):
        self.assertEqual(self.admin.role, User.Role.ADMINISTRATOR)
        self.assertTrue(self.admin.is_approved)

    def test_login_salah_password_gagal(self):
        response = self.client.post(reverse('pelanggan:login'), {
            'username': 'petugas1', 'password': 'salah',
        })
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_menghapus_session(self):
        self.client.login(username='pelanggan_lama', password='rahasia123')
        self.assertIn('_auth_user_id', self.client.session)
        response = self.client.get(reverse('pelanggan:logout'))
        self.assertRedirects(response, reverse('pelanggan:login'))
        self.assertNotIn('_auth_user_id', self.client.session)


class ApprovalTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.petugas = User.objects.create_user(
            username='petugas1', password='rahasia123', role=User.Role.petugas
        )
        self.pelanggan = User.objects.create_user(
            username='pelanggan_baru', password='rahasia123', role=User.Role.PELANGGAN, is_approved=False
        )

    def test_petugas_bisa_approve_pelanggan(self):
        self.client.login(username='petugas1', password='rahasia123')
        self.client.post(reverse('petugas:approve_pelanggan', args=[self.pelanggan.pk]))
        self.pelanggan.refresh_from_db()
        self.assertTrue(self.pelanggan.is_approved)
        self.assertEqual(self.pelanggan.approved_by, self.petugas)
        self.assertEqual(self.pelanggan.status_akun, 'Aktif')

    def test_petugas_bisa_tolak_pelanggan(self):
        self.client.login(username='petugas1', password='rahasia123')
        self.client.post(reverse('petugas:tolak_pelanggan', args=[self.pelanggan.pk]))
        self.assertFalse(User.objects.filter(pk=self.pelanggan.pk).exists())

    def test_pelanggan_yang_sudah_disetujui_bisa_login(self):
        self.client.login(username='petugas1', password='rahasia123')
        self.client.post(reverse('petugas:approve_pelanggan', args=[self.pelanggan.pk]))
        self.client.logout()

        response = self.client.post(reverse('pelanggan:login'), {
            'username': 'pelanggan_baru', 'password': 'rahasia123',
        })
        self.assertIn('_auth_user_id', self.client.session)

    def test_pelanggan_tidak_bisa_akses_halaman_approval(self):
        self.pelanggan.is_approved = True
        self.pelanggan.save()
        self.client.login(username='pelanggan_baru', password='rahasia123')
        response = self.client.get(reverse('petugas:pelanggan_pending'))
        self.assertEqual(response.status_code, 403)

    def test_pengunjung_anonim_tidak_bisa_akses_halaman_approval(self):
        response = self.client.get(reverse('petugas:pelanggan_pending'))
        self.assertNotEqual(response.status_code, 200)