
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    AuditEvent,
    Branch,
    BranchAssignment,
    Membership,
    Organization,
)


User = get_user_model()


class WorkspaceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username="workspace_owner",
            password="ExampleStrongPass123!",
        )

        cls.admin_user = User.objects.create_user(
            username="workspace_admin",
            password="ExampleStrongPass123!",
        )

        cls.manager = User.objects.create_user(
            username="workspace_manager",
            password="ExampleStrongPass123!",
        )

        cls.new_user = User.objects.create_user(
            username="workspace_new",
            password="ExampleStrongPass123!",
        )

        cls.org = Organization.objects.create(
            name="Academy One",
            slug="academy-one",
        )

        cls.other_org = Organization.objects.create(
            name="Academy Two",
            slug="academy-two",
        )

        cls.branch = Branch.objects.create(
            organization=cls.org,
            name="Kochi",
            code="KOC",
        )

        cls.other_branch = Branch.objects.create(
            organization=cls.org,
            name="Bangalore",
            code="BLR",
        )

        cls.foreign_branch = Branch.objects.create(
            organization=cls.other_org,
            name="Foreign Branch",
            code="EXT",
        )

        Membership.objects.create(
            organization=cls.org,
            user=cls.owner,
            role=Membership.Role.OWNER,
        )

        Membership.objects.create(
            organization=cls.org,
            user=cls.admin_user,
            role=Membership.Role.ADMIN,
        )

        Membership.objects.create(
            organization=cls.org,
            user=cls.manager,
            role=Membership.Role.STAFF,
        )

        cls.assignment = BranchAssignment.objects.create(
            branch=cls.branch,
            user=cls.manager,
            role=BranchAssignment.Role.MANAGER,
        )

    def dashboard_url(self):
        return reverse(
            "workspace-dashboard",
            kwargs={"org_slug": self.org.slug},
        )

    def members_url(self):
        return reverse(
            "workspace-members",
            kwargs={"org_slug": self.org.slug},
        )

    def create_branch_url(self):
        return reverse(
            "workspace-branch-create",
            kwargs={"org_slug": self.org.slug},
        )

    def test_owner_can_open_dashboard(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.dashboard_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Academy One")

    def test_manager_only_sees_assigned_branch(self):
        self.client.force_login(self.manager)

        response = self.client.get(self.dashboard_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kochi")
        self.assertNotContains(response, "Bangalore")

    def test_owner_can_create_branch_with_audit(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            self.create_branch_url(),
            {
                "name": "Calicut",
                "code": "CLT",
                "city": "Kozhikode",
            },
        )

        self.assertEqual(response.status_code, 302)

        branch = Branch.objects.get(
            organization=self.org,
            code="CLT",
        )

        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.org,
                action="branch.created",
                resource_id=str(branch.pk),
            ).exists()
        )

    def test_manager_cannot_create_branch(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            self.create_branch_url(),
            {
                "name": "Unauthorized",
                "code": "BAD",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            Branch.objects.filter(code="BAD").exists()
        )

    def test_cross_organization_edit_is_blocked(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse(
                "workspace-branch-edit",
                kwargs={
                    "org_slug": self.org.slug,
                    "branch_id": self.foreign_branch.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_manager_cannot_open_member_directory(self):
        self.client.force_login(self.manager)

        response = self.client.get(self.members_url())

        self.assertEqual(response.status_code, 403)

    def test_owner_can_assign_existing_user(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            self.members_url(),
            {
                "username": self.new_user.username,
                "grant": "TRAINER",
                "branch": str(self.branch.pk),
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Membership.objects.filter(
                organization=self.org,
                user=self.new_user,
                role=Membership.Role.TRAINER,
                is_active=True,
            ).exists()
        )

        self.assertTrue(
            BranchAssignment.objects.filter(
                branch=self.branch,
                user=self.new_user,
                role=BranchAssignment.Role.TRAINER,
                is_active=True,
            ).exists()
        )

    def test_non_owner_admin_cannot_grant_admin(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            self.members_url(),
            {
                "username": self.new_user.username,
                "grant": "ADMIN",
                "branch": "",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            Membership.objects.filter(
                organization=self.org,
                user=self.new_user,
                role=Membership.Role.ADMIN,
            ).exists()
        )

    def test_foreign_branch_grant_is_rejected(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            self.members_url(),
            {
                "username": self.new_user.username,
                "grant": "TRAINER",
                "branch": str(self.foreign_branch.pk),
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            Membership.objects.filter(
                organization=self.org,
                user=self.new_user,
            ).exists()
        )

    def test_revoke_branch_access(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse(
                "workspace-assignment-revoke",
                kwargs={
                    "org_slug": self.org.slug,
                    "assignment_id": self.assignment.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 302)

        self.assignment.refresh_from_db()
        self.assertFalse(self.assignment.is_active)

        self.assertTrue(
            AuditEvent.objects.filter(
                action="branch_access.revoked",
                resource_id=str(self.assignment.pk),
            ).exists()
        )

    def test_revoked_role_cannot_use_old_assignment(self):
        Membership.objects.create(
            organization=self.org,
            user=self.manager,
            role=Membership.Role.STUDENT,
        )

        staff_membership = Membership.objects.get(
            organization=self.org,
            user=self.manager,
            role=Membership.Role.STAFF,
        )

        staff_membership.is_active = False
        staff_membership.save(update_fields=["is_active"])

        self.client.force_login(self.manager)

        response = self.client.get(self.dashboard_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Kochi")

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)

        response = client.post(
            self.create_branch_url(),
            {
                "name": "CSRF Test",
                "code": "CSRF",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            Branch.objects.filter(code="CSRF").exists()
        )
