from creoleparser import text2html

from django.db import models
from django.conf import settings
from django.utils.timezone import now
from django.utils.safestring import mark_safe

class News(models.Model):
    title = models.CharField(max_length=120)
    teaser = models.TextField()
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(default=now, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL)
    frontpage = models.BooleanField(db_index=True)
    published = models.BooleanField()
    
    def __unicode__(self):
        return u'{0}: {1}'.format(self.created_at, self.title)

    def render_teaser(self):
        return mark_safe(text2html(self.teaser, method='xhtml'))
    
    def render_text(self):
        return mark_safe(text2html(self.text, method='xhtml'))

