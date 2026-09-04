from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    # extend with tenant-specific or profile fields later
    pass
