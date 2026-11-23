from django.db import models


class UserMaster(models.Model):
    email       = models.EmailField(max_length=50)
    password    = models.CharField(max_length=128)
    otp         = models.IntegerField()
    role        = models.CharField(max_length=50)
    is_active   = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_created  = models.DateTimeField(auto_now_add=True)
    is_updated  = models.DateTimeField(auto_now=True)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return f"{self.email} ({self.role})"


class Candidate(models.Model):
    user_id      = models.OneToOneField(UserMaster, on_delete=models.CASCADE)
    firstname    = models.CharField(max_length=50)
    lastname     = models.CharField(max_length=50)
    contact      = models.CharField(max_length=50)
    state        = models.CharField(max_length=50)
    city         = models.CharField(max_length=50)
    address      = models.CharField(max_length=80)
    dob          = models.CharField(max_length=50)
    gender       = models.CharField(max_length=50)
    min_salary   = models.BigIntegerField(default=0)
    max_salary   = models.BigIntegerField(default=0)
    job_type     = models.CharField(max_length=150, default="")
    jobcategory  = models.CharField(max_length=150, default="")
    country      = models.CharField(max_length=150, default="")
    highesedu    = models.CharField(max_length=150, default="")
    experience   = models.CharField(max_length=150, default="")
    website      = models.CharField(max_length=150, default="")
    shift        = models.CharField(max_length=150, default="")
    jobdescription = models.CharField(max_length=150, default="")
    profile_pic  = models.ImageField(upload_to="app/img/candidate", blank=True, null=True)


class Company(models.Model):
    user_id          = models.OneToOneField(UserMaster, on_delete=models.CASCADE)
    firstname        = models.CharField(max_length=50)
    lastname         = models.CharField(max_length=50)
    company_name     = models.CharField(max_length=50)
    state            = models.CharField(max_length=50, default="")
    city             = models.CharField(max_length=50, default="")
    contact          = models.CharField(max_length=50, default="")
    address          = models.CharField(max_length=150, default="")
    website          = models.CharField(max_length=150, default="")
    country          = models.CharField(max_length=150, default="")
    companydscription = models.CharField(max_length=150, default="")
    companycategory  = models.CharField(max_length=150, default="")
    companygstno     = models.CharField(max_length=30, default="")
    logo_pic         = models.ImageField(upload_to="app/img/company", blank=True, null=True)


class JobDetails(models.Model):
    company_id      = models.ForeignKey(Company, on_delete=models.CASCADE)
    jobname         = models.CharField(max_length=250)
    companyname     = models.CharField(max_length=250)
    companyaddress  = models.CharField(max_length=250)
    jobdescription  = models.TextField(max_length=550)
    qualification   = models.CharField(max_length=250)
    responsibilties = models.CharField(max_length=250)
    location        = models.CharField(max_length=250)
    companywebsite  = models.CharField(max_length=250)
    companyemail    = models.CharField(max_length=250)
    companycontact  = models.CharField(max_length=250)
    salarypackage   = models.CharField(max_length=250)
    experience      = models.IntegerField()
    job_type        = models.CharField(max_length=150)
    jobcategory     = models.CharField(max_length=150, default="")
    logo            = models.ImageField(upload_to="app/img/job", blank=True, null=True)


class ApplyList(models.Model):
    candidate    = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    job          = models.ForeignKey(JobDetails, on_delete=models.CASCADE)
    education    = models.CharField(max_length=200)
    website      = models.CharField(max_length=200)
    gender       = models.CharField(max_length=200)
    resume       = models.FileField(upload_to="app/resume")
    experience   = models.IntegerField(default=0)
    expectations = models.IntegerField(default=0)
    shift        = models.CharField(max_length=20, default='Day')


class ContactMessage(models.Model):
    name       = models.CharField(max_length=100)
    email      = models.EmailField(max_length=100)
    subject    = models.CharField(max_length=200)
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"


class Bookmark(models.Model):
    company   = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bookmarks')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'candidate')

    def __str__(self):
        return f"{self.company.company_name} -> {self.candidate.firstname} {self.candidate.lastname}"
