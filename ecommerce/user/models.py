from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

USER_TYPE_CHOICES = (
    ("customer", "Customer"),
    ("admin", "Admin"),
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        extra_fields.setdefault("user_type", "customer")
        extra_fields.setdefault("is_active", True)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None

    email = models.EmailField(unique=True)

    full_name = models.CharField(max_length=255)

    phone_number = models.CharField(max_length=20, blank=True, null=True)

    address = models.CharField(max_length=512, blank=True, null=True)

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default="customer",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    def __str__(self):
        return f"{self.full_name} ({self.user_type})"