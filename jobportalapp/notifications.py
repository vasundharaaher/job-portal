from django.conf import settings
from django.core.mail import send_mail


def send_company_approval_email(company):
    return send_mail(
        subject='Your company profile has been approved',
        message=(
            f'Hello {company.firstname},\n\n'
            f'Your company profile for {company.company_name} has been approved '
            'by the Job Portal admin. You can now post jobs from your account.\n\n'
            'Thank you,\n'
            'Job Portal Admin'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[company.user_id.email],
        fail_silently=False,
    )
