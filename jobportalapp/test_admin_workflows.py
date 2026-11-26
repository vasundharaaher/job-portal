from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Company, ContactMessage, UserMaster
from .authentication import get_tokens_for_user


class AdminWorkflowTests(TestCase):
    def setUp(self):
        admin_user = get_user_model().objects.create_superuser(
            username='siteadmin',
            email='siteadmin@example.com',
            password='test-password',
        )
        self.client.force_login(admin_user)

    def test_company_admin_action_approves_selected_company(self):
        company_user = UserMaster.objects.create(
            email='company@example.com',
            role='Company',
            otp=0,
            password='hashed-password',
            is_verified=False,
        )
        company = Company.objects.create(
            user_id=company_user,
            firstname='A',
            lastname='Company',
            company_name='Example Co',
        )

        response = self.client.post(
            reverse('admin:jobportalapp_company_changelist'),
            {
                'action': 'approve_selected_companies',
                '_selected_action': [str(company.pk)],
                'index': '0',
            },
        )

        self.assertEqual(response.status_code, 302)
        company_user.refresh_from_db()
        company.refresh_from_db()
        self.assertTrue(company.is_approved)
        self.assertFalse(company_user.is_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['company@example.com'])
        self.assertIn('You can now post jobs', mail.outbox[0].body)

    def test_api_company_approval_does_not_change_otp_verification(self):
        company_user = UserMaster.objects.create(
            email='company@example.com',
            role='Company',
            otp=123456,
            password='hashed-password',
            is_verified=False,
        )
        company = Company.objects.create(
            user_id=company_user,
            firstname='A',
            lastname='Company',
            company_name='Example Co',
        )
        admin_user = UserMaster.objects.create(
            email='api-admin@example.com',
            role='Admin',
            otp=0,
            password='hashed-password',
        )
        tokens = get_tokens_for_user(admin_user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = client.patch(f'/api/admin/companies/{company_user.pk}/verify/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['email_sent'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['company@example.com'])
        company.refresh_from_db()
        company_user.refresh_from_db()
        self.assertTrue(company.is_approved)
        self.assertFalse(company_user.is_verified)

    @patch(
        'jobportalapp.notifications.send_mail',
        side_effect=SMTPException('SMTP unavailable'),
    )
    def test_company_approval_email_failure_is_reported(self, send_mail_mock):
        company_user = UserMaster.objects.create(
            email='company@example.com',
            role='Company',
            otp=0,
            password='hashed-password',
        )
        company = Company.objects.create(
            user_id=company_user,
            firstname='A',
            lastname='Company',
            company_name='Example Co',
        )

        response = self.client.post(
            reverse('admin:jobportalapp_company_changelist'),
            {
                'action': 'approve_selected_companies',
                '_selected_action': [str(company.pk)],
                'index': '0',
            },
        )

        self.assertEqual(response.status_code, 302)
        error_page = self.client.get(response.url)
        self.assertContains(error_page, 'approval email(s) could not be sent')
        company.refresh_from_db()
        self.assertTrue(company.is_approved)
        send_mail_mock.assert_called_once()

    def test_contact_message_reply_is_sent_and_recorded(self):
        contact = ContactMessage.objects.create(
            name='Jane Customer',
            email='jane@example.com',
            subject='Question about a job',
            message='Could you share more details?',
        )
        change_url = reverse('admin:jobportalapp_contactmessage_change', args=[contact.pk])
        page = self.client.get(change_url)
        self.assertContains(page, 'name="_send_reply"')
        self.assertContains(page, 'Save and send reply')

        response = self.client.post(
            change_url,
            {
                'name': contact.name,
                'email': contact.email,
                'subject': contact.subject,
                'message': contact.message,
                'admin_reply': 'Thanks for reaching out.',
                '_send_reply': 'Save and send reply',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['jane@example.com'])
        self.assertEqual(mail.outbox[0].subject, 'Re: Question about a job')
        self.assertEqual(mail.outbox[0].body, 'Thanks for reaching out.')
        contact.refresh_from_db()
        self.assertEqual(contact.admin_reply, 'Thanks for reaching out.')
        self.assertIsNotNone(contact.reply_sent_at)

    @patch('jobportalapp.admin.send_mail', side_effect=SMTPException('SMTP unavailable'))
    def test_failed_contact_reply_is_reported_and_not_marked_sent(self, send_mail_mock):
        contact = ContactMessage.objects.create(
            name='Jane Customer',
            email='jane@example.com',
            subject='Question about a job',
            message='Could you share more details?',
        )

        response = self.client.post(
            reverse('admin:jobportalapp_contactmessage_change', args=[contact.pk]),
            {
                'name': contact.name,
                'email': contact.email,
                'subject': contact.subject,
                'message': contact.message,
                'admin_reply': 'Thanks for reaching out.',
                '_send_reply': 'Save and send reply',
            },
        )

        self.assertEqual(response.status_code, 302)
        error_page = self.client.get(response.url)
        self.assertContains(error_page, 'Could not send reply email: SMTP unavailable')
        self.assertEqual(len(mail.outbox), 0)
        contact.refresh_from_db()
        self.assertEqual(contact.admin_reply, 'Thanks for reaching out.')
        self.assertIsNone(contact.reply_sent_at)
        send_mail_mock.assert_called_once()
