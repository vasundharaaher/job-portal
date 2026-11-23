import os
from rest_framework.exceptions import ValidationError


ALLOWED_RESUME_EXTENSIONS = {'.pdf', '.doc', '.docx'}
MAX_RESUME_SIZE_MB = 5

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_IMAGE_SIZE_MB = 3


def validate_resume_file(file):
    """
    Validate uploaded resume file extension and size.
    """
    if not file:
        return file

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_RESUME_EXTENSIONS:
        raise ValidationError(
            f"Unsupported resume format '{ext}'. Allowed formats: {', '.join(ALLOWED_RESUME_EXTENSIONS)}."
        )

    if file.size > MAX_RESUME_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f"Resume file size exceeds the maximum limit of {MAX_RESUME_SIZE_MB}MB."
        )

    return file


def validate_image_file(file):
    """
    Validate uploaded profile picture or logo image extension and size.
    """
    if not file:
        return file

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported image format '{ext}'. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}."
        )

    if file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f"Image file size exceeds the maximum limit of {MAX_IMAGE_SIZE_MB}MB."
        )

    return file

