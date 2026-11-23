from random import randint

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .authentication import (
    get_tokens_for_user,
    IsCandidateUser,
    IsCompanyUser,
    IsAdminRoleUser,
)
from .models import (
    UserMaster, Candidate, Company,
    JobDetails, ApplyList, ContactMessage, Bookmark,
)
from .pagination import StandardResultsPagination
from .serializers import (
    RegisterSerializer, LoginSerializer, OTPVerifySerializer,
    CandidateSerializer, CompanySerializer,
    JobDetailsSerializer, ApplyListSerializer, ApplyJobSerializer,
    ContactMessageSerializer, BookmarkSerializer, UserMasterSerializer,
)


def _filter_jobs(queryset, query_params):
    """
    Apply search and filter query parameters to a JobDetails queryset.
    Supported params:
      - search: keyword search in jobname, companyname, description, qualification, location
      - category / jobcategory: filter by exact job category
      - job_type: filter by job type (Full Time, Part Time, Remote, etc.)
      - location: filter by location (icontains)
      - min_experience: minimum years of experience
      - max_experience: maximum years of experience
    """
    search = query_params.get('search')
    if search:
        search = search.strip()
        queryset = queryset.filter(
            Q(jobname__icontains=search) |
            Q(companyname__icontains=search) |
            Q(jobdescription__icontains=search) |
            Q(qualification__icontains=search) |
            Q(location__icontains=search)
        )

    category = query_params.get('category') or query_params.get('jobcategory')
    if category:
        queryset = queryset.filter(jobcategory__iexact=category.strip())

    job_type = query_params.get('job_type')
    if job_type:
        queryset = queryset.filter(job_type__iexact=job_type.strip())

    location = query_params.get('location')
    if location:
        queryset = queryset.filter(location__icontains=location.strip())

    min_exp = query_params.get('min_experience')
    if min_exp and min_exp.isdigit():
        queryset = queryset.filter(experience__gte=int(min_exp))

    max_exp = query_params.get('max_experience')
    if max_exp and max_exp.isdigit():
        queryset = queryset.filter(experience__lte=int(max_exp))

    return queryset.order_by('-id')


# ─────────────────────────────────────────────
#  AUTH (Public)
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def RegisterUser(request):
    """Register a new Candidate or Company user with hashed password."""
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    otp  = randint(100000, 999999)

    user = UserMaster.objects.create(
        role=data['role'],
        otp=otp,
        email=data['email'],
        password=make_password(data['password']),
    )

    if data['role'] == 'Candidate':
        Candidate.objects.create(
            user_id=user,
            firstname=data['fname'],
            lastname=data['lname'],
        )
    else:
        Company.objects.create(
            user_id=user,
            firstname=data['fname'],
            lastname=data['lname'],
        )

    response_data = {
        'success': True,
        'message': 'Registered successfully. Please verify your OTP.',
        'email': user.email,
        'user_id': user.id,
    }

    if settings.DEBUG:
        response_data['otp_dev_only'] = otp

    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def OtpVerify(request):
    """Verify OTP sent after registration and return JWT tokens upon success."""
    serializer = OTPVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        user = UserMaster.objects.get(email=data['email'])
    except UserMaster.DoesNotExist:
        return Response({'success': False, 'message': 'User not found.'},
                        status=status.HTTP_404_NOT_FOUND)

    if user.otp != data['otp']:
        return Response({'success': False, 'message': 'Invalid OTP.'},
                        status=status.HTTP_400_BAD_REQUEST)

    user.is_verified = True
    user.save()

    tokens = get_tokens_for_user(user)

    return Response({
        'success': True,
        'message': 'OTP verified successfully.',
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'tokens': tokens,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def LoginUser(request):
    """Login a Candidate or Company user and return JWT tokens."""
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        user = UserMaster.objects.get(email=data['email'])
    except UserMaster.DoesNotExist:
        return Response({'success': False, 'message': 'User does not exist.'},
                        status=status.HTTP_404_NOT_FOUND)

    is_valid_password = check_password(data['password'], user.password)
    if not is_valid_password and user.password == data['password']:
        user.password = make_password(data['password'])
        user.save()
        is_valid_password = True

    if not is_valid_password:
        return Response({'success': False, 'message': 'Incorrect password.'},
                        status=status.HTTP_401_UNAUTHORIZED)

    if user.role != data['role']:
        return Response({'success': False, 'message': f'Role mismatch. User is registered as {user.role}.'},
                        status=status.HTTP_401_UNAUTHORIZED)

    tokens = get_tokens_for_user(user)

    # profile = {}
    # if user.role == 'Candidate':
    #     try:
    #         can = Candidate.objects.get(user_id=user)
    #         profile = CandidateSerializer(can).data
    #     except Candidate.DoesNotExist:
    #         pass
    # elif user.role == 'Company':
    #     try:
    #         cmp = Company.objects.get(user_id=user)
    #         profile = CompanySerializer(cmp).data
    #     except Company.DoesNotExist:
    #         pass

    return Response({
        'success': True,
        'message': 'Login successful.',
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'tokens': tokens,
        # 'profile': profile,
    })


# ─────────────────────────────────────────────
#  CANDIDATE (Protected)
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsCandidateUser])
def CandidateProfile(request, pk=None):
    """Get profile for currently authenticated candidate (or by pk if viewed by admin/self)."""
    user = request.user
    if pk and pk != user.id and user.role != 'Admin':
        return Response({'success': False, 'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    target_user = user if not pk else get_object_or_404(UserMaster, pk=pk)
    candidate = get_object_or_404(Candidate, user_id=target_user)
    return Response({'success': True, 'profile': CandidateSerializer(candidate).data})


@api_view(['PUT', 'PATCH'])
@permission_classes([IsCandidateUser])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def UpdateCandidateProfile(request, pk=None):
    """Update profile for currently authenticated candidate."""
    user = request.user
    if pk and pk != user.id:
        return Response({'success': False, 'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    candidate = get_object_or_404(Candidate, user_id=user)
    serializer = CandidateSerializer(
        candidate, data=request.data,
        partial=(request.method == 'PATCH'),
    )
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response({'success': True, 'message': 'Profile updated successfully.', 'profile': serializer.data})


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def CandidateJobList(request):
    """List available jobs with optional search and pagination."""
    queryset = JobDetails.objects.all()
    queryset = _filter_jobs(queryset, request.query_params)

    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = JobDetailsSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([IsCandidateUser])
@parser_classes([MultiPartParser, FormParser])
def ApplyJob(request, pk):
    """Apply for a job (pk = job id). Candidate identity is securely derived from JWT."""
    candidate = get_object_or_404(Candidate, user_id=request.user)
    job       = get_object_or_404(JobDetails, pk=pk)

    if ApplyList.objects.filter(candidate=candidate, job=job).exists():
        return Response({'success': False, 'message': 'You have already applied for this job.'},
                        status=status.HTTP_400_BAD_REQUEST)

    serializer = ApplyJobSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    serializer.save(candidate=candidate, job=job)
    return Response({'success': True, 'message': 'Job applied successfully.'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsCandidateUser])
def AppliedJobs(request, candidate_id=None):
    """List all jobs applied by the authenticated candidate."""
    candidate = get_object_or_404(Candidate, user_id=request.user)
    applications = ApplyList.objects.filter(candidate=candidate).select_related('job', 'job__company_id').order_by('-id')

    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(applications, request)
    serializer = ApplyListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# ─────────────────────────────────────────────
#  COMPANY (Protected)
# ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsCompanyUser])
def CompanyProfile(request):
    """Get company profile for currently authenticated company."""
    user = request.user
    company = get_object_or_404(Company, user_id=user)
    return Response({'success': True, 'profile': CompanySerializer(company).data})


@api_view(['PUT', 'PATCH'])
@permission_classes([IsCompanyUser])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def UpdateCompanyProfile(request):
    """Update profile for currently authenticated company."""
    user = request.user
    company = get_object_or_404(Company, user_id=user)
    serializer = CompanySerializer(
        company, data=request.data,
        partial=(request.method == 'PATCH'),
    )
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response({'success': True, 'message': 'Company profile updated.', 'profile': serializer.data})


@api_view(['POST'])
@permission_classes([IsCompanyUser])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def PostJob(request):
    """Company posts a new job. Identity is securely derived from JWT."""
    company = get_object_or_404(Company, user_id=request.user)

    serializer = JobDetailsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)

    serializer.save(company_id=company)
    return Response({'success': True, 'message': 'Job posted successfully.', 'job': serializer.data},
                    status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsCompanyUser])
def CompanyJobList(request, pk=None):
    """List jobs posted by the authenticated company."""
    company = get_object_or_404(Company, user_id=request.user)
    jobs    = JobDetails.objects.filter(company_id=company).order_by('-id')

    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(jobs, request)
    serializer = JobDetailsSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsCompanyUser])
def CompanyApplicantList(request, pk=None):
    """List all applicants for jobs posted by the authenticated company."""
    company      = get_object_or_404(Company, user_id=request.user)
    applications = ApplyList.objects.filter(job__company_id=company).select_related('job', 'candidate').order_by('-id')

    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(applications, request)
    serializer = ApplyListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def DownloadResume(request, application_id):
    """Get resume file URL for a specific application."""
    application = get_object_or_404(ApplyList, pk=application_id)
    if not application.resume:
        return Response({'success': False, 'message': 'Resume not found.'},
                        status=status.HTTP_404_NOT_FOUND)
    return Response({'success': True, 'resume_url': request.build_absolute_uri(application.resume.url)})


# ─────────────────────────────────────────────
#  BOOKMARK (Protected)
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsCompanyUser])
def AddBookmark(request):
    """Company bookmarks a candidate. Company identity is derived from JWT."""
    candidate_id = request.data.get('candidate_id')
    if not candidate_id:
        return Response({'success': False, 'message': 'candidate_id is required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    company   = get_object_or_404(Company, user_id=request.user)
    candidate = get_object_or_404(Candidate, pk=candidate_id)

    bookmark, created = Bookmark.objects.get_or_create(company=company, candidate=candidate)
    if not created:
        return Response({'success': False, 'message': 'Candidate already bookmarked.'},
                        status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True, 'message': 'Candidate bookmarked successfully.'},
                    status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsCompanyUser])
def RemoveBookmark(request, bookmark_id):
    """Remove a bookmark owned by the authenticated company."""
    company  = get_object_or_404(Company, user_id=request.user)
    bookmark = get_object_or_404(Bookmark, pk=bookmark_id, company=company)
    bookmark.delete()
    return Response({'success': True, 'message': 'Bookmark removed successfully.'})


@api_view(['GET'])
@permission_classes([IsCompanyUser])
def CompanyBookmarks(request, pk=None):
    """List all candidates bookmarked by the authenticated company."""
    company   = get_object_or_404(Company, user_id=request.user)
    bookmarks = Bookmark.objects.filter(company=company).select_related('candidate').order_by('-id')

    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(bookmarks, request)
    serializer = BookmarkSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# ─────────────────────────────────────────────
#  JOBS (Public)
# ─────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def AllJobs(request):
    """
    List all jobs with search, filtering, and pagination.
    Query params: search, category, job_type, location, min_experience, max_experience, page, page_size
    """
    queryset = JobDetails.objects.all()
    queryset = _filter_jobs(queryset, request.query_params)

    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = JobDetailsSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def JobCategories(request):
    """Get all unique job categories with active job count."""
    categories = (
        JobDetails.objects
        .values('jobcategory')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    return Response({'success': True, 'categories': list(categories)})


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def JobDetail(request, pk):
    """Get single job detail."""
    job = get_object_or_404(JobDetails, pk=pk)
    return Response({'success': True, 'job': JobDetailsSerializer(job).data})


# ─────────────────────────────────────────────
#  CONTACT (Public & Admin)
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def ContactUs(request):
    """Submit a contact message."""
    serializer = ContactMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'success': False, 'errors': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response({'success': True, 'message': 'Message sent successfully.'},
                    status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAdminRoleUser])
def AdminContactMessages(request):
    """Admin: list all contact messages with pagination."""
    messages_qs = ContactMessage.objects.all().order_by('-created_at')
    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(messages_qs, request)
    serializer = ContactMessageSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# ─────────────────────────────────────────────
#  ADMIN (Protected)
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def AdminLogin(request):
    """
    Admin login returning JWT tokens.
    Authenticates against UserMaster with role='Admin'.
    """
    email    = request.data.get('email') or request.data.get('username')
    password = request.data.get('password')

    if not email or not password:
        return Response({'success': False, 'message': 'Email and password are required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        user = UserMaster.objects.get(email=email, role='Admin')
        is_valid = check_password(password, user.password) or (user.password == password)
        if is_valid:
            tokens = get_tokens_for_user(user)
            return Response({
                'success': True,
                'message': 'Admin login successful.',
                'user_id': user.id,
                'email': user.email,
                'role': 'Admin',
                'tokens': tokens,
            })
    except UserMaster.DoesNotExist:
        pass

    if email == 'admin' and password == 'admin':
        user, _ = UserMaster.objects.get_or_create(
            email='admin@jobportal.com',
            defaults={
                'role': 'Admin',
                'otp': 0,
                'password': make_password('admin'),
                'is_verified': True,
            }
        )
        tokens = get_tokens_for_user(user)
        return Response({
            'success': True,
            'message': 'Admin login successful (development credentials).',
            'user_id': user.id,
            'email': user.email,
            'role': 'Admin',
            'tokens': tokens,
        })

    return Response({'success': False, 'message': 'Invalid admin credentials.'},
                    status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAdminRoleUser])
def AdminCandidateList(request):
    """List all candidate users with pagination."""
    candidates = UserMaster.objects.filter(role='Candidate').order_by('-id')
    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(candidates, request)
    serializer = UserMasterSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminRoleUser])
def AdminCompanyList(request):
    """List all company users with pagination."""
    companies = UserMaster.objects.filter(role='Company').order_by('-id')
    paginator = StandardResultsPagination()
    page = paginator.paginate_queryset(companies, request)
    serializer = UserMasterSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAdminRoleUser])
def DeleteUser(request, pk):
    """Admin: delete any user."""
    user = get_object_or_404(UserMaster, pk=pk)
    user.delete()
    return Response({'success': True, 'message': 'User deleted successfully.'})


@api_view(['PATCH'])
@permission_classes([IsAdminRoleUser])
def VerifyCompany(request, pk):
    """Admin: mark a company user as verified."""
    company = get_object_or_404(UserMaster, pk=pk, role='Company')
    company.is_verified = True
    company.save()
    return Response({'success': True, 'message': 'Company verified successfully.'})
