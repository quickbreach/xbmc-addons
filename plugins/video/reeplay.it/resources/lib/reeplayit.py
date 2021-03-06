"""
    Support module for reeplay.it Plugin.
    Written by BigBellyBilly - 2009
"""
import urllib2, sys, os, os.path
import cookielib, traceback
import xbmc, xbmcgui, xbmcplugin
import xbmcutils.net as net
from xml.sax.saxutils import unescape
from pprint import pprint

__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__title__ = "reeplayitLib"
__author__ = 'BigBellyBilly [BigBellyBilly@gmail.com]'
__date__ = '18-02-2009'
xbmc.output("Imported From: " + __scriptname__ + " title: " + __title__ + " Date: " + __date__)

DIR_HOME = sys.modules[ "__main__" ].DIR_HOME
DIR_CACHE = sys.modules[ "__main__" ].DIR_CACHE
__lang__ = sys.modules[ "__main__" ].__lang__

from bbbLib import *
from bbbSkinGUILib import TextBoxDialogXML
################################################################################################
################################################################################################
class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    """Handle temporary redirection"""
    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)
        result.status = code
        return result

################################################################################################
################################################################################################
class ReeplayitLib:
    """ Reeplay.it data gatherer / store """

    URL_BASE = "http://reeplay.it/"        # LIVE: "http://reeplay.it/" DEV: http://staging.reeplay.it

    def __init__(self, user, pwd, pageSize=50, highVQ=True, docType='xml'):
        log("ReeplayitLib().__init__ %s pageSize=%d highVQ=%s docType=%s" % (user,pageSize,highVQ,docType))

        self.pageSize = pageSize
        self.docType = docType
        self.setVideoProfile(highVQ)

        self.PROP_ID = "ID"                    # pls id
        self.PROP_COUNT = "COUNT"            # pls video count
        self.PROP_URL = "URL"                # video url

        try:
            # password manager handler
            passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passman.add_password(None, self.URL_BASE, user, pwd)

            # Basic Auth. handler
            authhandler = urllib2.HTTPBasicAuthHandler(passman)

            # Cookie handler
            cookiejar = cookielib.LWPCookieJar()
            cookiehandler = urllib2.HTTPCookieProcessor(cookiejar)

            # add our handlers
            urlopener = urllib2.build_opener(authhandler, cookiehandler, SmartRedirectHandler())

            # install urlopener so all urllib2 calls use our handlers
            urllib2.install_opener(urlopener)
            log("HTTP handlers installed")
        except:
            handleException("HTTP handlers")
            return

        self.URL_PLAYLISTS = self.URL_BASE + "users/"+user+"/playlists."+self.docType
        self.URL_PLAYLIST = self.URL_BASE + "users/"+user+"/playlists/%s."+self.docType+"?page=%s&page_size=%s"
        self.URL_VIDEO_INFO = self.URL_BASE + "users/"+user+"/contents/%s."+self.docType + "?profile=%s"

        self.plsListItems = []
        self.videoListItems = []
        self.DEFAULT_THUMB_IMG = os.path.join( DIR_HOME, "default.tbn" )
        self.isPluginAuth = False

    ################################################################################################
    def setVideoProfile(self, highVQ=True):
        self.vqProfile = ( 'xbmc_standard','xbmc_high' )[highVQ]
        log("setVideoProfile() %s" % self.vqProfile)

    ################################################################################################
    def setPageSize(self, pageSize):
        self.pageSize = pageSize

    ################################################################################################
    def retrieve(self, url, post=None, headers={}, fn=None):
        """ Downloads an url. Returns: None = error , '' = cancelled """
        log("retrieve() %s" % url)
        try:
            return net.retrieve (url, post, headers, self.report_hook, self.report_udata, fn)
        except net.AuthError, e:
            messageOK(__lang__(0), __lang__(108))
        except net.DownloadAbort, e:
            messageOK(__lang__(102), e.value)
            return "" # means aborted
        except net.DownloadError, e:
            messageOK(__lang__(102), e.value)
        except:
            handleException(__lang__(0))
        return None

    ################################################################################################
    def set_report_hook(self, func, udata=None):
        """Set the download progress report handler."""
        log("set_report_hook()")
        self.report_hook = func
        self.report_udata = udata

    ################################################################################################
    def getPlaylists(self):
        log("> getPlaylists()")

        if not self.plsListItems:

            dialogProgress.create(__lang__(0), __lang__(215))
            self.set_report_hook(self.progressHandler, dialogProgress)

            # if exist, load from cache
            docFN = os.path.join( DIR_CACHE, os.path.basename(self.URL_PLAYLISTS) )
            data = readFile(docFN)
            if not data:
                # not in cache, download
                data = self.retrieve(self.URL_PLAYLISTS)

            if data:
                items = self.parsePlaylists(data)

                # load data into content list
                log("storing data to listItems ...")
                for item in items:
                    try:
                        title, id, desc, count, updatedDate, imgURL = item

                        # convert YYYY-MM-DD to DD-MM-YYY
                        try:
                            updatedDate = "%s-%s-%s" % ( updatedDate[ 8:10 ], updatedDate[ 5:7 ], updatedDate[ :4 ] )
                        except:
                            print "bad date formatting updatedDate %s" % updatedDate

                        longTitle = "%s (%s)" % (title, count)
                        # let xbmc download thumb in background, just supply url
                        li = xbmcgui.ListItem(longTitle, desc, "DefaultFolder.png", imgURL)
                        li.setProperty(self.PROP_ID, id)
                        li.setProperty(self.PROP_COUNT, str(count))
                        li.setInfo("video", {"Title" : title, "Size": count, "Album" : desc, \
                                            "Plot" : desc, "Date" : updatedDate})
                        self.plsListItems.append(li)
                    except:
                        traceback.print_exc()

                del items
            dialogProgress.close()

        count = len(self.plsListItems)
        log("< getPlaylists() count=%s" % count)
        return count

    ################################################################################################
    def getPlaylist(self, plsId="", page=1, pageSize=0):
        """ Download video list for playlist """
        log("> getPlaylist() plsId=%s page=%d pageSize=%d" % (plsId, page, pageSize))

        # reset stored videos
        self.videoListItems = []
        totalsize = 0
        # use settings pageSize, unless overridden
        if not pageSize:
            pageSize = self.pageSize

        # load cached file
        docFN = os.path.join( DIR_CACHE, "%s_page_%d.%s" % (plsId, page, self.docType) )
        data = readFile(docFN)
        if not data:
            # not cached, download
            url = self.URL_PLAYLIST % (plsId, page, pageSize)
            data = self.retrieve(url)
            saveData(data, docFN)

        if data:
            dialogProgress.update(0, __lang__(210), "") # parsing
            items = self.parsePlaylist(data)

            # load data into content list
            if items:
                log("storing items as listitems ...")
                totalsize = len(items)

                dialogProgress.update(0, __lang__(210)) # + " (%d) % totalsize")
                lastPercent = 0
                for itemCount, item in enumerate(items):
                    try:
                        title, videoid, captured, link, imgURL, duration = item
                        link += "?profile=%s" % self.vqProfile
                        if not videoid:
                            continue

                        # convert YYYY-MM-DD to DD-MM-YYY
                        try:
                            captured = "%s-%s-%s" % ( captured[ 8:10 ], captured[ 5:7 ], captured[ :4 ] )
                        except:
                            print "bad date formatting captured %s" % captured

                        percent = int((itemCount * 100.0) / totalsize)
                        if percent != lastPercent and percent % 5 == 0:
                            lastPercent = percent
                            countMsg = "(%d / %d)" % (itemCount+1, totalsize)
                            dialogProgress.update(percent, __lang__(210), countMsg )
                            if dialogProgress.iscanceled():
                                log("parsing cancelled")
                                break

                        lbl2 = "%.1f mins" % (float(duration) / 60)
                        # let xbmc download thumb in background, just supply url
                        li = xbmcgui.ListItem(title, lbl2, "DefaultVideo.png", imgURL)
                        li.setInfo("video", {"Title" : title, "Date" : captured, "Duration" : duration})
                        li.setProperty(self.PROP_ID, videoid)
                        li.setProperty(self.PROP_URL, link)
                        self.videoListItems.append(li)
                    except:
                        traceback.print_exc()

                del items

        # delete file if failed to parse etc
        if not self.videoListItems:
            deleteFile(docFN)

        log("< getPlaylist() totalsize=%s" % totalsize)
        return totalsize

    ################################################################################################
    def getVideo(self, idx=-1, id="", title="", stream=False):
        """ stream the selected video info doc to get video url """
        log("> getVideo() idx=%s id=%s stream=%s" % (idx, id, stream))
        fn = None

        # get LI info
        if not id:
            li = self.getVideoLI(idx)
            title = li.getLabel()
            id = li.getProperty(self.PROP_ID)
#            infoUrl = li.getProperty(self.PROP_URL)
            log("From idx; id=%s title=%s" % (id, title))
        else:
            # from plugin, create a video li
            li = xbmcgui.ListItem( title )
            li.setInfo("video", {"Title" : title})

        fn = self.doesVideoExist(id)    # no need to get video info doc if we have video

        if not fn:
            videoURL = self.getVideoMediaUrl(id, title)

            # download and save video from its unique media-url
            if videoURL:
                # download video to cache (no need to handle redirection as urllib2 does this)
                basename = os.path.basename(videoURL)
                videoName = "%s_%s%s" % (id, self.vqProfile, os.path.splitext(basename)[1])        # eg ".mp4"
                fn = os.path.join( DIR_CACHE, videoName )
                if not stream:
                    log("download video")
                    dialogProgress.update(0,  __lang__(223))
                    if not self.retrieve(videoURL, fn=fn):
                        deleteFile(fn)    # delete incase of partial DL
                        fn = ''
                else:
                    log("stream video")
                    fn = videoURL

        log("< getVideo() fn=%s li=%s" % (fn, li))
        return (fn, li)

    ################################################################################################
    def doesVideoExist(self, id):
        """ Look for existing video file based on id and VQ """

        exts = ('.ts','.mp4')
        for ext in exts:
            fn = os.path.join( DIR_CACHE, "%s_%s%s" % (id, self.vqProfile, ext) )
            if fileExist(fn):
                return fn
        return None

    ################################################################################################
    def getVideoMediaUrl(self, videoId, title=""):
        """ Download the selected video info doc to get video url """
        log("> getVideoMediaUrl() videoId=%s" % videoId)

        videoURL = ""
        infoUrl = self.URL_VIDEO_INFO % (videoId, self.vqProfile)
        log("infoUrl=" + infoUrl)

        # if exist, load cached
        docFN = os.path.join( DIR_CACHE, "%s_%s.%s" % (videoId, self.vqProfile, self.docType) )
        data = readFile(docFN)

        # Need to do this every time method is called, including when the info is cached
        # Otherwise a second play of the same video won't  be authenticated
        if not self.isPluginAuth:
            log("http authenticate ...")
            # This is for Plugin; as it won't have done Auth. before getVideo() call
            dialogProgress.update(0, __lang__(209), title)  # loggin in
            if not self.retrieve(self.URL_PLAYLISTS):
                dialogProgress.close()
                messageOK("Error", __lang__(108))    # auth failed.
                log("< getVideoMediaUrl() failed auth.")
                return None
            self.isPluginAuth = True

        if not data:
            # video info not cached, download
            dialogProgress.update(0, __lang__(222), title)  # download info
            data = self.retrieve(infoUrl)
            saveData(data, docFN)

        if data:
            videoURL = self.parseVideo(data)

            # Check for redirection, and use redirected url if necessary
            log("Check for redirection %s" % videoURL)
            f = urllib2.urlopen(unescape(videoURL))
            try:
                if f.status == 302:
                    log("URL redirected to %s" % f.url)
                    videoURL = f.url
                    f.close()
            except AttributeError:
                pass

        if not videoURL:
            dialogProgress.close()
            messageOK(__lang__(0), "Video Media URL missing!")
            deleteFile(docFN) # incase its a bad info doc

        log("< getVideoMediaUrl() videoURL=%s" % videoURL)
        return videoURL

    ################################################################################################
    def getPlsLI(self, idx):
        try:
            return self.plsListItems[idx]
        except:
            return None

    ################################################################################################
    def getVideoLI(self, idx):
        try:
            return self.videoListItems[idx]
        except:
            return None

    ################################################################################################
    def getMaxPages(self, plsCount):
        maxPages = int(plsCount / self.pageSize)
        mod = plsCount % self.pageSize
        if mod:
            maxPages += 1
        log("getMaxPages() %d" % maxPages)
        return maxPages

    ################################################################################################
    def progressHandler(self, count, totalsize, dlg):
        """Update progress dialog percent and return abort status."""

        try:
            if count and totalsize:
                percent = int((count * 100) / totalsize)
                if (percent % 5) == 0:
                    dlg.update( percent )
        except:
            traceback.print_exc()

        return not dlg.iscanceled()

    ################################################################################################
    def parsePlaylists(self, doc):
        """ Wrapper to call Playlists parsing """
        log("parsePlaylists()")
        if self.docType == "json":
            return parsePlaylistsJSON(doc)
        else:
            return parsePlaylistsXML(doc)

    ################################################################################################
    def parsePlaylist(self, doc):
        """ Wrapper to call Playlist parsing """
        log("parsePlaylist()")
        if self.docType == "json":
            return parsePlaylistJSON(doc)
        else:
            return parsePlaylistXML(doc)

    ################################################################################################
    def parseVideo(self, doc):
        """ Wrapper to parse Video info doc  """
        log("parseVideo()")
        if self.docType == "json":
            return parseVideoJSON(doc)
        else:
            return parseVideoXML(doc)



################################################################################################
def parsePlaylistsXML(doc):
    """ Parse Playlists XML using regex to [ [], [], [] ... ] """
    log("parsePlaylistsXML()")

    data = []
    idList = findAllRegEx(doc, '<id>(\d+)</')
    titleList = findAllRegEx(doc, '<title>(.*?)</')
    descList = findAllRegEx(doc, '<description>(.*?)</')
    countList = findAllRegEx(doc, '<contents_count>(\d+)</')
    updatedList = findAllRegEx(doc, '<updated_at>(\d\d\d\d.\d\d.\d\d)')
    imgList  = findAllRegEx(doc, '<img.*?src="(.*?)"')
    itemCount = len(idList)
    log("ParsePlaylists.itemCount=%d" % itemCount)
    for i in range(itemCount):
        data.append((unescape(titleList[i]), idList[i], unescape(descList[i]), int(countList[i]), updatedList[i], imgList[i]))
    data.sort()
    return data


################################################################################################
def parsePlaylistXML(doc):
    """ Parse Playlist XML to get videos using regex """
    log("parsePlaylistXML()")

    data = []
    videos = findAllRegEx(doc, '(<content>.*?</content>)')
    log("ParsePlaylist.itemCount=%d" % len(videos))
    for video in videos:
        data.append( ( unescape(searchRegEx(video, '<title>(.*?)</')), \
                        searchRegEx(video, '<id>(.*?)<'), \
                        searchRegEx(video, '<captured_at>(\d\d\d\d.\d\d.\d\d)'), \
                        searchRegEx(video, '<link>(.*?)</').strip() + ".xml", \
                        searchRegEx(video, '<img.*?src="(.*?)"'), \
                        searchRegEx(video, '<duration>(.*?)<')) )
    return data

################################################################################################
def parsePlaylistsJSON(doc):
    """ Parse Playlists JSON using eval to [ [], [], [] ... ] """
    log("parsePlaylistsJSON()")

    data = []
    try:
        # evals to [ {}, {}, .. ]
        items = eval( doc.replace('null', '\"\"' ) )
        # convert to [ [], [], .. ] as its easier to unpack without key knowlegde
        for item in items:
            try:
                updated = item.get('updated_at','')[:10]                # yyyy/mm/dd
            except:
                updated = ''
            data.append( (unescape(item.get('title','')), \
                        str(item.get('id','')), \
                        unescape(item.get('description','')), \
                        item.get('contents_count',0), \
                        updated, \
                        item.get('icon_url','')) )
        data.sort()
    except:
        traceback.print_exc()
        data = []
    return data


################################################################################################
def parsePlaylistJSON(doc):
    """ Parse Playlist JSON to get videos using eval """
    log("parsePlaylistJSON()")

    data = []
    try:
        # evals to [ {}, {}, .. ]
        items = eval( doc )['contents']
        # convert to [ [], [], .. ] as its easier to unpack without key knowlegde
        for item in items:
            link = item.get('link','')
            id = link[link.rfind('/')+1:]                            # extract ID off end of link eg /1167
            try:
                captured = item.get('captured','')[:10]                # yyyy/mm/dd
            except:
                captured = ''
            data.append( (
                    unescape(item.get('title','')), \
                    id, \
                    captured, \
                    link + ".json", \
                    item.get('keyframe_url',''),
                    str(item.get('duration','0'))
                    ) )
    except:
        traceback.print_exc()
        data = []
    return data

################################################################################################
def parseVideoXML(doc):
    """ Parse Video ID XML to get media url using regex """
    return searchRegEx(doc, '<media[_-]url>(.*?)</')        # _ or - depending on XML in use

################################################################################################
def parseVideoJSON(doc):
    """ Parse Video ID XML to get media url using regex """

    items = eval( doc.replace('null', '\"\"' ) )
    data = items.get('media_url','')
    return data

################################################################################################
def deleteScriptCache(deleteVideos=True, deleteData=True):
    """ Delete script cache contents according to settings """
    log("deleteScriptCache() deleteVideos=%s deleteData=%s" % (deleteVideos, deleteData))
    try:
        deleteExts = []
        if deleteData:
            deleteExts += ['.xml','.json',]
        if deleteVideos:
            deleteExts += ['.mp4','.ts,','.flv']

        # Delete videos and xml
        allFiles = os.listdir( xbmc.translatePath(DIR_CACHE) )
        for f in allFiles:
            fn, ext = os.path.splitext(f)
            if ext in deleteExts:
                deleteFN = os.path.join( DIR_CACHE, f )
                deleteFile(deleteFN)
    except:
        handleException("deleteScriptCache()")

########################################################################################################################
def showTextFile(filename):
    """ Show the text from a file """
    log( "showTextFile() " + filename)
    try:
        tbd = TextBoxDialogXML("DialogScriptInfo.xml", DIR_HOME)
        tbd.ask( title=filename, fn=filename )
        del tbd
    except:
        handleException()

################################################################################################
################################################################################################
class ReeplayitSettings:
    """ Settings for reeplay.it, allows same file to be shared by script and plugin """

    SETTING_USER = "user"
    SETTING_PWD = "pwd"
    SETTING_CHECK_UPDATE = "check_update"
    SETTING_PAGE_SIZE = "page_size"
    SETTING_VQ = "hq_video"
    SETTING_DELETE_VIDEOS = "delete_videos"
    SETTING_STREAM_VIDEO = "stream_videos"

    def __init__(self):
        self.load()

    def load(self):
        log("ReeplayitSettings.load()")
        self.settings = {}
        self.settings[self.SETTING_USER] = xbmcplugin.getSetting(self.SETTING_USER)
        self.settings[self.SETTING_PWD] = xbmcplugin.getSetting(self.SETTING_PWD)
        self.settings[self.SETTING_CHECK_UPDATE] = (xbmcplugin.getSetting(self.SETTING_CHECK_UPDATE) == 'true')    # bool
        self.settings[self.SETTING_PAGE_SIZE] = int(xbmcplugin.getSetting(self.SETTING_PAGE_SIZE))
        self.settings[self.SETTING_VQ] = (xbmcplugin.getSetting(self.SETTING_VQ) == 'true')    # bool
        self.settings[self.SETTING_STREAM_VIDEO] = (xbmcplugin.getSetting(self.SETTING_STREAM_VIDEO) == 'true')    # bool
        self.settings[self.SETTING_DELETE_VIDEOS] = (xbmcplugin.getSetting(self.SETTING_DELETE_VIDEOS) == 'true')    # bool


    def get(self, key):
        return self.settings.get(key, '')

    def check(self):
        ok = bool( self.settings and self.get(self.SETTING_USER) and self.get(self.SETTING_PWD) )
        log("ReeplayitSettings.check() %s" % ok)
        return ok
