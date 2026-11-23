from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [

    # ── Auth ──────────────────────────────────────────────────────────────────
    path('api/auth/register/',         views.RegisterUser,            name='api-register'),
    path('api/auth/otp-verify/',       views.OtpVerify,               name='api-otp-verify'),
    path('api/auth/login/',            views.LoginUser,               name='api-login'),
    path('api/auth/token/refresh/',    TokenRefreshView.as_view(),    name='api-token-refresh'),

    # ── Jobs (public) ─────────────────────────────────────────────────────────
    path('api/jobs/',                  views.AllJobs,                 name='api-all-jobs'),
    path('api/jobs/categories/',       views.JobCategories,          name='api-job-categories'),
    path('api/jobs/<int:pk>/',         views.JobDetail,               name='api-job-detail'),

    # ── Candidate (Self & by ID) ──────────────────────────────────────────────
    path('api/candidate/profile/',                  views.CandidateProfile,       name='api-candidate-profile-self'),
    path('api/candidate/<int:pk>/profile/',         views.CandidateProfile,       name='api-candidate-profile'),
    path('api/candidate/profile/update/',          views.UpdateCandidateProfile, name='api-candidate-profile-update-self'),
    path('api/candidate/<int:pk>/profile/update/',  views.UpdateCandidateProfile, name='api-candidate-profile-update'),
    path('api/candidate/jobs/',                     views.CandidateJobList,       name='api-candidate-job-list'),
    path('api/candidate/applied-jobs/',            views.AppliedJobs,            name='api-applied-jobs-self'),
    path('api/candidate/<int:candidate_id>/applied-jobs/', views.AppliedJobs,    name='api-applied-jobs'),
    path('api/jobs/<int:pk>/apply/',                views.ApplyJob,               name='api-apply-job'),

    # ── Company (Self & by ID) ────────────────────────────────────────────────
    path('api/company/profile/',                    views.CompanyProfile,         name='api-company-profile-self'),
    path('api/company/profile/update/',            views.UpdateCompanyProfile,   name='api-company-profile-update-self'),
    path('api/company/jobs/post/',                  views.PostJob,                name='api-post-job'),
    path('api/company/jobs/',                       views.CompanyJobList,         name='api-company-job-list-self'),
    path('api/company/<int:pk>/jobs/',              views.CompanyJobList,         name='api-company-job-list'),
    path('api/company/applicants/',                 views.CompanyApplicantList,   name='api-company-applicants-self'),
    path('api/company/<int:pk>/applicants/',        views.CompanyApplicantList,   name='api-company-applicants'),

    # ── Bookmark (Company) ────────────────────────────────────────────────────
    path('api/bookmarks/add/',                      views.AddBookmark,            name='api-add-bookmark'),
    path('api/bookmarks/<int:bookmark_id>/remove/', views.RemoveBookmark,         name='api-remove-bookmark'),
    path('api/company/bookmarks/',                  views.CompanyBookmarks,       name='api-company-bookmarks-self'),
    path('api/company/<int:pk>/bookmarks/',         views.CompanyBookmarks,       name='api-company-bookmarks'),

    # ── Resume ────────────────────────────────────────────────────────────────
    path('api/applications/<int:application_id>/resume/', views.DownloadResume,   name='api-download-resume'),

    # ── Contact ───────────────────────────────────────────────────────────────
    path('api/contact/',                            views.ContactUs,              name='api-contact'),

    # ── Admin ─────────────────────────────────────────────────────────────────
    path('api/admin/login/',                        views.AdminLogin,             name='api-admin-login'),
    path('api/admin/candidates/',                   views.AdminCandidateList,     name='api-admin-candidates'),
    path('api/admin/companies/',                    views.AdminCompanyList,       name='api-admin-companies'),
    path('api/admin/users/<int:pk>/delete/',        views.DeleteUser,             name='api-delete-user'),
    path('api/admin/companies/<int:pk>/verify/',    views.VerifyCompany,          name='api-verify-company'),
    path('api/admin/contact-messages/',             views.AdminContactMessages,   name='api-admin-contact-messages'),
]
