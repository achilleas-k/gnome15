# coding: utf-8
 
#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2011 Brett Smith <tanktarta@blueyonder.co.uk>
#  Copyright (C) 2013 Brett Smith <tanktarta@blueyonder.co.uk>
#                     Nuno Araujo <nuno.araujo@russo79.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Helpers for internationalisation. See http://wiki.maemo.org/How_to_Internationalize_python_apps.
Gnome15 has multiple translation domains that are loaded dynamically and then cached
in memory.

Translations may be required for Python code, SVG or Glade files. 
"""

import os
import locale
import gettext
import g15globals
import util.g15gconf as g15gconf
import time
import datetime
import re

import logging
logger = logging.getLogger(__name__)
 
# Change this variable to your app name!
#  The translation files will be under
#  @LOCALE_DIR@/@LANGUAGE@/LC_MESSAGES/@APP_NAME@.mo
APP_NAME = "SleepAnalyser"
 
LOCALE_DIR = g15globals.i18n_dir
 
# Now we need to choose the language. We will provide a list, and gettext
# will use the first translation available in the list
#
#  In maemo it is in the LANG environment variable
#  (on desktop is usually LANGUAGES)
DEFAULT_LANGUAGES = []
if 'LANG' in os.environ:
    DEFAULT_LANGUAGES += os.environ.get('LANG', '').split(':')
if 'LANGUAGE' in os.environ:
    DEFAULT_LANGUAGES += os.environ.get('LANGUAGE', '').split('.')
DEFAULT_LANGUAGES += ['en_GB']
 
lc, encoding = locale.getdefaultlocale()
if lc:
    languages = [lc]
else:
    languages = []
 
# Concat all languages (env + default locale),
#  and here we have the languages and location of the translations
languages += DEFAULT_LANGUAGES
mo_location = LOCALE_DIR

# Cached translations
__translations = {}

# Replace these date/time formats to get a format without seconds
REPLACE_FORMATS = [
        (u'.%S', u''),
        (u':%S', u''),
        (u',%S', u''),
        (u' %S', u''),
        (u':%OS', ''),
        (u'%r', '%I:%M %p'),
        (u'%t', '%H:%M'),
        (u'%T', '%H:%M')
    ]

def format_time(time_val, gconf_client, display_seconds = True, show_timezone = False, compact = True):
    """
    Format a given time / datetime as a time in the 12hour format. GConf
    is checked for custom format, otherwise the default for the locale is
    used.
    
    Keyword arguments:
    time_val         --    time / datetime object
    gconf_client     --    gconf client instance
    display_seconds  --    if false, seconds will be stripped from result
    """
    fmt = g15gconf.get_string_or_default(gconf_client,
                                        "/apps/gnome15/time_format", 
                                        locale.nl_langinfo(locale.T_FMT_AMPM))
    # For some locales T_FMT_AMPM is empty.
    # Set the format to a default value if this is the case.
    if fmt == "":
        fmt = "%r"

    if not display_seconds:
        fmt = __strip_seconds(fmt)
    if isinstance(time_val, time.struct_time):
        time_val = datetime.datetime(*time_val[:6])
    
    if not show_timezone:
        fmt = fmt.replace("%Z", "")
    
    if compact:
        fmt = fmt.replace(" %p", "%p")
        fmt = fmt.replace(" %P", "%P")
        
    fmt = fmt.strip()

    if isinstance(time_val, tuple):
        return time.strftime(fmt, time_val)
    else:
        return time_val.strftime(fmt)

def format_time_24hour(time_val, gconf_client, display_seconds = True, show_timezone = False):
    """
    Format a given time / datetime as a time in the 24hour format. GConf
    is checked for custom format, otherwise the default for the locale is
    used.
    
    Keyword arguments:
    time_val         --    time / datetime object / tuple
    gconf_client     --    gconf client instance
    display_seconds  --    if false, seconds will be stripped from result
    """    
    fmt = g15gconf.get_string_or_default(gconf_client, "/apps/gnome15/time_format_24hr", locale.nl_langinfo(locale.T_FMT))
    if not display_seconds:
        fmt = __strip_seconds(fmt)
    if isinstance(time_val, time.struct_time):
        time_val = datetime.datetime(*time_val[:6])
        
    if not show_timezone:
        fmt = fmt.replace("%Z", "")
    fmt = fmt.strip()
    
    if isinstance(time_val, tuple):
        return time.strftime(fmt, time_val)
    else:
        return time_val.strftime(fmt)

def format_date(date_val, gconf_client):
    """
    Format a datetime as a date (without time). GConf
    is checked for custom format, otherwise the default for the locale is
    used.
    
    Keyword arguments:
    date_val         --    date / datetime object
    gconf_client     --    gconf client instance
    """    
    fmt = g15gconf.get_string_or_default(gconf_client, "/apps/gnome15/date_format", locale.nl_langinfo(locale.D_FMT))
    if isinstance(date_val, tuple):
        return datetime.date.strftime(fmt, date_val)
    else:
        return date_val.strftime(fmt)

def format_date_time(date_val, gconf_client, display_seconds = True):
    """
    Format a datetime as a date and a time. GConf
    is checked for custom format, otherwise the default for the locale is
    used.
    
    Keyword arguments:
    date_val         --    date / datetime object
    gconf_client     --    gconf client instance
    display_seconds  --    if false, seconds will be stripped from result
    """    
    fmt = g15gconf.get_string_or_default(gconf_client, "/apps/gnome15/date_time_format", locale.nl_langinfo(locale.D_T_FMT))
    if not display_seconds:
        fmt = __strip_seconds(fmt)
    if isinstance(date_val, tuple):
        return datetime.datetime.strftime(fmt, date_val)
    else:
        return date_val.strftime(fmt)
 
def get_translation(domain, modfile=None):
    """
    Initialize a translation domain. Unless modfile is supplied,
    the translation will be searched for in the default location. If it
    is supplied, it's parent directory will be pre-pended to i18n to get
    the location to use.
    
    Translation objects are cached.
    
    Keyword arguments:
    domain        --    translation domain
    modfile       --    module file location (search relative to this file + /i18n)
    """
    if domain in __translations:
        return __translations[domain]
    gettext.install (True, localedir=None, unicode=1)
    translation_location = mo_location
    if modfile is not None:
        translation_location = "%s/i18n" % os.path.dirname(modfile)
    gettext.find(domain, translation_location)
    locale.bindtextdomain(domain, translation_location)
    gettext.bindtextdomain(domain, translation_location)
    gettext.textdomain (domain)
    gettext.bind_textdomain_codeset(domain, "UTF-8")
    language = gettext.translation (domain, translation_location, languages=languages, fallback=True)
    __translations[domain] = language
    return language

def parse_US_time(time_val):
    """
    Parses a time in the US format (%I:%M %p)
    This method assumes that the time_val value is valid.
    It's behaviour is similar to a call to time.strptime
    """
    parsed = re.match('(0?[1-9]|1[0-2]):([0-5][0-9]) (AM|am|PM|pm)', time_val)
    hour, minute, ampm = parsed.group(1, 2, 3)
    hour = int(hour)
    minute = int(minute)
    if ampm.lower() == 'pm':
        hour = hour + 12
    return time.struct_time((1900, 1, 1, hour, minute, 0, 0, 1, -1))

def parse_US_time_or_none(time_val):
    try:
        return parse_US_time(time_val)
    except Exception as e:
        logger.debug("Invalid format for US time.", exc_info = e)
        return None

"""
Private
"""

def __strip_seconds(fmt):
    for f in REPLACE_FORMATS:
        fmt = fmt.replace(*f)
    return fmt