from django.conf.urls import patterns, include, url
from pdns import views


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'privatedns.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', views.index, name='index'),
    url(r'^new/(?P<name>.+)/(?P<number>\d+)/$', views.add_new),
    #url(r'^index2/$', views.index2),
    url(r'^all_records/(?P<name>.+)/$', views.modify_all),
    url(r'^single/(?P<name>\w+)/(?P<record>.+)/$', views.mod_single_record),
    url(r'^single/(?P<name>.+)/$', views.mod_single),
    #url(r'^new/$', views.add_new),
    url(r'^html/ip/(?P<name>.+)$', views.html_ip, name='html_ip'),
    url(r'^html/name/(?P<name>.+)$', views.html_name),
    #url(r'^text/$', views.index_request, name='index_request'),
    url(r'^text/reverse/(?P<name>.+)/$', views.text_reverse, name='text_reverse'),
    url(r'^text/domain/(?P<domain_name>.+)/$', views.text_all, name='text_all'),
    url(r'^summary/$', views.summary_display),
    url(r'^error/$', views.error_display),
    url(r'^changelog/$', views.changelog),
    url(r'^text/(?P<name>.+)/$', views.text, name='text'),   # $ means that this will only match when there is nothing after it
)
