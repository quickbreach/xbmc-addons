"""
        Plugin for streaming media from CBS.com
"""
#main imports
import sys
import os
import urllib,urllib2
import re
import xbmc
import xbmcgui
import xbmcplugin

import resources.lib.common as common

#plugin constants
__plugin__ = "CBS"
__authors__ = "BlueCop"
__credits__ = "hulu and fancast plugins"
__version__ = "1.12"


print "\n\n\n\n\n\n\nstart of CBS plugin\n\n\n\n\n\n"
try:print "CBS--> common.args.mode -- > " + common.args.mode
except: print "CBS--> no mode has been defined"


def modes( ):
        if sys.argv[2]=='':
            import resources.lib._home as home
            home.Main()
        elif common.args.mode.startswith('Play'):
            import resources.lib.episodeplayer as episodeplayer
            episodeplayer.Main()
        elif common.args.mode.startswith('Shows'):
            import resources.lib._shows as shows
            shows.Main()
        elif common.args.mode.startswith('All'):
            import resources.lib._videolist as videolist
            videolist.Main()
        elif common.args.mode.startswith('Latest'):
            import resources.lib._videolist as videolist
            videolist.Main()
        elif common.args.mode.startswith('Popular'):
            import resources.lib._videolist as videolist
            videolist.Main()
        elif common.args.mode.startswith('Editorial'):
            import resources.lib._videolist as videolist
            videolist.Main()                         
        elif common.args.mode.startswith('Clips'):
            import resources.lib._videolist as videolist
            videolist.Main()
        elif common.args.mode.startswith('List'):
            import resources.lib._videolist as videolist
            videolist.Main()
        elif common.args.mode.startswith('Seasons'):
            import resources.lib._videolist as videolist
            videolist.Main()
        elif common.args.mode.startswith('HD'):
            #import resources.lib._hd as videolist
            #videolist.Main()
            import resources.lib._hd as hd
            hd.Main()
        else:
            import xbmcgui
            xbmcgui.Dialog().ok('common.args.mode',common.args.mode)
            print "unknown mode--> "+common.args.mode

modes ( )   
sys.modules.clear()
