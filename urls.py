from django.conf.urls import include, url

from . import views

urlpatterns = [

#BIG CHANGE: we stop using library/something/number urls
# Start using /library/number the level is implicit in the number of ids supplied

#collections and index become one
    url(r'^$', views.collections, name='index'),
#    url(r'^collections$', views.collections, name='collections'),
    url(r'^([\-0-9]+)$', views.collection, name='collection'),
	#While we use edit/master with refato branch, we need the library/master to respond to both new and old view names
    url(r'^([\-0-9]+)$', views.collection, name='document-list'),
#    url(r'^([\-0-9]+)/([0-9]+)$', views.document, name='document'),
    url(r'^([\-0-9]+)/([0-9]+)/([0-9]+)$', views.document_page, name='document_page'),
    url(r'^([\-0-9]+)/([0-9]+)$', views.document_page, name='document_page'),
#    url(r'^([\-0-9]+)/([0-9]+)/([0-9]+)$', views.page, name='page'),
    url(r'^([\-0-9]+)/([0-9]+)/([0-9]+)/([0-9]+)$', views.transcript, name='transcript'),
    url(r'^([\-0-9]+)/([0-9]+)/([0-9]+)/([0-9]+)/([\w-]+)$', views.region, name='region'), #TODO improve regionId regex?
    url(r'^([\-0-9]+)/([0-9]+)/([0-9]+)/([0-9]+)/([\w-]+)/([\w-]+)$', views.line, name='line'), #TODO as above...
    url(r'^([\-0-9]+)/([0-9]+)/([0-9]+)/([0-9]+)/([\w-]+)/([\w-]+)/([\w-]+)$', views.word, name='word'), #TODO as above...
    url(r'^([\-0-9]+)/(word|line|region|transcript|document)$', views.rand, name='rand'),

    url(r'^users/([\-0-9]+)/([0-9]+)$', views.users, name='users'),
    url(r'^coll_metadata/(?P<collId>[0-9]+)$', views.collection_metadata, name='collection_metadata'),
    url(r'^doc_metadata/(?P<collId>[0-9]+)/(?P<docId>[0-9]+)$', views.document_metadata, name='document_metadata'),
]
