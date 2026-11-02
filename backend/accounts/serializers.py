
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from .models import UserProfile

User = get_user_model()


class RegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        # The default Django User model also requires a unique username.
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": "The passwords do not match."
            })

        user = User(
            username=attrs["email"],
            email=attrs["email"],
            first_name=attrs["name"],
        )

        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({
                "password": list(exc.messages)
            }) from exc

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data["password"]
        email = validated_data["email"]
        name = validated_data["name"]

        try:
            user = User(
                username=email,
                email=email,
                first_name=name,
            )
            user.set_password(password)
            user.save()

            UserProfile.objects.create(
                user=user,
                email_verified=False,
            )

        except IntegrityError as exc:
            raise serializers.ValidationError({
                "email": "An account with this email already exists."
            }) from exc

        return user





class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    preferred_market = serializers.CharField(
        source="profile.preferred_market",
        read_only=True,
    )
    risk_tolerance = serializers.CharField(
        source="profile.risk_tolerance",
        read_only=True,
    )
    investment_horizon = serializers.CharField(
        source="profile.investment_horizon",
        read_only=True,
    )
    preferred_sectors = serializers.ListField(
        child=serializers.CharField(max_length=100),
        source="profile.preferred_sectors",
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "name",
            "first_name",
            "last_name",
            "profile_picture",
            "preferred_market",
            "risk_tolerance",
            "investment_horizon",
            "preferred_sectors",
        )
        read_only_fields = (
            "id",
            "username",
            "email",
            "last_name",
            "profile_picture",
            "preferred_market",
            "risk_tolerance",
            "investment_horizon",
            "preferred_sectors",
        )

    def get_name(self, obj):
        return obj.get_full_name() or obj.email or obj.username

    def get_profile_picture(self, obj):
        profile = getattr(obj, "profile", None)

        if not profile or not profile.profile_picture:
            return None

        request = self.context.get("request")
        picture_url = profile.profile_picture.url

        if request:
            return request.build_absolute_uri(picture_url)

        return picture_url
