#imports of python modules
import json
#import sys
import re
import random
#import os
import sys

#Imports of django modules
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils import translation
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string

from apps.utils.decorators import t_login_required_ajax
from apps.utils.utils import get_ts_session, crop, t_metadata, t_log
from apps.utils.services import *
from apps.utils.views import *

#Imports from app (library)
import settings
import apps.library.settings

#from apps.navigation import navigation

import apps.library.settings

#from .forms import RegisterForm, IngestMetsUrlForm, MetsFileForm, QuickIngestMetsUrlForm

def index(request):
    return render(request, 'library/homepage.html' )

#/library
#view that lists available collections for a user
@login_required
def collections(request):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    collections = t.collections(request,{'empty':'true'})
    if isinstance(collections,HttpResponse):
        return apps.utils.views.error_view(request,collections)

    return render(request, 'library/collections.html', {'collections': collections} )


#/library/{colId}
#view that
# - lists documents
# - also lists pages for documents
@login_required
def collection(request, collId):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    #Avoid this sort of nonsense if possible
    collections = t.collections(request,{'end':None,'start':None,'empty':'true'})
    if isinstance(collections,HttpResponse):
        return apps.utils.views.error_view(request,collections)

    # Get the collection metadata (from colections list)
    collection = apps.utils.utils.collection_from_collections(collections, collId)
    
    # Get the number of tags for this collection for a variety of common tags:
    # Person
    personCount = t.countCollTags(request,{'collId': collId, 'tagName': 'person'})
    if isinstance(personCount,HttpResponse):
        return apps.utils.views.error_view(request,personCount)
    # Place
    placeCount = t.countCollTags(request, {'collId': collId, 'tagName': 'place'})
    if isinstance(placeCount,HttpResponse):
        return apps.utils.views.error_view(request,placeCount)
    # Date
    dateCount = t.countCollTags(request,{'collId': collId, 'tagName': 'date'})
    if isinstance(dateCount,HttpResponse):
        return apps.utils.views.error_view(request,dateCount)
    # Abbreviations
    abbrevCount = t.countCollTags(request,{'collId': collId, 'tagName': 'abbrev'})
    if isinstance(abbrevCount,HttpResponse):
        return apps.utils.views.error_view(request,abbrevCount)
    # Other (?)
    otherCount = t.countCollTags(request,{'collId': collId, 'tagName': 'other'})
    if isinstance(otherCount,HttpResponse):
        return apps.utils.views.error_view(request,otherCount)

    # Lastly lets get some stats on the number of Words in the collection
    collStat = t.collStat(request, {'collId': collId})
    if isinstance(collStat,HttpResponse):
        return apps.utils.views.error_view(request,collStat)

    return render(request, 'library/collection.html', {
					'collection' : collection,
					'nrOfWords' : collStat.get('nrOfWords'),
					'nrOfDocuments' : collection.get('nrOfDocuments'),
					'personCount' : personCount,
					'placeCount' : placeCount,
					'dateCount' : dateCount,
					'abbrevCount' : abbrevCount,
					'otherCount' : otherCount,
				})

#/library/{colId}/{docId}
# view that lists pages in doc and some doc level metadata
@login_required
def document(request, collId, docId, page=None):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    collection = t.collection(request, {'collId': collId})
    if isinstance(collection,HttpResponse):
        return apps.utils.views.error_view(request,collection)
    fulldoc = t.document(request, collId, docId,-1)
    if isinstance(fulldoc,HttpResponse):
        return apps.utils.views.error_view(request,fulldoc)

#    nav = navigation.up_next_prev(request,"document",docId,collection,[collId])

#    navdata = navigation.get_nav(collection,docId,'docId','title')
    #if we didn't have a focus before navigation call, we'll have one after
    #document = navdata.get("focus")
    pagedata = {'document':  fulldoc}
    #merge the dictionaries
#    combidata = pagedata.copy()
#    combidata.update(navdata)

    #merge the dictionaries
    combidata = pagedata.copy()
 #   combidata.update(navdata)

    return render(request, 'library/document.html', combidata)

def _get_collection(document, collId):
    for collection in document['collectionList']['colList']:
        if int(collection['colId']) == int(collId):
            return collection


def collection_metadata(request, collId):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    collections = t.collection(request, {'collId': collId})
    if isinstance(collections,HttpResponse):
        return apps.utils.views.error_view(request,collections)

    collection = _get_collection(collections[0], collId)

    #Add collection of data on last saved page (aka recent)
    recent = t.collection_recent(request,{'collId': collId, 'userid' : request.user.tsdata.userId})
    if isinstance(recent,HttpResponse):
        recent = None
#Don't stop if we don't get recents back from actions/list
#        return apps.utils.views.error_view(request,recent)
 
    #last save data for the doc (generally... not specific to the current user)
    recent_save = t.document_recent(request,{'collId': collId})
    if isinstance(recent_save,HttpResponse):
        recent_save = None
#Don't stop if we don't get recents back from actions/list
#        return apps.utils.views.error_view(request,recent_save)

    title_desc = ''
    title_desc += '<p><b>%s</b> (%s)</p>' % (collection['colName'], collId)
    if 'description' in collection:
        title_desc += '<p id="long_text_%s">%s</p>' % (collId, collection['description'])

    if recent_save :
        #recent will be a single item array
        if 'time' in recent_save[0]:
            title_desc += '<p>%s</p>' % (_('Page %(pageNr)s of %(docName)s last saved on %(time)s</p>') % {'pageNr': recent_save[0].get('pageNr'), 'docName': recent_save[0].get('docName'), 'time': apps.utils.templatetags.str_to_date(recent_save[0].get('time'))})

    if recent :
        #recent will be a single item array
        if 'pageNr' in recent[0]:
            title_desc += str(_('<p>Go to <i>your</i> <a href="%s">last saved page</a> in this collection.</p>')) % reverse('edit:correct', args=[collId,recent[0].get('docId'),recent[0].get('pageNr')])


    #Add collection stats from metadata call
    stats = t.collection_metadata(request,{'collId':collId})
    if isinstance(stats,HttpResponse):
        return apps.utils.views.error_view(request,stats)

    total_pages = stats.get('nrOfNew') +  stats.get('nrOfInProgress') + stats.get('nrOfDone') + stats.get('nrOfFinal') + stats.get('nrOfGT')
    pc_new = int(round((int(stats.get('nrOfNew'))/total_pages) * 100))
    pc_ip = int(round((int(stats.get('nrOfInProgress'))/total_pages) * 100))
    pc_done = int(round((int(stats.get('nrOfDone'))/total_pages) * 100))
    pc_final = int(round((int(stats.get('nrOfFinal'))/total_pages) * 100))
    pc_gt = int(round((int(stats.get('nrOfGT'))/total_pages) * 100))

    stats_table = '<table class="embedded-stats-table">'
    if pc_new > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('New'), pc_new)
    if pc_ip > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('In Progress'), pc_ip)
    if pc_done > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('Done'), pc_done)
    if pc_final > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('Final'), pc_final)
    if pc_gt > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('Ground Truth'), pc_gt)
    stats_table += '</table>'

    return JsonResponse({'titleDesc': title_desc, 'stats': stats, 'stats_table': stats_table}, safe=False)


#Fetch a single thumb url from the document referenced
def document_metadata(request, collId, docId):
    import timeit

    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    #links direct to the various views of the document
    view_links = '<ul class="list-unstyled text-center twi-view-link-list">'
    view_links += '<li class=""><a href="%s?i=i">%s</a></li>' % (reverse('edit:correct', args=[collId, docId, 1]),_('Image'))
    view_links += '<li class=""><a href="%s?i=lbl">%s</a></li>' % (reverse('edit:correct', args=[collId, docId, 1]),_('Line by line'))
    view_links += '<li class=""><a href="%s?i=sbs">%s</a></li>' % (reverse('edit:correct', args=[collId, docId, 1]),_('Side by side'))
    view_links += '<li class=""><a href="%s?i=t">%s</a></li>' % (reverse('edit:correct', args=[collId, docId, 1]),_('Text'))
    view_links += '</ul>'

    #Get data for tags used in this doc
    personCount = t.countDocTags(request,{'collId': collId, 'docId': docId, 'tagName': 'person'})
    placeCount = t.countDocTags(request,{'collId': collId, 'docId': docId, 'tagName': 'place'})
    dateCount = t.countDocTags(request,{'collId': collId, 'docId': docId, 'tagName': 'date'})
    abbrevCount = t.countDocTags(request,{'collId': collId, 'docId': docId, 'tagName': 'abbrev'})
    otherCount = t.countDocTags(request,{'collId': collId, 'docId': docId, 'tagName': 'other'})

    #Most of the metadata can be got from fulldoc now
    fulldoc = t.document(request, collId, docId,-1)
    stats = fulldoc.get('md')

    #data on last saved page for current user (aka recent)
    recent = t.document_recent(request,{'id': docId, 'userid' : request.user.tsdata.userId})
    if isinstance(recent,HttpResponse):
#Don't stop if we don't get recents back from actions/list
        recent = None
        #return apps.utils.views.error_view(request,recent)

    #last save data for the doc (generally... not specific to the current user)
    recent_save = t.document_recent(request,{'id': docId})
    if isinstance(recent_save,HttpResponse):
#Don't stop if we don't get recents back from actions/list
        recent_save = None
        #return apps.utils.views.error_view(request,recent_save)

    #title and description
    title_desc = ''
    title_desc += '<p><b>%s</b> (%s)</p>' % (stats.get('title'), docId)
    if 'desc' in stats:
        title_desc += '<p id="long_text_%s">%s</p>' % (docId, stats.get('desc'))

    if recent_save :
        #recent will be a single item array
        if 'time' in recent_save[0]:
            title_desc += '<p>%s</p>' % (_('Page %(pageNr)s last saved on %(time)s</p>') % {'pageNr': recent_save[0].get('pageNr'), 'time': apps.utils.templatetags.str_to_date(recent_save[0].get('time'))})
    if recent :
        #recent will be a single item array
        if 'pageNr' in recent[0]:
            title_desc += '<p>%s</p>' % (_('Go to <i>your</i> <a href="%(link)s">last saved page</a> in this document') % {'link': reverse('edit:correct', args=[collId,recent[0].get('docId'),recent[0].get('pageNr')])})


    #derive proportion of pages in various states
    total_pages = stats.get('nrOfNew') +  stats.get('nrOfInProgress') + stats.get('nrOfDone') + stats.get('nrOfFinal') + stats.get('nrOfGT')
    pc_new = int(round((int(stats.get('nrOfNew'))/total_pages) * 100))
    pc_ip = int(round((int(stats.get('nrOfInProgress'))/total_pages) * 100))
    pc_done = int(round((int(stats.get('nrOfDone'))/total_pages) * 100))
    pc_final = int(round((int(stats.get('nrOfFinal'))/total_pages) * 100))
    pc_gt = int(round((int(stats.get('nrOfGT'))/total_pages) * 100))

    #build a mini table of the stats to embed in the main table
    stats_table = '<table class="embedded-stats-table">'

    if stats.get('nrOfTranscribedLines') or stats.get('nrOfWords') : 
        stats_table += '<tr><th colspan="2" class="embedded-stats-table-heading">%s</th></tr>' % _('Available for editing')
    if stats.get('nrOfTranscribedLines') : stats_table += '<tr><th>%s</th><td>%s</td></tr>' % (_('Lines'), stats.get('nrOfTranscribedLines'))
    if stats.get('nrOfWordsInLines') : stats_table += '<tr><th>%s</th><td>%s</td></tr>' % (_('Words'), stats.get('nrOfWordsInLines'))

    stats_table += '<tr><th colspan="2" class="embedded-stats-table-heading">%s</th></tr>' % _('Status of pages')
    if pc_new > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('New'), pc_new)
    if pc_ip > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('In Progress'), pc_ip)
    if pc_done > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('Done'), pc_done)
    if pc_final > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('Final'), pc_final)
    if pc_gt > 0 : stats_table += '<tr><th>%s</th><td>%s%%</td></tr>' % (_('Ground Truth'), pc_gt)

    if personCount or placeCount or dateCount or abbrevCount or otherCount :
        stats_table += '<tr><th colspan="2" class="embedded-stats-table-heading">%s</th></tr>' % _('Tags')
    if personCount > 0 : stats_table += '<tr><th>%s</th><td>%s</td></tr>' % (_('People'), personCount)
    if placeCount > 0 : stats_table += '<tr><th>%s</th><td>%s</td></tr>' % (_('Places'), placeCount)
    if dateCount > 0 : stats_table += '<tr><th>%s</th><td>%s</td></tr>' % (_('Dates'), dateCount)
    if abbrevCount > 0 : stats_table += '<tr><th>%s</th><td>%s</td></tr>' % (_('Abbreviations'), abbrevCount)
    if otherCount > 0 : stats_table += '<tr><th>%s</th><td>%s</td></tr>' % (_('Other'), otherCount)

    stats_table += '</table>'

    return JsonResponse({
            'titleDesc': title_desc,
            'viewLinks': view_links,
            'thumbUrl': stats.get('thumbUrl'),
	    'stats_table' : stats_table
        },safe=False)

@login_required
def document_page(request, collId, docId, page=None):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    collection = t.collection(request, {'collId': collId})
    if isinstance(collection,HttpResponse):
        return apps.utils.views.error_view(request,collection)
    full_doc = t.document(request, collId, docId,-1)
    if isinstance(full_doc,HttpResponse):
        return apps.utils.views.error_view(request,full_doc)

    if (page is None):
        page = 1

    index = int(page)-1
    #extract page data from full_doc (may be better from a  separate page data request)
    pagedata = full_doc.get('pageList').get('pages')[index]
#     transcripts = pagedata.get('tsList').get('transcripts')

    sys.stdout.write((str(request)))
    sys.stdout.write((str(request)).rsplit('/', 1)[0])
    sys.stdout.flush()
    startStr = (str(request)).rsplit('/', 1)[0]

    #new for fetching all text regions and text of all pages
    textlines = []
    current_transcript = t.current_transcript(request, collId, docId, page)
    transcript = t.transcript(request, current_transcript.get("tsId"),current_transcript.get("url"))
    regions=transcript.get("PcGts").get("Page").get("TextRegion");

    if isinstance(regions, dict):
        regions = [regions]
#
#
    lineList = []
    if regions:
        sys.stdout.write("number of regions on this page : %s \r\n" % len(regions))
        sys.stdout.flush()
        for y in regions:
            if y is not None:
                lines = y.get("TextLine")
                #region_width = crop(x.get("Coords").get("@points"), 1).get('w')
                if lines:
                    if isinstance(lines, dict):
                        #lines['regionWidth'] = region_width
                        lineList.extend([lines])
                    else: # Assume that lines is a list of lines
                        if lines is not None:
                            for line in lines:
                                #line['regionWidth'] = region_width
                                lineList.extend([line])

    if lineList:
        for line in lineList:
            if line.get('TextEquiv') is not None:
                unicode_string = line.get('TextEquiv').get('Unicode')
            else:
                unicode_string = "";
            line['Unicode'] = unicode_string
            line_crop = crop(line.get("Coords").get("@points"))#,True)
            line['crop'] = line_crop
            line_id = line.get("@id")
            line['id'] = line_id

#     paginator = Paginator(full_doc.get('pageList').get('pages'), 10)  # Show 5 docs per page
#     page = request.GET.get('page')
#     try:
#         doclist = paginator.page(page)
#     except PageNotAnInteger:
#         # If page is not an integer, deliver first page.
#         doclist = paginator.page(1)
#     except EmptyPage:
#         # If page is out of range (e.g. 9999), deliver last page of results.
#         doclist = paginator.page(paginator.num_pages)

    return render(request, 'library/document_page.html', {
        'metadata': full_doc.get('md'),
        'textlines': lineList,
        'pageList': full_doc.get('pageList'),
        'collId': int(collId),
        'docId': int(docId),
        'pageNr': page,
        'pagedata': pagedata
        })



#/library/{colId}/{docId}/{page}
# view that lists transcripts in doc and some page level metadata
@login_required
def page(request, collId, docId, page):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    #call t_document with noOfTranscript=-1 which will return no transcript data
    full_doc = t.document(request, collId, docId, -1)
    if isinstance(full_doc,HttpResponse):
        return apps.utils.views.error_view(request,full_doc)
    # big wodge of data from full doc includes data for each page and for each page, each transcript...
    index = int(page)-1
    #extract page data from full_doc (may be better from a  separate page data request)
    pagedata = full_doc.get('pageList').get('pages')[index]
    transcripts = pagedata.get('tsList').get('transcripts')

    # the way xmltodict parses multiple instances of tags means that if there is one <transcripts> we get a dict,
    # if there is > 1 we get a list. Solution: put dict in list if dict (or get json from transkribus which is
    # parsed better, but not yet available)
    if isinstance(transcripts, dict):
        transcripts = [transcripts]

    return render(request, 'library/page.html', {
        'pagedata': pagedata,
        'transcripts': transcripts,
        'collId': collId,
        'docId': docId,
        })

#/library/{colId}/{docId}/{page}/{tsId}
# view that lists regions in transcript and some transcript level metadata
@login_required
def transcript(request, collId, docId, page, transcriptId):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    #t_page returns an array of the transcripts for a page
    pagedata = t.page(request, collId, docId, page)
    if isinstance(pagedata,HttpResponse):
        return apps.utils.views.error_view(request,pagedata)

    pageXML_url = None;
    for x in pagedata:
        if int(x.get("tsId")) == int(transcriptId):
            pageXML_url = x.get("url")
            break
    sys.stdout.write("PAGEXML URL : %s \r\n" % (pageXML_url) )
    sys.stdout.flush()

    if pageXML_url:
        transcript = t.transcript(request,transcriptId,pageXML_url)
        if isinstance(transcript,HttpResponse):
            return apps.utils.views.error_view(request,transcript)


    regions=transcript.get("PcGts").get("Page").get("TextRegion");

    if isinstance(regions, dict):
        regions = [regions]

    if regions:
        for x in regions:
            sys.stdout.write("CUSTOM : %s \r\n" % (x.get("@custom")) )
            sys.stdout.flush()
            x['md'] = t_metadata(x.get("@custom"))

    return render(request, 'library/transcript.html', {
                'transcript' : transcript,
                'regions' : regions,
               'collId': collId,
                'docId': docId,
                'pageId': page, #NB actually the number for now
                })

#/library/{colId}/{docId}/{page}/{tsId}/{regionId}
# view that lists lines in region and some region level metadata
@login_required
def region(request, collId, docId, page, transcriptId, regionId):

    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    # We need to be able to target a transcript (as mentioned elsewhere)
    # here there is no need for anything over than the pageXML really
    # we could get one transcript from ...{page}/curr, but for completeness would
    # rather use transciptId to target a particular transcript
    transcripts = t.page(request,collId, docId, page)
    if isinstance(transcripts,HttpResponse):
        return apps.utils.views.error_view(request,transcripts)

    #To get the page image url we need the full_doc (we hope it's been cached)
    full_doc = t.document(request, collId, docId, -1)
    if isinstance(full_doc,HttpResponse):
        return apps.utils.views.error_view(request,full_doc)

    index = int(page)-1
    # and then extract the correct page from full_doc (may be better from a  separate page data request??)
    pagedata = full_doc.get('pageList').get('pages')[index]

    t_log("############# TRANSCRIPTS: %s" % transcripts )

    #we are only using the transcripts to get the pageXML for a particular transcript...
    pageXML_url = None;
    for x in transcripts:
        if int(x.get("tsId")) == int(transcriptId):
            t_log("############# transcript id comp: %s" % x.get("tsId") )
            t_log("############# transcript id comp: %s" % transcriptId )
            pageXML_url = x.get("url")
            break

    t_log("############# PAGEXML_url: %s" % pageXML_url )

    if pageXML_url:
        transcript = t.transcript(request,transcriptId,pageXML_url)
        if isinstance(transcript,HttpResponse):
            return apps.utils.views.error_view(request,transcript)

    regions=transcript.get("PcGts").get("Page").get("TextRegion");
    if isinstance(regions, dict):
        regions = [regions]

    for x in regions:
        x['key'] = x.get("@id")
        if(str(regionId) == str(x.get("@id"))):
            region = x

    if(region.get("Coords")):
        region['crop'] = crop(region.get("Coords").get("@points"),True)

    lines = region.get("TextLine")
    if isinstance(lines, dict):
        lines = [lines]
    #parse metadata
    if lines:
        for x in lines:
            x['md'] = t_metadata(x.get("@custom"))

    return render(request, 'library/region.html', {
                'region' : region,
                'lines' : lines,
                'collId': collId,
                'docId': docId,
                'pageId': page, #NB actually the number for now
                'transcriptId': transcriptId,
                'imageUrl' : pagedata.get("url"),
                })


#/library/{colId}/{docId}/{page}/{tsId}/{regionId}/{lineId}
# view that lists words in line and some line level metadata
@login_required
def line(request, collId, docId, page, transcriptId, regionId, lineId):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    # We need to be able to target a transcript (as mentioned elsewhere)
    # here there is no need for anything over than the pageXML really
    # we could get one transcript from ...{page}/curr, but for completeness would
    # rather use transciptId to target a particular transcript
    transcripts = t.page(request,collId, docId, page)
    if isinstance(transcripts,HttpResponse):
        return apps.utils.views.error_view(request,transcripts)
    #we are only using the transcripts to get the pageXML for a particular
    pageXML_url = None;
    for x in transcripts:
        if int(x.get("tsId")) == int(transcriptId):
            pageXML_url = x.get("url")
            break

    if pageXML_url:
        transcript = t.transcript(request,transcriptId,pageXML_url)
        if isinstance(transcript,HttpResponse):
            return apps.utils.views.error_view(request,transcript)

    #To get the page image url we need the full_doc (we hope it's been cached)
    full_doc = t.document(request, collId, docId, -1)
    if isinstance(full_doc,HttpResponse):
        return apps.utils.views.error_view(request,full_doc)

    index = int(page)-1
    # and then extract the correct page from full_doc (may be better from a  separate page data request??)
    pagedata = full_doc.get('pageList').get('pages')[index]

    #This now officially bonkers....
    regions=transcript.get("PcGts").get("Page").get("TextRegion");
    if isinstance(regions, dict):
        regions = [regions]

    for x in regions:
        if(str(regionId) == str(x.get("@id"))):
            region = x

    lines=region.get("TextLine");

    if isinstance(lines, dict):
        lines = [lines]


    for x in lines:
        x['key'] = x.get("@id")
        if(str(lineId) == str(x.get("@id"))):
            line = x

    if(line.get("Coords")):
        line['crop'] = crop(line.get("Coords").get("@points"),True)

    words = line.get("Word")
    if isinstance(words, dict):
        words = [words]
    #parse metadata
    if words:
        for x in words:
            x['md'] = t_metadata(x.get("@custom"))

    return render(request, 'library/line.html', {
                'line' : line,
                'words' : words,
                'collId': collId,
                'docId': docId,
                'pageId': page, #NB actually the number for now
                'transcriptId': transcriptId,
                'regionId': regionId,
                'lineId': lineId,
                'imageUrl' : pagedata.get("url"),
                })

#/library/{colId}/{docId}/{page}/{tsId}/{regionId}/{lineId}/{wordId}
# view that shows some word level metadata
@login_required
def word(request, collId, docId, page, transcriptId, regionId, lineId, wordId):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    # booo hiss
    transcripts = t.page(request, collId, docId, page)
    if isinstance(transcripts,HttpResponse):
        return apps.utils.views.error_view(request,transcripts)
    #we are only using the pagedata to get the pageXML for a particular
    pageXML_url = None;
    for x in transcripts:
        if int(x.get("tsId")) == int(transcriptId):
            pageXML_url = x.get("url")
            break

    if pageXML_url:
        transcript = t.transcript(request,transcriptId,pageXML_url)
        if isinstance(transcript,HttpResponse):
            return apps.utils.views.error_view(request,transcript)

    #To get the page image url we need the full_doc (we hope it's been cached)
    full_doc = t.document(request, collId, docId, -1)
    if isinstance(full_doc,HttpResponse):
        return apps.utils.views.error_view(request,full_doc)

    index = int(page)-1
    # and then extract the correct page from full_doc (may be better from a  separate page data request??)
    pagedata = full_doc.get('pageList').get('pages')[index]

    #This now officially bonkers....
    regions=transcript.get("PcGts").get("Page").get("TextRegion");
    if isinstance(regions, dict):
        regions = [regions]

    for x in regions:
        if(str(regionId) == str(x.get("@id"))):
            region = x

    lines=region.get("TextLine");

    if isinstance(lines, dict):
        lines = [lines]

    for x in lines:
        if(str(lineId) == str(x.get("@id"))):
            line = x

    words = line.get("Word")
    if isinstance(words, dict):
        words = [words]

    #parse metadata
    for x in words:
        x['key'] = x.get("@id")
        if(str(wordId) == str(x.get("@id"))):
            x['md'] = t_metadata(x.get("@custom"))
            word = x

    if(word.get("Coords")):
        word['crop'] = crop(word.get("Coords").get("@points"),True)

    return render(request, 'library/word.html', {
                'word' : word,
                'collId': collId,
                'docId': docId,
                'pageId': page, #NB actually the number for now
                'transcriptId': transcriptId,
                'regionId': regionId,
                'lineId': lineId,
                'imageUrl' : pagedata.get("url"),
                })

# Randomly fetch region/line/word this gives us an awful lot of empty responses
# Ideally we want to filter out the transcripts that don't contain good qulity data
# This may be as simple as isPublished(), rather than any analysis on the content
@login_required
def rand(request, collId, element):
    t = get_ts_session(request)
    if isinstance(t,HttpResponse) :
        return error_view(request,t)

    collection = t.collection(request, {'collId': collId})

    if isinstance(collection,HttpResponse):
        return apps.utils.views.error_view(request,collection)

    doc = random.choice(collection)

    collection = None
    for x in doc.get("collectionList").get("colList"):
        if str(x.get("colId")) == str(collId):
            collection = x

    pages  = t.document(request, collId, doc.get("docId"), 0)
    if isinstance(pages,HttpResponse):
        return apps.utils.views.error_view(request,pages)
    page = random.choice(pages.get("pageList").get("pages"))

    sys.stdout.write("RANDOM PAGE: %s\r\n" % (page.get("pageNr")) )
    sys.stdout.flush()

    #best to avoid a random transcript, so we'll go for the current in the hope that it is best....
    current_transcript = t.current_transcript(request, collId, doc.get("docId"), page.get("pageNr"))
    transcript = t.transcript(request, current_transcript.get("tsId"),current_transcript.get("url"))

    word = None
    line = None
    region = None

    regions = transcript.get("PcGts").get("Page").get("TextRegion")
    if isinstance(regions, dict):
        regions = [regions]

    if regions:
        region = random.choice(regions)
        if element == "region" :
            sys.stdout.write("region I have\r\n" )
        lines = region.get("TextLine")
    else:
        if transcript.get("PcGts").get("Page").get("TextLine"):
            # I don't think we ever get here.. need to check with UIBK if Page > TextLine is even possible
            sys.stdout.write("I HAVE A LINE DIRECT IN PAGE\r\n" )
            sys.stdout.flush()
            lines = transcript.get("PcGts").get("Page").get("TextLine")
        else:
            sys.stdout.write("NO TEXT IN REGION\r\n" )
            return render(request, 'library/random.html', {
                        "level": element,
                        "text": {},
                        "collection" : collection,
                        "document" : doc,
                        "page" : page,
                        "transcript" : transcript,
                        } )

    if isinstance(lines, dict):
        lines = [lines]

    if element in ['line', 'word'] :
        if lines:
            line = random.choice(lines);
        else:
            return render(request, 'library/random.html', {
                            "level": element,
                            "text": {},
                            "collection" : collection,
                            "document" : doc,
                            "page" : page,
                            "transcript" : transcript,
                            } )

        sys.stdout.write("LINE: %s\r\n" % ( line ) )
        if element == "word" :
            words = line.get("Word")
            if isinstance(words, dict):
                words = [words]

            if words:
                word = random.choice(words);
            else:
                return render(request, 'library/random.html', {
                                "level": element,
                                "text": {},
                                "collection" : collection,
                                "document" : doc,
                                "page" : page,
                                "transcript" : transcript,
                                } )

    switcher = {
        "region" : display_random(request,element,region,collection,doc,page),
        "line" : display_random(request,element,line,collection,doc,page),
        "word" : display_random(request,element,word,collection,doc,page),
    }

    return switcher.get(element, {})

def display_random(request,level,data, collection, doc, page):
    text = None
    if not data :
        text = {}
    elif data.get("TextEquiv"):
        if data.get("TextEquiv").get("Unicode"):
            text = str(data.get("TextEquiv").get("Unicode"))

    return render(request, 'library/random.html', {
                "level": level,
                "text": text,
                "collection" : collection,
                "document" : doc,
                "page" : page,
        } )

@login_required
def users(request, collId, userId):
    return render(request, 'library/users.html')


