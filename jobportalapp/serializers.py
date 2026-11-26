from rest_framework import serializers
from .models import (
    UserMaster, Candidate, Company,
    JobDetails, ApplyList, ContactMessage, Bookmark,
)
from .validators import validate_resume_file, validate_image_file


class UserMasterSerializer(serializers.ModelSerializer):
    company_profile_approved = serializers.SerializerMethodField()

    class Meta:
        model = UserMaster
        fields = [
            'id', 'email', 'role', 'is_active', 'is_verified',
            'company_profile_approved', 'is_created', 'is_updated',
        ]
        read_only_fields = ['id', 'is_created', 'is_updated']

    def get_company_profile_approved(self, obj):
        if obj.role != 'Company':
            return None
        try:
            return obj.company.is_approved
        except Company.DoesNotExist:
            return False


class RegisterSerializer(serializers.Serializer):
    fname     = serializers.CharField(max_length=50)
    lname     = serializers.CharField(max_length=50)
    email     = serializers.EmailField()
    password  = serializers.CharField(max_length=128, write_only=True)
    cpassword = serializers.CharField(max_length=128, write_only=True)
    role      = serializers.ChoiceField(choices=['Candidate', 'Company'])

    def validate(self, data):
        if data['password'] != data['cpassword']:
            raise serializers.ValidationError("Passwords do not match.")
        if UserMaster.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("User already exists.")
        return data


class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role     = serializers.ChoiceField(choices=['Candidate', 'Company'])


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp   = serializers.IntegerField()


class CandidateSerializer(serializers.ModelSerializer):
    profile_pic = serializers.ImageField(required=False, allow_null=True, validators=[validate_image_file])

    class Meta:
        model = Candidate
        fields = '__all__'
        read_only_fields = ['user_id']


class CompanySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user_id.email', read_only=True)
    logo_pic = serializers.ImageField(required=False, allow_null=True, validators=[validate_image_file])

    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ['user_id', 'is_approved']


class JobDetailsSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField(required=False, allow_null=True, validators=[validate_image_file])

    class Meta:
        model = JobDetails
        fields = '__all__'
        read_only_fields = ['company_id', 'is_open']


class ApplyListSerializer(serializers.ModelSerializer):
    job_name     = serializers.CharField(source='job.jobname', read_only=True)
    company_name = serializers.CharField(source='job.companyname', read_only=True)

    class Meta:
        model = ApplyList
        fields = '__all__'
        read_only_fields = ['candidate', 'job', 'status']


class ApplicationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplyList
        fields = ['status']


class ApplyJobSerializer(serializers.ModelSerializer):
    resume = serializers.FileField(validators=[validate_resume_file])

    class Meta:
        model = ApplyList
        fields = ['education', 'website', 'gender', 'resume', 'experience', 'expectations', 'shift']


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class BookmarkSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    company_name   = serializers.CharField(source='company.company_name', read_only=True)

    class Meta:
        model = Bookmark
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'company', 'candidate']

    def get_candidate_name(self, obj):
        return f"{obj.candidate.firstname} {obj.candidate.lastname}"
