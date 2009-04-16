"""
    SVN Repo Installer Log Viewer
"""

import os
import sys
try:
    import xbmcgui
    import xbmc
    DEBUG = False
except:
    DEBUG = True
    
import urllib
import re
from xml.sax.saxutils import unescape


class _Info:
    def __init__( self, *args, **kwargs ):
        self.__dict__.update( kwargs )


class ChangelogParser:
    # TODO: make these settings
    BASE_URL = "http://code.google.com/p/%s/updates/list?start=%d"
    PAGES = 3

    def __init__( self, repo, category=None, revision=None, parse=True ):
        self.log = "[B]%s: %s[/B]\n----\n" % ( category or repo, xbmc.getLocalizedString( 30017 ) )
        self.repo = repo
        self.category = category
        self.revision = revision
        self.parse = parse

    def fetch_changelog( self ):
        try:
            if ( DEBUG ):
                base_path = os.getcwd()
            else:
                base_path = os.path.join( xbmc.translatePath( "special://profile/" ), "plugin_data", "programs", os.path.basename( os.getcwd() ) )
            # make path
            if ( not os.path.isdir( base_path ) ):
                os.path.makedirs( base_path )
            for page in range( self.PAGES ):
                path = os.path.join( base_path, "%s%d.txt" % ( self.repo, page, ) )
                # open socket
                if ( ( DEBUG or self.parse == True ) and os.path.isfile( path ) and self.revision is None):
                    usock = open( path, "r" )
                else:
                    usock = urllib.urlopen( self.BASE_URL % ( self.repo, page * 50, ) )
                #read html source
                htmlSource = usock.read()
                # close socket
                usock.close()
                # save source for debugging
                if ( self.parse == False or not os.path.isfile( path ) ):
                    file_object = open( path, "w" )
                    file_object.write( htmlSource )
                    file_object.close()
                # parse source
                if ( self.parse ):
                    self._parse_html_source( htmlSource )
        except Exception, e:
            print str( e )

    def _parse_html_source( self, htmlSource ):
        # regex's
        regex_items = re.compile( '<li>(.+?)</li>', re.DOTALL )
        regex_revisions = re.compile( '<a class="ot-revision-link" href="/p/[^/]+/source/detail\?r=[0-9]+">([^<]+)</a>' )
        regex_dates = re.compile( '<span class="date below-more" title="([^"]+)"' )
        regex_authors = re.compile( '<a class="ot-profile-link-2" href="/u/[^/]+/">([^<]+)</a></span>' )
        regex_details = re.compile( '<div class=\"details\"><span class=\"ot-logmessage\">(.+?)</span></div>', re.DOTALL )
        if ( self.category is not None ):
            regex_subst = re.compile( "\[%s\]" % self.category, re.IGNORECASE )
        # scrape info
        items = regex_items.findall( htmlSource )
        # enumerate thru and scrape and combine all info
        for item in items:
            try:
                # scrape info
                revision = regex_revisions.findall( item )[ 0 ]
                date = regex_dates.findall( item )[ 0 ]
                author = regex_authors.findall( item )[ 0 ]
                detail = regex_details.findall( item )[ 0 ]
                # add to log
                if ( self.category is not None and re.findall( "[.*%s.*]" % self.category.lower(), detail, re.IGNORECASE ) ):
                    if ( self.revision is not None and int( revision[ 1 : ] ) <= self.revision ):
                        self.log += "[I]%s - %s - %s[/I]\n%s\n----\n" % ( revision, date, author, unescape( re.sub( regex_subst, "", detail ).strip(), { "&#39;": "'", "&quot;": '"' } ), )
                    elif ( self.revision is None ):
                        self.log += "[I]%s - %s - %s[/I]\n%s\n----\n" % ( revision, date, author, unescape( re.sub( regex_subst, "", detail ).strip(), { "&#39;": "'", "&quot;": '"' } ), )
                elif ( self.category is None ):
                    pos = ( detail.find( "]" ) )
                    if ( pos >= 0 ):
                        msg = unescape( "%s [I]%s - %s - %s[/I]\n%s\n----\n" % ( detail[ : pos + 1 ].strip(), revision, date, author, detail[ pos + 1 : ].strip() ), { "&#39;": "'", "&quot;": '"' } )
                    else:
                        msg = unescape( "[I]%s - %s - %s[/I]\n%s\n----\n" % ( revision, date, author, detail.strip(), ), { "&#39;": "'", "&quot;": '"' } )
                    self.log += msg
            except:
                # not a valid log message
                pass

if ( not DEBUG ):
    class GUI( xbmcgui.WindowXMLDialog ):
        # action codes
        ACTION_EXIT_SCRIPT = ( 9, 10, )

        def __init__( self, *args, **kwargs ):
            xbmcgui.WindowXMLDialog.__init__( self )
            self.dialog = xbmcgui.DialogProgress()
            self.dialog.create( sys.modules[ "__main__" ].__plugin__, "Fetching changelog..." )
            self._parse_argv()

        def onInit( self ):
            if ( self.args.repo is None ):
                log = self._fetch_readme()
            else:
                log = self._fetch_changelog()
            self._paste_log( log )
            self.dialog.close()

        def _parse_argv( self ):
            # call _Info() with our formatted argv to create the self.args object
            exec "self.args = _Info(%s)" % ( urllib.unquote_plus( sys.argv[ 2 ][ 1 : ].replace( "&", ", " ) ), )

        def _fetch_changelog( self ):
            if ( self.args.revision == True ):
                self.args.revision = int( re.findall( "\$Revision: ([0-9]+) \$", sys.modules[ "__main__" ].__svn_revision__ )[ 0 ] )

            parser = ChangelogParser( self.args.repo, self.args.category, self.args.revision, self.args.parse )
            parser.fetch_changelog()
            return parser.log

        def _fetch_readme( self ):
            path = os.path.join( os.getcwd(), "resources", "readme.txt" )
            # open socket
            usock = open( path, "r" )
            #read html source
            readme = usock.read()
            # close socket
            usock.close()
            # set category
            self.args.category = "readme.txt"
            # return text
            return readme

        def _paste_log( self, log ):
            try:
                title = ( self.args.category or self.args.repo )
                self.getControl( 5 ).setText( log )
                self.getControl( 3 ).setText( title )
            except:
                pass

        def onClick( self, controlId ):
            pass

        def onFocus( self, controlId ):
            pass

        def onAction( self, action ):
            if ( action in self.ACTION_EXIT_SCRIPT ):
                self.close()

def Main():
    ui = GUI( "DialogScriptInfo.xml", os.getcwd(), "Default" )
    ui.doModal()
    del ui

if ( __name__ == "__main__" ):
    if ( not DEBUG ):
        Main()
    else:
        parser = ChangelogParser( "xbmc-addons", "YouTube" )
        parser.fetch_changelog()
        print parser.log

