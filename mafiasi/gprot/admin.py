from django.contrib import admin

from mafiasi.gprot.models import Attachment, GProt, Notification, Reminder

admin.site.register(Attachment)

class GProtAdmin(admin.ModelAdmin):
    list_display = ('pk', 'course', 'exam_date', 'published', 'is_pdf')
    list_display_links = ('course',)
    list_filter = ('published', 'is_pdf')
    search_fields = ('course__name',)
admin.site.register(GProt, GProtAdmin)

admin.site.register(Notification)
admin.site.register(Reminder)
