from django.conf.urls import patterns, include, url
from django.contrib import admin
from pdns import views

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'privatedns.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    
    url(r'^$', include('pdns.urls')),	
    url(r'^admin/', include(admin.site.urls)),
    #url(r'^index2/', include('pdns.urls')),
    url(r'^index/', include('pdns.urls')),
    url(r'^hostname/(?P<name>.+)/$', views.host, name='host'),
    url(r'^bulkcreate/', views.bulkadd),
    url(r'^view/', include('pdns.urls', namespace='pdns')),
    url(r'^add/', include('pdns.urls', namespace='pdns')),
    url(r'^modify/', include('pdns.urls', namespace='pdns')),
)
