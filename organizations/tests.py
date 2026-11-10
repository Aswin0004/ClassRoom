
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Organization,
    Branch,
    Membership,
    BranchAssignment,
)


User = get_user_model()


class OrganizationAccessTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username="owner",
            password="ExampleStrongPass123!",
        )

        cls.manager = User.objects.create_user(
            username="manager",
            password="ExampleStrongPass123!",
        )

        cls.org_a = Organization.objects.create(
            name="Academy A",
            slug="academy-a",
        )

        cls.org_b = Organization.objects.create(
            name="Academy B",
            slug="academy-b",
        )

        cls.branch_a1 = Branch.objects.create(
            organization=cls.org_a,
            name="Branch A1",
            code="A1",
        )

        cls.branch_a2 = Branch.objects.create(
            organization=cls.org_a,
            name="Branch A2",
            code="A2",
        )

        cls.branch_b = Branch.objects.create(
            organization=cls.org_b,
            name="Branch B",
            code="B1",
        )

        Membership.objects.create(
            organization=cls.org_a,
            user=cls.owner,
            role=Membership.Role.OWNER,
        )

        Membership.objects.create(
            organization=cls.org_a,
            user=cls.manager,
            role=Membership.Role.STAFF,
        )

        BranchAssignment.objects.create(
            branch=cls.branch_a1,
            user=cls.manager,
            role=BranchAssignment.Role.MANAGER,
        )

    def test_owner_can_see_all_own_branches(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse(
                "branch-list-create",
                kwargs={"org_slug": "academy-a"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_manager_sees_only_assigned_branch(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse(
                "branch-list-create",
                kwargs={"org_slug": "academy-a"},
            )
        )

        self.assertEqual(response.status_code, 200)

        codes = [
            item["code"]
            for item in response.json()
        ]

        self.assertEqual(codes, ["A1"])

    def test_manager_cannot_access_another_organization(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse(
                "branch-list-create",
                kwargs={"org_slug": "academy-b"},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_manager_cannot_create_branch(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse(
                "branch-list-create",
                kwargs={"org_slug": "academy-a"},
            ),
            {
                "name": "Unauthorized Branch",
                "code": "A3",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            Branch.objects.filter(code="A3").exists()
        )

    def test_owner_can_create_branch(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse(
                "branch-list-create",
                kwargs={"org_slug": "academy-a"},
            ),
            {
                "name": "New Branch",
                "code": "A3",
                "city": "Kochi",
            },
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(
            Branch.objects.filter(
                organization=self.org_a,
                code="A3",
            ).exists()
        )

    def test_anonymous_user_cannot_list_organizations(self):
        response = self.client.get(
            reverse("organization-list")
        )

        self.assertEqual(response.status_code, 403)

    def test_revoked_manager_loses_branch_access(self):
        assignment = BranchAssignment.objects.get(
            branch=self.branch_a1,
            user=self.manager,
        )

        assignment.is_active = False
        assignment.save()

        self.client.force_login(self.manager)

        response = self.client.get(
            reverse(
                "branch-list-create",
                kwargs={"org_slug": "academy-a"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
