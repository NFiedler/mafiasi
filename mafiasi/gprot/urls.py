from django.conf.urls import patterns, url

urlpatterns = patterns('mafiasi.gprot.views',
    url(r'^$', 'index', name='gprot_index'),
    url(r'^view/(\d+)$', 'view_gprot', name='gprot_view'),
    url(r'^create$', 'create_gprot', name='gprot_create'),
)
