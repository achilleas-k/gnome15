# coding: utf-8
 
#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) Brett Smith <tanktarta@blueyonder.co.uk>                      |
#        |                                                                             |
#        | This program is free software; you can redistribute it and/or               |
#        | modify it under the terms of the GNU General Public License                 |
#        | as published by the Free Software Foundation; either version 2              |
#        | of the License, or (at your option) any later version.                      |
#        |                                                                             |
#        | This program is distributed in the hope that it will be useful,             |
#        | but WITHOUT ANY WARRANTY; without even the implied warranty of              |
#        | MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               |
#        | GNU General Public License for more details.                                |
#        |                                                                             |
#        | You should have received a copy of the GNU General Public License           |
#        | along with this program; if not, write to the Free Software                 |
#        | Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA. |
#        +-----------------------------------------------------------------------------+

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
    language = []
 
# Concat all languages (env + default locale),
#  and here we have the languages and location of the translations
languages += DEFAULT_LANGUAGES
mo_location = LOCALE_DIR

# Cached translations
__translations = {}
 
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
