import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.utils import timezone

from .models import (
    UserMaster, Candidate, Company,
    JobDetails, ApplyList, ContactMessage, Bookmark,
)
from .notifications import send_company_approval_email

logger = logging.getLogger(__name__)


@admin.register(UserMaster)
class UserMasterAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'role', 'get_email_verified', 'is_active', 'is_created')
    list_filter = ('role', 'is_verified', 'is_active', 'is_created')
    search_fields = ('email',)
    readonly_fields = ('is_created', 'is_updated')
    ordering = ('-id',)

    @admin.display(boolean=True, description='Email verified', ordering='is_verified')
    def get_email_verified(self, obj):
        return obj.is_verified


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('id', 'firstname', 'lastname', 'get_email', 'contact', 'city', 'state')
    list_filter = ('job_type', 'city', 'state', 'experience')
    search_fields = ('firstname', 'lastname', 'user_id__email', 'contact', 'city')
    ordering = ('-id',)

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.user_id.email


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'company_name', 'firstname', 'lastname', 'get_email',
        'get_is_approved', 'contact', 'city',
    )
    list_filter = ('companycategory', 'city', 'state', 'is_approved')
    search_fields = ('company_name', 'user_id__email', 'contact', 'companygstno')
    ordering = ('-id',)
    actions = ('approve_selected_companies',)
    readonly_fields = ('is_approved',)

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.user_id.email

    @admin.display(boolean=True, description='Profile approved', ordering='is_approved')
    def get_is_approved(self, obj):
        return obj.is_approved

    @admin.action(description='Approve selected company profiles')
    def approve_selected_companies(self, request, queryset):
        if not request.user.has_perm('jobportalapp.change_company'):
            raise PermissionDenied

        pending_companies = list(
            queryset.filter(is_approved=False).select_related('user_id')
        )
        for company in pending_companies:
            company.is_approved = True
            company.save(update_fields=('is_approved',))

        sent_count = 0
        email_failures = []
        for company in pending_companies:
            try:
                if send_company_approval_email(company) == 1:
                    sent_count += 1
                else:
                    email_failures.append(company.user_id.email)
            except (SMTPException, OSError) as exc:
                logger.exception(
                    'Could not send company approval email to %s',
                    company.user_id.email,
                )
                email_failures.append(f'{company.user_id.email}: {exc}')

        if pending_companies and not email_failures:
            self.message_user(
                request,
                f'Approved {len(pending_companies)} company profile(s) and sent '
                f'{sent_count} approval email(s).',
                level=messages.SUCCESS,
            )
        elif pending_companies:
            self.message_user(
                request,
                f'Approved {len(pending_companies)} company profile(s), but '
                f'{len(email_failures)} approval email(s) could not be sent: '
                f'{"; ".join(email_failures)}',
                level=messages.WARNING,
            )
        else:
            self.message_user(
                request,
                'No pending company profiles were approved.',
                level=messages.INFO,
            )


@admin.register(JobDetails)
class JobDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'jobname', 'companyname', 'jobcategory', 'job_type', 'location', 'experience', 'is_open')
    list_filter = ('is_open', 'jobcategory', 'job_type', 'experience', 'location')
    search_fields = ('jobname', 'companyname', 'location', 'qualification')
    ordering = ('-id',)


@admin.register(ApplyList)
class ApplyListAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_candidate_name', 'get_job_name', 'status', 'experience', 'expectations', 'shift')
    list_filter = ('status', 'shift', 'gender', 'experience')
    search_fields = ('candidate__firstname', 'candidate__lastname', 'job__jobname', 'job__companyname')
    ordering = ('-id',)

    @admin.display(description='Candidate')
    def get_candidate_name(self, obj):
        return f"{obj.candidate.firstname} {obj.candidate.lastname}"

    @admin.display(description='Job')
    def get_job_name(self, obj):
        return obj.job.jobname


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    change_form_template = 'admin/jobportalapp/contactmessage/change_form.html'
    list_display = ('id', 'name', 'email', 'subject', 'created_at', 'reply_sent_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'reply_sent_at')
    ordering = ('-created_at',)
    fields = ('name', 'email', 'subject', 'message', 'created_at', 'admin_reply', 'reply_sent_at')

    def save_model(self, request, obj, form, change):
        if change and 'admin_reply' in form.changed_data:
            obj.reply_sent_at = None
        super().save_model(request, obj, form, change)

    def response_change(self, request, obj):
        if '_send_reply' not in request.POST:
            return super().response_change(request, obj)

        reply_body = obj.admin_reply.strip()
        if not reply_body:
            self.message_user(
                request,
                'Enter a reply before sending it.',
                level=messages.ERROR,
            )
            return HttpResponseRedirect(request.path)

        reply_subject = obj.subject
        if not reply_subject.lower().startswith('re:'):
            reply_subject = f'Re: {reply_subject}'

        try:
            sent_count = send_mail(
                subject=reply_subject,
                message=reply_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[obj.email],
                fail_silently=False,
            )
        except (SMTPException, OSError) as exc:
            self.message_user(
                request,
                f'Could not send reply email: {exc}',
                level=messages.ERROR,
            )
            return HttpResponseRedirect(request.path)

        if sent_count != 1:
            self.message_user(
                request,
                'The email backend did not confirm that the reply was sent.',
                level=messages.ERROR,
            )
            return HttpResponseRedirect(request.path)

        obj.admin_reply = reply_body
        obj.reply_sent_at = timezone.now()
        obj.save(update_fields=('admin_reply', 'reply_sent_at'))
        self.message_user(request, 'Reply email sent successfully.', level=messages.SUCCESS)
        return HttpResponseRedirect(request.path)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'candidate', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('company__company_name', 'candidate__firstname', 'candidate__lastname')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
