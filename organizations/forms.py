
from django import forms
from django.contrib.auth import get_user_model

from .models import (
    Branch,
    Membership,
)


User = get_user_model()


class BranchForm(forms.ModelForm):
    code = forms.RegexField(
        regex=r"^[A-Za-z0-9_-]{2,30}$",
        max_length=30,
        help_text="2-30 letters, digits, hyphens or underscores.",
    )

    class Meta:
        model = Branch
        fields = [
            "name",
            "code",
            "city",
            "is_active",
        ]

    def __init__(self, *args, organization, **kwargs):
        self.organization = organization
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields.pop("is_active")

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()

        existing = Branch.objects.filter(
            organization=self.organization,
            code=code,
        )

        if self.instance.pk:
            existing = existing.exclude(
                pk=self.instance.pk
            )

        if existing.exists():
            raise forms.ValidationError(
                "This branch code is already in use."
            )

        return code


class GrantAccessForm(forms.Form):

    GRANT_CHOICES = [
        ("MANAGER", "Branch Manager"),
        ("TRAINER", "Trainer"),
        ("STUDENT", "Student"),
        ("STAFF", "Organization Staff"),
        ("ADMIN", "Organization Admin"),
    ]

    username = forms.CharField(max_length=150)

    grant = forms.ChoiceField(
        choices=GRANT_CHOICES,
    )

    branch = forms.ModelChoiceField(
        queryset=Branch.objects.none(),
        required=False,
        empty_label="No branch selected",
    )

    def __init__(
        self,
        *args,
        organization,
        actor,
        **kwargs
    ):
        self.organization = organization
        self.actor = actor
        self.target_user = None

        super().__init__(*args, **kwargs)

        self.fields["branch"].queryset = (
            Branch.objects.filter(
                organization=organization,
                is_active=True,
            ).order_by("name")
        )

    def clean(self):
        data = super().clean()

        username = data.get("username")
        grant = data.get("grant")
        branch = data.get("branch")

        if username:
            user = User.objects.filter(
                username=username,
                is_active=True,
            ).first()

            if user is None:
                self.add_error(
                    "username",
                    "No active account with this username."
                )
            else:
                self.target_user = user

        scoped_roles = {
            "MANAGER",
            "TRAINER",
            "STUDENT",
        }

        if grant in scoped_roles and not branch:
            self.add_error(
                "branch",
                "A branch is required for this role."
            )

        if grant in {"ADMIN", "STAFF"} and branch:
            self.add_error(
                "branch",
                "Leave branch empty for organization-wide roles."
            )

        if grant == "ADMIN":
            actor_is_owner = Membership.objects.filter(
                organization=self.organization,
                user=self.actor,
                role=Membership.Role.OWNER,
                is_active=True,
            ).exists()

            if not actor_is_owner:
                self.add_error(
                    "grant",
                    "Only an organization owner can grant admin access."
                )

        return data
