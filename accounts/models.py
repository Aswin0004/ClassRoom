
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    One login identity across the platform.

    Organization and branch permissions are stored
    separately rather than in a global user role.
    """

    def __str__(self):
        return self.get_full_name() or self.username
