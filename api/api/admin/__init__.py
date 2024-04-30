from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.http.response import HttpResponseRedirect
from django.urls import reverse

from oauth2_provider.models import AccessToken

from api.admin.forms import UserPreferencesAdminForm
from api.admin.media_report import (
    AudioReportAdmin,
    ImageReportAdmin,
    MediaReportAdmin,
    MediaSubreportAdmin,
)
from api.admin.site import openverse_admin
from api.models import (
    Audio,
    AudioReport,
    ContentProvider,
    Image,
    ImageReport,
    UserPreferences,
)
from api.models.media import AbstractDeletedMedia, AbstractSensitiveMedia
from api.models.oauth import ThrottledApplication


admin.site = openverse_admin
admin.sites.site = openverse_admin


# Show User and Group views in the Admin view
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    search_fields = ("identifier",)


@admin.register(Audio)
class AudioAdmin(admin.ModelAdmin):
    search_fields = ("identifier",)


# Register the MediaReportAdmin classes and its subclasses

admin.site.register(AudioReport, AudioReportAdmin)
admin.site.register(ImageReport, ImageReportAdmin)

for klass in [
    *AbstractSensitiveMedia.__subclasses__(),
    *AbstractDeletedMedia.__subclasses__(),
]:
    admin.site.register(klass, MediaSubreportAdmin)


@admin.register(ContentProvider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("provider_name", "provider_identifier", "media_type")
    search_fields = ("provider_name", "provider_identifier")
    ordering = ("media_type", "provider_name")


@admin.register(ThrottledApplication)
class ThrottledApplicationAdmin(admin.ModelAdmin):
    search_fields = ("client_id", "name", "rate_limit_model")
    list_display = ("client_id", "name", "created", "rate_limit_model")
    ordering = ("-created",)

    readonly_fields = (
        "skip_authorization",
        "verified",
        "client_id",
        "name",
        "user",
        "algorithm",
        "redirect_uris",
        "post_logout_redirect_uris",
        "client_type",
        "authorization_grant_type",
        "client_secret",
    )


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    search_fields = ("token", "id")
    list_display = ("token", "id", "created", "scope", "expires")
    ordering = ("-created",)

    readonly_fields = (
        "id",
        "user",
        "source_refresh_token",
        "token",
        "id_token",
        "application",
        "expires",
        "scope",
        "created",
        "updated",
    )


@admin.register(UserPreferences)
class IndividualUserPreferencesAdmin(admin.ModelAdmin):
    """
    Model admin for showing user preferences. This should only ever show the
    currently logged-in user's preferences
    """

    verbose_name_plural = "My Preferences"
    verbose_name = "My Preferences"
    form = UserPreferencesAdminForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(user=request.user)

    def has_change_permission(self, request, obj=None):
        return True

    def has_add_permission(*args, **kwargs):
        return False

    def has_delete_permission(*args, **kwargs):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = self.get_queryset(request).first()
        return HttpResponseRedirect(
            reverse("admin:api_userpreferences_change", args=[obj.id])
        )
