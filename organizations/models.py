
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Branch(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="branches",
    )

    name = models.CharField(max_length=180)

    code = models.CharField(
        max_length=30,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9_-]{2,30}$",
                message="Use 2-30 uppercase letters, digits, _ or -.",
            )
        ],
    )

    city = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_branch_code_per_organization",
            )
        ]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class Membership(models.Model):

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Organization Admin"
        STAFF = "STAFF", "Staff"
        TRAINER = "TRAINER", "Trainer"
        STUDENT = "STUDENT", "Student"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "role"],
                name="unique_organization_user_role",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.organization} - {self.role}"


class BranchAssignment(models.Model):

    class Role(models.TextChoices):
        MANAGER = "MANAGER", "Branch Manager"
        TRAINER = "TRAINER", "Trainer"
        STUDENT = "STUDENT", "Student"

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="branch_assignments",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "user", "role"],
                name="unique_branch_user_role",
            )
        ]

    def clean(self):
        if not self.branch_id or not self.user_id:
            return

        allowed_roles = {
            self.Role.MANAGER: [
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
                Membership.Role.STAFF,
            ],
            self.Role.TRAINER: [
                Membership.Role.TRAINER,
            ],
            self.Role.STUDENT: [
                Membership.Role.STUDENT,
            ],
        }

        if self.role not in allowed_roles:
            return

        valid = Membership.objects.filter(
            organization_id=self.branch.organization_id,
            organization__is_active=True,
            user_id=self.user_id,
            user__is_active=True,
            role__in=allowed_roles[self.role],
            is_active=True,
        ).exists()

        if not valid:
            raise ValidationError({
                "user": "User requires an active, matching "
                        "organization membership."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.branch} - {self.role}"



class AuditEvent(models.Model):
    """
    Tracks sensitive organization management actions.

    Application code creates audit records in the
    same transaction as the corresponding change.
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="organization_audit_events",
    )

    action = models.CharField(max_length=80)
    resource_type = models.CharField(max_length=60)
    resource_id = models.CharField(max_length=80)

    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="org_audit_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.action} - {self.resource_type}"
