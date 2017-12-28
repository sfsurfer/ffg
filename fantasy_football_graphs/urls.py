from django.conf.urls import url
from . import views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^oauth', views.oauth, name='oauth'),
    url(r'^processing', views.processing, name='processing'),
    url(r'^graph', views.graph, name='graph'),
]

urlpatterns += staticfiles_urlpatterns()
