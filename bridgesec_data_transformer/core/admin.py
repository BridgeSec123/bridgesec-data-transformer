from django.contrib import admin
from django.contrib.sessions.models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'expire_date', 'get_decoded_data']
    readonly_fields = ['session_key', 'expire_date', 'session_data', 'get_decoded_data']

    def get_decoded_data(self, obj):
        return obj.get_decoded()
    get_decoded_data.short_description = 'Session Data'
