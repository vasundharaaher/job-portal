import io
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import UserMaster, Candidate, Company, JobDetails, ApplyList


class JobPortalAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Register a test company
        self.company_user = UserMaster.objects.create(
            email='techcorp@example.com',
            role='Company',
            otp=123456,
            password='hashed_dummy_password',
            is_verified=True,
        )
        self.company = Company.objects.create(
            user_id=self.company_user,
            is_approved=True,
            firstname='Alice',
            lastname='Smith',
            company_name='TechCorp',
            city='New York',
        )

        # Register a test candidate
        self.candidate_user = UserMaster.objects.create(
            email='dev@example.com',
            role='Candidate',
            otp=654321,
            password='hashed_dummy_password',
            is_verified=True,
        )
        self.candidate = Candidate.objects.create(
            user_id=self.candidate_user,
            firstname='Bob',
            lastname='Johnson',
            city='Boston',
        )

        # Create a test job
        self.job = JobDetails.objects.create(
            company_id=self.company,
            jobname='Senior Python Developer',
            companyname='TechCorp',
            companyaddress='123 Wall St',
            jobdescription='Build scalable APIs using Django and DRF.',
            qualification='B.Tech/BS in CS',
            responsibilties='Develop microservices',
            location='New York',
            companywebsite='https://techcorp.com',
            companyemail='jobs@techcorp.com',
            companycontact='1234567890',
            salarypackage='$120,000 - $140,000',
            experience=4,
            job_type='Full Time',
            jobcategory='IT',
        )

    # ── Auth & Security Tests ─────────────────────────────────────────────────

    def test_registration_hashes_password(self):
        payload = {
            'fname': 'David',
            'lname': 'Miller',
            'email': 'david@example.com',
            'password': 'StrongPassword123!',
            'cpassword': 'StrongPassword123!',
            'role': 'Candidate',
        }
        res = self.client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['success'])

        user = UserMaster.objects.get(email='david@example.com')
        # Ensure password is not stored in plaintext
        self.assertNotEqual(user.password, 'StrongPassword123!')
        self.assertTrue(check_password('StrongPassword123!', user.password))
        self.assertNotIn('otp_dev_only', res.data)
        self.assertEqual(mail.outbox[-1].to, ['david@example.com'])
        self.assertIn(str(user.otp), mail.outbox[-1].body)

    @patch('jobportalapp.views.send_mail', side_effect=SMTPException('SMTP unavailable'))
    def test_registration_rolls_back_if_verification_email_fails(self, send_mail_mock):
        response = self.client.post('/api/auth/register/', {
            'fname': 'Sam',
            'lname': 'Taylor',
            'email': 'sam@example.com',
            'password': 'StrongPassword123!',
            'cpassword': 'StrongPassword123!',
            'role': 'Candidate',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(UserMaster.objects.filter(email='sam@example.com').exists())
        send_mail_mock.assert_called_once()

    def test_unverified_user_cannot_log_in(self):
        from django.contrib.auth.hashers import make_password
        user = UserMaster.objects.create(
            email='unverified@example.com',
            role='Candidate',
            otp=123456,
            password=make_password('CandidatePass123!'),
        )
        Candidate.objects.create(user_id=user, firstname='A', lastname='B')

        response = self.client.post('/api/auth/login/', {
            'email': user.email,
            'password': 'CandidatePass123!',
            'role': 'Candidate',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn('tokens', response.data)

    def test_company_profile_is_available_through_self_route(self):
        from .authentication import get_tokens_for_user
        tokens = get_tokens_for_user(self.company_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.client.get('/api/company/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['profile']['email'], self.company_user.email)

        id_route = self.client.get(f'/api/company/{self.company_user.id}/profile/')
        self.assertEqual(id_route.status_code, status.HTTP_404_NOT_FOUND)

    def test_company_profile_update_uses_self_route(self):
        from .authentication import get_tokens_for_user
        tokens = get_tokens_for_user(self.company_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.client.patch(
            '/api/company/profile/update/',
            {'city': 'Seattle', 'email': 'changed@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.company.refresh_from_db()
        self.assertEqual(self.company.city, 'Seattle')
        self.company_user.refresh_from_db()
        self.assertEqual(self.company_user.email, 'techcorp@example.com')
        id_route = self.client.patch(
            f'/api/company/{self.company_user.id}/profile/update/',
            {'city': 'Portland'},
            format='json',
        )
        self.assertEqual(id_route.status_code, status.HTTP_404_NOT_FOUND)

    def test_otp_verification_issues_tokens(self):
        user = UserMaster.objects.create(
            email='verify_me@example.com',
            role='Candidate',
            otp=998877,
            password='hash',
        )
        Candidate.objects.create(user_id=user, firstname='V', lastname='U')

        res = self.client.post('/api/auth/otp-verify/', {'email': 'verify_me@example.com', 'otp': 998877}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', res.data)
        self.assertIn('access', res.data['tokens'])

        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_login_returns_jwt_tokens(self):
        from django.contrib.auth.hashers import make_password
        self.candidate_user.password = make_password('CandidatePass123!')
        self.candidate_user.save()

        res = self.client.post('/api/auth/login/', {
            'email': 'dev@example.com',
            'password': 'CandidatePass123!',
            'role': 'Candidate',
        }, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', res.data)
        self.assertIn('access', res.data['tokens'])
        self.assertEqual(res.data['role'], 'Candidate')

    # ── Job Search & Filtering Tests ──────────────────────────────────────────

    def test_jobs_list_with_search_and_filter(self):
        # Match by search
        res = self.client.get('/api/jobs/?search=Python')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)

        # Match by category
        res = self.client.get('/api/jobs/?category=IT')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)

        # Filter with non-matching category
        res = self.client.get('/api/jobs/?category=Healthcare')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)

    def test_job_categories_endpoint(self):
        res = self.client.get('/api/jobs/categories/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['success'])
        self.assertTrue(len(res.data['categories']) >= 1)

    # ── Permissions & Role-based Access Tests ─────────────────────────────────

    def test_candidate_cannot_post_job(self):
        from .authentication import get_tokens_for_user
        tokens = get_tokens_for_user(self.candidate_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        res = self.client.post('/api/company/jobs/post/', {'jobname': 'Hacker Job'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_can_post_job(self):
        from .authentication import get_tokens_for_user
        tokens = get_tokens_for_user(self.company_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        job_data = {
            'jobname': 'DevOps Engineer',
            'companyname': 'TechCorp',
            'companyaddress': '123 Wall St',
            'jobdescription': 'Manage AWS and Docker environments.',
            'qualification': 'BS Computer Science',
            'responsibilties': 'CI/CD pipeline maintenance',
            'location': 'Remote',
            'companywebsite': 'https://techcorp.com',
            'companyemail': 'jobs@techcorp.com',
            'companycontact': '1234567890',
            'salarypackage': '$130,000',
            'experience': 3,
            'job_type': 'Remote',
            'jobcategory': 'DevOps',
        }
        res = self.client.post('/api/company/jobs/post/', job_data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JobDetails.objects.filter(jobname='DevOps Engineer').count(), 1)

    def test_company_cannot_post_job_until_profile_is_approved(self):
        from .authentication import get_tokens_for_user
        self.company.is_approved = False
        self.company.save(update_fields=['is_approved'])
        tokens = get_tokens_for_user(self.company_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.client.post('/api/company/jobs/post/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('approved', response.data['message'])

    def test_company_profile_update_resets_admin_approval(self):
        from .authentication import get_tokens_for_user
        tokens = get_tokens_for_user(self.company_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.client.patch(
            '/api/company/profile/update/',
            {'company_name': 'Updated TechCorp', 'is_approved': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['profile']['is_approved'])
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_approved)

    def test_company_can_edit_and_close_own_job(self):
        from .authentication import get_tokens_for_user
        tokens = get_tokens_for_user(self.company_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        detail_url = f'/api/company/jobs/{self.job.pk}/'
        response = self.client.patch(
            detail_url,
            {'jobname': 'Updated job title', 'is_open': False},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.job.refresh_from_db()
        self.assertEqual(self.job.jobname, 'Updated job title')
        self.assertTrue(self.job.is_open)
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)

        close_response = self.client.post(f'/api/company/jobs/{self.job.pk}/close/')
        self.assertEqual(close_response.status_code, status.HTTP_200_OK)
        self.job.refresh_from_db()
        self.assertFalse(self.job.is_open)

    def test_company_cannot_edit_another_companys_job(self):
        from .authentication import get_tokens_for_user
        other_user = UserMaster.objects.create(
            email='other-company@example.com',
            role='Company',
            otp=123456,
            password='hashed_dummy_password',
            is_verified=True,
        )
        Company.objects.create(
            user_id=other_user,
            firstname='Other',
            lastname='Company',
            company_name='Other Co',
            is_approved=True,
        )
        tokens = get_tokens_for_user(other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.client.patch(
            f'/api/company/jobs/{self.job.pk}/',
            {'jobname': 'Unauthorized edit'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.job.refresh_from_db()
        self.assertEqual(self.job.jobname, 'Senior Python Developer')

    def test_closed_jobs_are_hidden_and_cannot_be_applied_to(self):
        from .authentication import get_tokens_for_user
        self.job.is_open = False
        self.job.save(update_fields=['is_open'])

        response = self.client.get('/api/jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(
            self.client.get(f'/api/jobs/{self.job.pk}/').status_code,
            status.HTTP_404_NOT_FOUND,
        )

        tokens = get_tokens_for_user(self.candidate_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        apply_response = self.client.post(
            f'/api/jobs/{self.job.pk}/apply/',
            {},
            format='multipart',
        )
        self.assertEqual(apply_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_company_can_update_application_status_without_email_notification(self):
        from .authentication import get_tokens_for_user
        application = ApplyList.objects.create(
            candidate=self.candidate,
            job=self.job,
            education='BSc',
            website='https://candidate.example.com',
            gender='Other',
            resume='resume.pdf',
        )
        tokens = get_tokens_for_user(self.company_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.client.patch(
            f'/api/company/applications/{application.pk}/status/',
            {'status': 'Shortlisted'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'Shortlisted')
        self.assertEqual(len(mail.outbox), 0)
        application.refresh_from_db()
        self.assertEqual(application.status, 'Shortlisted')

        invalid_response = self.client.patch(
            f'/api/company/applications/{application.pk}/status/',
            {'status': 'NotAStatus'},
            format='json',
        )
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(self.candidate_user)['access']}"
        )
        applied_jobs = self.client.get('/api/candidate/applied-jobs/')
        self.assertEqual(applied_jobs.status_code, status.HTTP_200_OK)
        self.assertEqual(applied_jobs.data['results'][0]['status'], 'Shortlisted')

    # ── Job Application Flow ──────────────────────────────────────────────────

    def test_public_job_endpoints_allow_browsing_without_login(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid')
        public_paths = [
            '/api/jobs/',
            '/api/jobs/categories/',
            f'/api/jobs/{self.job.id}/',
            '/api/candidate/jobs/',
        ]
        for path in public_paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, status.HTTP_200_OK)

        self.client.credentials()
        response = self.client.post(f'/api/jobs/{self.job.id}/apply/', {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_candidate_apply_job_with_file_validation(self):
        from .authentication import get_tokens_for_user
        tokens = get_tokens_for_user(self.candidate_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Upload a dummy PDF resume
        fake_resume = SimpleUploadedFile(
            name='my_resume.pdf',
            content=b'%PDF-1.4 Fake PDF Content',
            content_type='application/pdf'
        )

        apply_data = {
            'education': 'Master of CS',
            'website': 'https://bob.dev',
            'gender': 'Male',
            'experience': 4,
            'expectations': 130000,
            'shift': 'Day',
            'resume': fake_resume,
        }
        res = self.client.post(f'/api/jobs/{self.job.id}/apply/', apply_data, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ApplyList.objects.filter(job=self.job, candidate=self.candidate).count(), 1)

        # Applying again should be rejected (prevent duplicate applications)
        fake_resume.seek(0)
        res_dup = self.client.post(f'/api/jobs/{self.job.id}/apply/', apply_data, format='multipart')
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)
