from django.contrib import admin
from .models import (
    UserMaster, Candidate, Company,
    JobDetails, ApplyList, ContactMessage, Bookmark,
)


@admin.register(UserMaster)
class UserMasterAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'role', 'is_verified', 'is_active', 'is_created')
    list_filter = ('role', 'is_verified', 'is_active', 'is_created')
    search_fields = ('email',)
    readonly_fields = ('is_created', 'is_updated')
    ordering = ('-id',)


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
    list_display = ('id', 'company_name', 'firstname', 'lastname', 'get_email', 'contact', 'city')
    list_filter = ('companycategory', 'city', 'state')
    search_fields = ('company_name', 'user_id__email', 'contact', 'companygstno')
    ordering = ('-id',)

    @admin.display(description='Email')
    def get_email(self, obj):
        return obj.user_id.email


@admin.register(JobDetails)
class JobDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'jobname', 'companyname', 'jobcategory', 'job_type', 'location', 'experience')
    list_filter = ('jobcategory', 'job_type', 'experience', 'location')
    search_fields = ('jobname', 'companyname', 'location', 'qualification')
    ordering = ('-id',)


@admin.register(ApplyList)
class ApplyListAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_candidate_name', 'get_job_name', 'experience', 'expectations', 'shift')
    list_filter = ('shift', 'gender', 'experience')
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
    list_display = ('id', 'name', 'email', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'candidate', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('company__company_name', 'candidate__firstname', 'candidate__lastname')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
