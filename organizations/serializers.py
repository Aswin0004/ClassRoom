
from rest_framework import serializers

from .models import Organization, Branch


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug"]
        read_only_fields = fields


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "code",
            "city",
            "is_active",
        ]
        read_only_fields = ["id", "is_active"]

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        organization = self.context["organization"]

        code = attrs.get("code")

        if code and Branch.objects.filter(
            organization=organization,
            code=code,
        ).exists():
            raise serializers.ValidationError({
                "code": "This branch code already exists."
            })

        return attrs
