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
Helper classes for implementing desktop components that can monitor and control some functions
of the desktop service. It is used for Indicators, System tray icons and panel applets and
deals with all the hard work of connecting to DBus and monitoring events.
"""

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("gnome15").ugettext

import sys
import pygtk
pygtk.require('2.0')
import gtk
import subprocess
import gconf
import gobject
import shutil
import traceback
import gnome15.g15globals as g15globals
import gnome15.g15screen as g15screen
import gnome15.g15util as g15util
import gnome15.g15notify as g15notify
import dbus
import os.path
import operator
import xdg.DesktopEntry

# Logging
import logging
logger = logging.getLogger()

from threading import RLock
from threading import Thread
                
icon_theme = gtk.icon_theme_get_default()
if g15globals.dev:
    icon_theme.prepend_search_path(g15globals.icons_dir)

# Private     
__browsers = { }
    
"""
Some constants
"""
AUTHORS=["Brett Smith <tanktarta@blueyonder.co.uk>", "Nuno Araujo", "Ciprian Ciubotariu", "Andrea Calabrò" ]
GPL="""
                    GNU GENERAL PUBLIC LICENSE
                       Version 2, June 1991

 Copyright (C) 1989, 1991 Free Software Foundation, Inc.,
 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.

                            Preamble

  The licenses for most software are designed to take away your
freedom to share and change it.  By contrast, the GNU General Public
License is intended to guarantee your freedom to share and change free
software--to make sure the software is free for all its users.  This
General Public License applies to most of the Free Software
Foundation's software and to any other program whose authors commit to
using it.  (Some other Free Software Foundation software is covered by
the GNU Lesser General Public License instead.)  You can apply it to
your programs, too.

  When we speak of free software, we are referring to freedom, not
price.  Our General Public Licenses are designed to make sure that you
have the freedom to distribute copies of free software (and charge for
this service if you wish), that you receive source code or can get it
if you want it, that you can change the software or use pieces of it
in new free programs; and that you know you can do these things.

  To protect your rights, we need to make restrictions that forbid
anyone to deny you these rights or to ask you to surrender the rights.
These restrictions translate to certain responsibilities for you if you
distribute copies of the software, or if you modify it.

  For example, if you distribute copies of such a program, whether
gratis or for a fee, you must give the recipients all the rights that
you have.  You must make sure that they, too, receive or can get the
source code.  And you must show them these terms so they know their
rights.

  We protect your rights with two steps: (1) copyright the software, and
(2) offer you this license which gives you legal permission to copy,
distribute and/or modify the software.

  Also, for each author's protection and ours, we want to make certain
that everyone understands that there is no warranty for this free
software.  If the software is modified by someone else and passed on, we
want its recipients to know that what they have is not the original, so
that any problems introduced by others will not reflect on the original
authors' reputations.

  Finally, any free program is threatened constantly by software
patents.  We wish to avoid the danger that redistributors of a free
program will individually obtain patent licenses, in effect making the
program proprietary.  To prevent this, we have made it clear that any
patent must be licensed for everyone's free use or not licensed at all.

  The precise terms and conditions for copying, distribution and
modification follow.

                    GNU GENERAL PUBLIC LICENSE
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

  0. This License applies to any program or other work which contains
a notice placed by the copyright holder saying it may be distributed
under the terms of this General Public License.  The "Program", below,
refers to any such program or work, and a "work based on the Program"
means either the Program or any derivative work under copyright law:
that is to say, a work containing the Program or a portion of it,
either verbatim or with modifications and/or translated into another
language.  (Hereinafter, translation is included without limitation in
the term "modification".)  Each licensee is addressed as "you".

Activities other than copying, distribution and modification are not
covered by this License; they are outside its scope.  The act of
running the Program is not restricted, and the output from the Program
is covered only if its contents constitute a work based on the
Program (independent of having been made by running the Program).
Whether that is true depends on what the Program does.

  1. You may copy and distribute verbatim copies of the Program's
source code as you receive it, in any medium, provided that you
conspicuously and appropriately publish on each copy an appropriate
copyright notice and disclaimer of warranty; keep intact all the
notices that refer to this License and to the absence of any warranty;
and give any other recipients of the Program a copy of this License
along with the Program.

You may charge a fee for the physical act of transferring a copy, and
you may at your option offer warranty protection in exchange for a fee.

  2. You may modify your copy or copies of the Program or any portion
of it, thus forming a work based on the Program, and copy and
distribute such modifications or work under the terms of Section 1
above, provided that you also meet all of these conditions:

    a) You must cause the modified files to carry prominent notices
    stating that you changed the files and the date of any change.

    b) You must cause any work that you distribute or publish, that in
    whole or in part contains or is derived from the Program or any
    part thereof, to be licensed as a whole at no charge to all third
    parties under the terms of this License.

    c) If the modified program normally reads commands interactively
    when run, you must cause it, when started running for such
    interactive use in the most ordinary way, to print or display an
    announcement including an appropriate copyright notice and a
    notice that there is no warranty (or else, saying that you provide
    a warranty) and that users may redistribute the program under
    these conditions, and telling the user how to view a copy of this
    License.  (Exception: if the Program itself is interactive but
    does not normally print such an announcement, your work based on
    the Program is not required to print an announcement.)

These requirements apply to the modified work as a whole.  If
identifiable sections of that work are not derived from the Program,
and can be reasonably considered independent and separate works in
themselves, then this License, and its terms, do not apply to those
sections when you distribute them as separate works.  But when you
distribute the same sections as part of a whole which is a work based
on the Program, the distribution of the whole must be on the terms of
this License, whose permissions for other licensees extend to the
entire whole, and thus to each and every part regardless of who wrote it.

Thus, it is not the intent of this section to claim rights or contest
your rights to work written entirely by you; rather, the intent is to
exercise the right to control the distribution of derivative or
collective works based on the Program.

In addition, mere aggregation of another work not based on the Program
with the Program (or with a work based on the Program) on a volume of
a storage or distribution medium does not bring the other work under
the scope of this License.

  3. You may copy and distribute the Program (or a work based on it,
under Section 2) in object code or executable form under the terms of
Sections 1 and 2 above provided that you also do one of the following:

    a) Accompany it with the complete corresponding machine-readable
    source code, which must be distributed under the terms of Sections
    1 and 2 above on a medium customarily used for software interchange; or,

    b) Accompany it with a written offer, valid for at least three
    years, to give any third party, for a charge no more than your
    cost of physically performing source distribution, a complete
    machine-readable copy of the corresponding source code, to be
    distributed under the terms of Sections 1 and 2 above on a medium
    customarily used for software interchange; or,

    c) Accompany it with the information you received as to the offer
    to distribute corresponding source code.  (This alternative is
    allowed only for noncommercial distribution and only if you
    received the program in object code or executable form with such
    an offer, in accord with Subsection b above.)

The source code for a work means the preferred form of the work for
making modifications to it.  For an executable work, complete source
code means all the source code for all modules it contains, plus any
associated interface definition files, plus the scripts used to
control compilation and installation of the executable.  However, as a
special exception, the source code distributed need not include
anything that is normally distributed (in either source or binary
form) with the major components (compiler, kernel, and so on) of the
operating system on which the executable runs, unless that component
itself accompanies the executable.

If distribution of executable or object code is made by offering
access to copy from a designated place, then offering equivalent
access to copy the source code from the same place counts as
distribution of the source code, even though third parties are not
compelled to copy the source along with the object code.

  4. You may not copy, modify, sublicense, or distribute the Program
except as expressly provided under this License.  Any attempt
otherwise to copy, modify, sublicense or distribute the Program is
void, and will automatically terminate your rights under this License.
However, parties who have received copies, or rights, from you under
this License will not have their licenses terminated so long as such
parties remain in full compliance.

  5. You are not required to accept this License, since you have not
signed it.  However, nothing else grants you permission to modify or
distribute the Program or its derivative works.  These actions are
prohibited by law if you do not accept this License.  Therefore, by
modifying or distributing the Program (or any work based on the
Program), you indicate your acceptance of this License to do so, and
all its terms and conditions for copying, distributing or modifying
the Program or works based on it.

  6. Each time you redistribute the Program (or any work based on the
Program), the recipient automatically receives a license from the
original licensor to copy, distribute or modify the Program subject to
these terms and conditions.  You may not impose any further
restrictions on the recipients' exercise of the rights granted herein.
You are not responsible for enforcing compliance by third parties to
this License.

  7. If, as a consequence of a court judgment or allegation of patent
infringement or for any other reason (not limited to patent issues),
conditions are imposed on you (whether by court order, agreement or
otherwise) that contradict the conditions of this License, they do not
excuse you from the conditions of this License.  If you cannot
distribute so as to satisfy simultaneously your obligations under this
License and any other pertinent obligations, then as a consequence you
may not distribute the Program at all.  For example, if a patent
license would not permit royalty-free redistribution of the Program by
all those who receive copies directly or indirectly through you, then
the only way you could satisfy both it and this License would be to
refrain entirely from distribution of the Program.

If any portion of this section is held invalid or unenforceable under
any particular circumstance, the balance of the section is intended to
apply and the section as a whole is intended to apply in other
circumstances.

It is not the purpose of this section to induce you to infringe any
patents or other property right claims or to contest validity of any
such claims; this section has the sole purpose of protecting the
integrity of the free software distribution system, which is
implemented by public license practices.  Many people have made
generous contributions to the wide range of software distributed
through that system in reliance on consistent application of that
system; it is up to the author/donor to decide if he or she is willing
to distribute software through any other system and a licensee cannot
impose that choice.

This section is intended to make thoroughly clear what is believed to
be a consequence of the rest of this License.

  8. If the distribution and/or use of the Program is restricted in
certain countries either by patents or by copyrighted interfaces, the
original copyright holder who places the Program under this License
may add an explicit geographical distribution limitation excluding
those countries, so that distribution is permitted only in or among
countries not thus excluded.  In such case, this License incorporates
the limitation as if written in the body of this License.

  9. The Free Software Foundation may publish revised and/or new versions
of the General Public License from time to time.  Such new versions will
be similar in spirit to the present version, but may differ in detail to
address new problems or concerns.

Each version is given a distinguishing version number.  If the Program
specifies a version number of this License which applies to it and "any
later version", you have the option of following the terms and conditions
either of that version or of any later version published by the Free
Software Foundation.  If the Program does not specify a version number of
this License, you may choose any version ever published by the Free Software
Foundation.

  10. If you wish to incorporate parts of the Program into other free
programs whose distribution conditions are different, write to the author
to ask for permission.  For software which is copyrighted by the Free
Software Foundation, write to the Free Software Foundation; we sometimes
make exceptions for this.  Our decision will be guided by the two goals
of preserving the free status of all derivatives of our free software and
of promoting the sharing and reuse of software generally.

                            NO WARRANTY

  11. BECAUSE THE PROGRAM IS LICENSED FREE OF CHARGE, THERE IS NO WARRANTY
FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW.  EXCEPT WHEN
OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES
PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED
OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.  THE ENTIRE RISK AS
TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU.  SHOULD THE
PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING,
REPAIR OR CORRECTION.

  12. IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING
WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MAY MODIFY AND/OR
REDISTRIBUTE THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES,
INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING
OUT OF THE USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED
TO LOSS OF DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY
YOU OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER
PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE
POSSIBILITY OF SUCH DAMAGES.

                     END OF TERMS AND CONDITIONS

            How to Apply These Terms to Your New Programs

  If you develop a new program, and you want it to be of the greatest
possible use to the public, the best way to achieve this is to make it
free software which everyone can redistribute and change under these terms.

  To do so, attach the following notices to the program.  It is safest
to attach them to the start of each source file to most effectively
convey the exclusion of warranty; and each file should have at least
the "copyright" line and a pointer to where the full notice is found.

    <one line to give the program's name and a brief idea of what it does.>
    Copyright (C) <year>  <name of author>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

Also add information on how to contact you by electronic and paper mail.

If the program is interactive, make it output a short notice like this
when it starts in an interactive mode:

    Gnomovision version 69, Copyright (C) year name of author
    Gnomovision comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `show c' for details.

The hypothetical commands `show w' and `show c' should show the appropriate
parts of the General Public License.  Of course, the commands you use may
be called something other than `show w' and `show c'; they could even be
mouse-clicks or menu items--whatever suits your program.

You should also get your employer (if you work as a programmer) or your
school, if any, to sign a "copyright disclaimer" for the program, if
necessary.  Here is a sample; alter the names:

  Yoyodyne, Inc., hereby disclaims all copyright interest in the program
  `Gnomovision' (which makes passes at compilers) written by James Hacker.

  <signature of Ty Coon>, 1 April 1989
  Ty Coon, President of Vice

This General Public License does not permit incorporating your program into
proprietary programs.  If your program is a subroutine library, you may
consider it more useful to permit linking proprietary applications with the
library.  If this is what you want to do, use the GNU Lesser General
Public License instead of this License.
"""
    
def is_desktop_application_installed(application_name):
    """
    Get if a desktop file is installed for a particular application
    
    Keyword arguments:
    service_name    --    name of application
    """
    return os.path.exists("/etc/xdg/autostart/%s.desktop" % application_name) or os.path.exists(os.path.expanduser("~/.local/share/autostart/%s.desktop" % application_name))

def is_autostart_application(application_name):
    """
    Get whether the application is set to autostart
    """
    installed  = is_desktop_application_installed(application_name)
    path = os.path.expanduser("~/.config/autostart/%s.desktop" % application_name)
    if os.path.exists(path):
        desktop_entry = xdg.DesktopEntry.DesktopEntry(path)
        autostart = len(desktop_entry.get('X-GNOME-Autostart-enabled')) == 0 or desktop_entry.get('X-GNOME-Autostart-enabled', type="boolean")
        hidden = desktop_entry.getHidden()
        return autostart and not hidden
    else:
        # There is no config file, so enabled if installed
        return installed

def set_autostart_application(application_name, enabled):
    """
    Set whether an application is set to autostart
    
    Keyword arguments:
    application_name    -- application name
    enabled             -- enabled or not
    """
    path = os.path.expanduser("~/.config/autostart/%s.desktop" % application_name)
    if enabled and os.path.exists(path):
        os.remove(path)
    elif not enabled:
        app_path = "/etc/xdg/autostart/%s.desktop" % application_name
        if not os.path.exists(path):
            shutil.copy(app_path, path)
        desktop_entry = xdg.DesktopEntry.DesktopEntry(path)
        desktop_entry.set("X-GNOME-Autostart-enabled", "false")
        desktop_entry.set("Hidden", "false")
        desktop_entry.write()

def get_desktop():
    '''
    Utility function to get the name of the current desktop environment. The list
    of detectable desktop environments is not complete, but hopefully this will
    improve over time. Currently no attempt is made to determine the version of
    the desktop in use.
    
    Will return :-
    
    gnome          GNOME Desktop
    gnome-shell    GNOME Shell Desktop 
    kde            KDE 
    [None]         No known desktop  
    '''
    
    evars = os.environ
    
    # GNOME Shell (need a better way)
    if ( "DESKTOP_SESSION" in evars and evars["DESKTOP_SESSION"] == "gnome-shell" ) or \
       ( "GJS_DEBUG_OUTPUT" in evars ):
            return "gnome-shell"
    
    # XDG_CURRENT_DESKTOP
    dt = { "LXDE" : "lxde", "GNOME" : "gnome"}
    if "XDG_CURRENT_DESKTOP" in evars:
        val = evars["XDG_CURRENT_DESKTOP"]
        if val in dt:
            return dt[val]
    
    # Environment variables that suggest the use of GNOME
    for i in [ "GNOME_DESKTOP_SESSION_ID", "GNOME_KEYRING_CONTROL" ]:
        if i in evars:
            return "gnome"
    
    # Environment variables that suggest the use of KDE
    for i in [ "KDE_FULL_SESSION", "KDE_SESSION_VERSION", "KDE_SESSION_UID" ]:
        if i in evars:
            return "kde"
    
    # Environment variables that suggest the use of LXDE
    for i in [ "_LXSESSION_PID" ]:
        if i in evars:
            return "lxde"
        
def is_shell_extension_installed(extension):
    """
    Get whether a GNOME Shell extension is installed.
    
    Keyword arguments:
    extension        --    extension name
    """
    
    # 
    # TODO - Bit crap, how can we be sure this is the prefix?
    # 
    prefix = "/usr/share"
    return os.path.exists("%s/gnome-shell/extensions/%s" % (prefix, extension)) or \
        os.path.exists(os.path.expanduser("~/.local/share/gnome-shell/extensions/%s" % extension)) 
        
def is_gnome_shell_extension_enabled(extension):
    """
    Get whether a GNOME Shell extension is enabled. This uses the
    gsettings command. Python GSettings bindings (GObject introspected ones)
    are not used, as well already use PyGTK and the two don't mix
    
    Keyword arguments:
    extension        --    extension name
    """
    status, text = g15util.execute_for_output("gsettings get org.gnome.shell enabled-extensions")
    if status == 0:
        try:
            return extension in eval(text)
        except Exception as e:
            logger.debug("Failed testing if extension is enabled. %s" % e)
            
    return False
        
def set_gnome_shell_extension_enabled(extension, enabled):
    """
    Enable or disable a GNOME Shell extension is enabled. This uses the
    gsettings command. Python GSettings bindings (GObject introspected ones)
    are not used, as well already use PyGTK and the two don't mix
    
    Keyword arguments:
    extension        --    extension name
    enabled          --    enabled
    """
    status, text = g15util.execute_for_output("gsettings get org.gnome.shell enabled-extensions")
    if status == 0:
        try:
            extensions = eval(text)
        except:
            # No extensions available, so init an empty array
            extensions = []
            pass
        contains = extension in extensions
        if contains and not enabled:
            extensions.remove(extension)
        elif not contains and enabled:
            extensions.append(extension)
        s = ""
        for c in extensions:
            if len(s) >0:
                s += ","
            s += "'%s'" % c
        try:
            status, text = g15util.execute_for_output("gsettings set org.gnome.shell enabled-extensions \"[%s]\"" % s)
        except Exception as e:
            logger.debug("Failed to set extension enabled. %s" % e)
            
def browse(url):
    """
    Open the configured browser
    
    Keyword arguments:
    url        -- URL
    """
    b = g15util.get_string_or_default(gconf.client_get_default(), \
                                      "/apps/gnome15/browser", "default")
    if not b in __browsers and not b == "default":
        logger.warning("Could not find browser %s, falling back to default" % b)
        b = "default"
    if not b in __browsers:
        raise Exception("Could not find browser %s" % b)
    __browsers[b].browse(url)

def add_browser(browser):
    """
    Register a new browser. The object must extend G15Browser
    
    Keyword arguments:
    browser        -- browser object.
    """
    if browser.browser_id in __browsers:
        raise Exception("Browser already registered")
    if not isinstance(browser, G15Browser):
        raise Exception("Not a G15Browser instance")
    __browsers[browser.browser_id] = browser
        
class G15Browser():
    def __init__(self, browser_id, name):
        self.name = name
        self.browser_id = browser_id
    
    def browse(self, url):
        raise Exception("Not implemented")

class G15DefaultBrowser(G15Browser):
    def __init__(self):
        G15Browser.__init__(self, "default", _("Default system browser"))
    
    def browse(self, url):
        logger.info("xdg-open '%s'" % url)
        subprocess.Popen(['xdg-open', url])
        
add_browser(G15DefaultBrowser())
    
class G15AbstractService(Thread):
    
    def __init__(self):
        Thread.__init__(self)        
        # Start this thread, which runs the gobject loop. This is 
        # run first, and in a thread, as starting the Gnome15 will send
        # DBUS events (which are sent on the loop). 
        self.loop = gobject.MainLoop()
        self.start()
        
    def start_loop(self):
        logger.info("Starting GLib loop")
        g15util.set_gobject_thread()
        try:
            self.loop.run()
        except:
            traceback.print_stack()
        logger.info("Exited GLib loop")
        
    def start_service(self):
        raise Exception("Not implemented")
        
    def run(self):        
        # Now start the service, which will connect to all devices and
        # start their plugins
        self.start_service()
                
    
class G15Screen():
    """
    Client side representation of a remote screen. Holds general details such
    as model name, UID and the pages that screen is currently showing.
    """
    
    def __init__(self, path, device_model_fullname, device_uid):
        self.path = path
        self.device_model_fullname = device_model_fullname
        self.device_uid = device_uid
        self.items = {}
        self.message = None

class G15DesktopComponent():
    """
    Helper class for implementing desktop components that can monitor and control some functions
    of the desktop service. It is used for Indicators, System tray icons and panel applets and
    deals with all the hard work of connecting to DBus and monitoring events.
    """
    
    def __init__(self):
        self.screens = {}
        self.service = None
        self.start_service_item = None
        self.attention_item = None
        self.pages = []   
        self.lock = RLock()
        self.attention_messages = {}
        self.connected = False
        
        # Connect to DBus and GConf
        self.conf_client = gconf.client_get_default()
        self.session_bus = dbus.SessionBus()
        
        # Initialise desktop component
        self.initialise_desktop_component()     
        self.icons_changed()
        
    def start_service(self):
        """
        Start the desktop component. An attempt will be made to connect to Gnome15 over 
        DBus. If this fails, the component should stay active until the service becomes
        available.
        """
        
        # Try and connect to the service now
        try :
            self._connect()        
        except dbus.exceptions.DBusException:
            if logger.isEnabledFor(logging.DEBUG):
                traceback.print_exc(file=sys.stdout)
            self._disconnect()
        
        # Start watching various events
        self.conf_client.notify_add("/apps/gnome15/indicate_only_on_error", self._indicator_options_changed)
        gtk_icon_theme = gtk.icon_theme_get_default()
        gtk_icon_theme.connect("changed", self._theme_changed)

        # Watch for Gnome15 starting and stopping
        self.session_bus.add_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')  
        
    """
    Pulic functions
    """
    def is_attention(self):
        return len(self.attention_messages) > 0
    
    def get_icon_path(self, icon_name):
        """
        Helper function to get an icon path or it's name, given the name. 
        """
        if g15globals.dev:
            # Because the icons aren't installed in this mode, they must be provided
            # using the full filename. Unfortunately this means scaling may be a bit
            # blurry in the indicator applet
            path = g15util.get_icon_path(icon_name, 128)
            logger.debug("Dev mode icon %s is at %s" % ( icon_name, path ) )
            return path
        else:
            if not isinstance(icon_name, list):
                icon_name = [ icon_name ]
            for i in icon_name:
                p = g15util.get_icon_path(i, -1)
                if p is not None:
                    return i
             
    def show_configuration(self, arg = None):
        """
        Show the configuration user interface
        """        
        g15util.run_script("g15-config")
        
    def stop_desktop_service(self, arg = None):
        """
        Stop the desktop service
        """ 
        self.session_bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Service').Stop()   
        
    def start_desktop_service(self, arg = None):
        """
        Start the desktop service
        """    
        g15util.run_script("g15-desktop-service", ["-f"])   
        
    def show_page(self, path):
        """
        Show a page, given its path
        """
        self.session_bus.get_object('org.gnome15.Gnome15', path).CycleTo()
        
    def check_attention(self):
        """
        Check the current state of attention, either clearing it or setting it and displaying
        a new message
        """
        if len(self.attention_messages) == 0:
            self.clear_attention()      
        else:
            for i in self.attention_messages:
                message = self.attention_messages[i]
                self.attention(message)
                break
        
    """
    Functions that must be implemented
    """
        
    def initialise_desktop_component(self):
        """
        This function is called during construction and should create initial desktop component
        """ 
        raise Exception("Not implemented")
    
    def rebuild_desktop_component(self):
        """
        This function is called every time the list of screens or pages changes 
        in someway. The desktop component should be rebuilt to reflect the
        new state
        """
        raise Exception("Not implemented")
    
    def clear_attention(self):
        """
        Clear any "Attention" state indicators
        """
        raise Exception("Not implemented")
        
    def attention(self, message = None):
        """
        Display an "Attention" state indicator with a message
        
        Keyword Arguments:
        message    --    message to display
        """
        raise Exception("Not implemented")
    
    def icons_changed(self):
        """
        Invoked once a start up, and then whenever the desktop icon theme changes. Implementations
        should do whatever required to change any themed icons they are displayed
        """
        raise Exception("Not implemented")
    
    def options_changed(self):
        """
        Invoked when any global desktop component options change.
        """
        raise Exception("Not implemented")
        
    '''
    DBUS Event Callbacks
    ''' 
    def _name_owner_changed(self, name, old_owner, new_owner):
        if name == "org.gnome15.Gnome15":
            if old_owner == "":
                if self.service == None:
                    self._connect()
            else:
                if self.service != None:
                    self.connected = False
                    self._disconnect()
        
    def _page_created(self, page_path, page_title, path = None):
        screen_path = path
        logger.debug("Page created (%s) %s = %s" % ( screen_path, page_path, page_title ) )
        page = self.session_bus.get_object('org.gnome15.Gnome15', page_path )
        self.lock.acquire()
        try :
            if page.GetPriority() >= g15screen.PRI_LOW:
                self._add_page(screen_path, page_path, page)
        finally :
            self.lock.release()
        
    def _page_title_changed(self, page_path, title, path = None):
        screen_path = path
        self.lock.acquire()
        try :
            self.screens[screen_path].items[page_path] = title
            self.rebuild_desktop_component()
        finally :
            self.lock.release()
    
    def _page_deleting(self, page_path, path = None):
        screen_path = path
        self.lock.acquire()
        logger.debug("Destroying page (%s) %s" % ( screen_path, page_path ) )
        try :
            items = self.screens[screen_path].items
            if page_path in items:
                del items[page_path]
                self.rebuild_desktop_component()
        finally :
            self.lock.release()
        
    def _attention_cleared(self, path = None):
        screen_path = path
        if screen_path in self.attention_messages:
            del self.attention_messages[screen_path]
            self.rebuild_desktop_component()
        
    def _attention_requested(self, message = None, path = None):
        screen_path = path
        if not screen_path in self.attention_messages:
            self.attention_messages[screen_path] = message
            self.rebuild_desktop_component()
        
    """
    Private
    """
            
    def _enable(self, widget, device):
        device.Enable()
        
    def _disable(self, widget, device):
        device.Disable()
        
    def _cycle_screens_option_changed(self, client, connection_id, entry, args):
        self.rebuild_desktop_component()
        
    def _remove_screen(self, screen_path):
        print "*** removing %s from %s" % ( str(screen_path), str(self.screens))
        if screen_path in self.screens:
            try :
                del self.screens[screen_path]
            except dbus.DBusException:
                pass
        self.rebuild_desktop_component()
        
    def _add_screen(self, screen_path):
        logger.debug("Screen added %s" % screen_path)
        remote_screen = self.session_bus.get_object('org.gnome15.Gnome15', screen_path)
        ( device_uid, device_model_name, device_usb_id, device_model_fullname ) = remote_screen.GetDeviceInformation()
        screen = G15Screen(screen_path, device_model_fullname, device_uid)        
        self.screens[screen_path] = screen
        if remote_screen.IsAttentionRequested():
            screen.message = remote_screen.GetMessage()
        
    def _device_added(self, screen_path):
        self.rebuild_desktop_component()
        
    def _device_removed(self, screen_path):
        self.rebuild_desktop_component()                                
        
    def _connect(self):
        logger.debug("Connecting")
        self._reset_attention()
        self.service = self.session_bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Service')
        self.connected = True
        logger.debug("Connected")
                
        # Load the initial screens
        self.lock.acquire()
        try : 
            for screen_path in self.service.GetScreens():
                logger.debug("Adding %s" % screen_path)
                self._add_screen(screen_path)
                remote_screen = self.session_bus.get_object('org.gnome15.Gnome15', screen_path)
                for page_path in remote_screen.GetPagesBelowPriority(g15screen.PRI_LOW):
                    page = self.session_bus.get_object('org.gnome15.Gnome15', page_path)
                    if page.GetPriority() >= g15screen.PRI_LOW and page.GetPriority() < g15screen.PRI_HIGH:
                        self._add_page(screen_path, page_path, page)
        finally :
            self.lock.release()
        
        # Listen for events
        self.session_bus.add_signal_receiver(self._device_added, dbus_interface = "org.gnome15.Service", signal_name = "DeviceAdded")
        self.session_bus.add_signal_receiver(self._device_removed, dbus_interface = "org.gnome15.Service", signal_name = "DeviceRemoved")
        self.session_bus.add_signal_receiver(self._add_screen, dbus_interface = "org.gnome15.Service", signal_name = "ScreenAdded")
        self.session_bus.add_signal_receiver(self._remove_screen, dbus_interface = "org.gnome15.Service", signal_name = "ScreenRemoved")
        self.session_bus.add_signal_receiver(self._page_created, dbus_interface = "org.gnome15.Screen", signal_name = "PageCreated",  path_keyword = 'path')
        self.session_bus.add_signal_receiver(self._page_title_changed, dbus_interface = "org.gnome15.Screen", signal_name = "PageTitleChanged",  path_keyword = 'path')
        self.session_bus.add_signal_receiver(self._page_deleting, dbus_interface = "org.gnome15.Screen", signal_name = "PageDeleting",  path_keyword = 'path')
        self.session_bus.add_signal_receiver(self._attention_requested, dbus_interface = "org.gnome15.Screen", signal_name = "AttentionRequested",  path_keyword = 'path')
        self.session_bus.add_signal_receiver(self._attention_cleared, dbus_interface = "org.gnome15.Screen", signal_name = "AttentionCleared",  path_keyword = 'path')
            
        # We are now connected, so remove the start service menu item and allow cycling
        self.rebuild_desktop_component()
        
    def _disconnect(self):
        logger.debug("Disconnecting")                  
        self.session_bus.remove_signal_receiver(self._device_added, dbus_interface = "org.gnome15.Service", signal_name = "DeviceAdded")
        self.session_bus.remove_signal_receiver(self._device_removed, dbus_interface = "org.gnome15.Service", signal_name = "DeviceRemoved")
        self.session_bus.remove_signal_receiver(self._add_screen, dbus_interface = "org.gnome15.Service", signal_name = "ScreenAdded")
        self.session_bus.remove_signal_receiver(self._remove_screen, dbus_interface = "org.gnome15.Service", signal_name = "ScreenRemoved")
        self.session_bus.remove_signal_receiver(self._page_created, dbus_interface = "org.gnome15.Screen", signal_name = "PageCreated")
        self.session_bus.remove_signal_receiver(self._page_title_changed, dbus_interface = "org.gnome15.Screen", signal_name = "PageTitleChanged")
        self.session_bus.remove_signal_receiver(self._page_deleting, dbus_interface = "org.gnome15.Screen", signal_name = "PageDeleting")
        self.session_bus.remove_signal_receiver(self._attention_requested, dbus_interface = "org.gnome15.Screen", signal_name = "AttentionRequested")
        self.session_bus.remove_signal_receiver(self._attention_cleared, dbus_interface = "org.gnome15.Screen", signal_name = "AttentionCleared")
             
        if self.service != None and self.connected:
            for screen_path in dict(self.screens):
                self._remove_screen(screen_path)
        
        self._reset_attention()
        self._attention_requested("service", "g15-desktop-service is not running.")
            
        self.service = None  
        self.connected = False 
        self.rebuild_desktop_component()      
        
    def _reset_attention(self):
        self.attention_messages = {}
        self.rebuild_desktop_component()
            
    def _add_page(self, screen_path, page_path, page):
        logger.debug("Adding page %s to %s" % (page_path, screen_path))
        items = self.screens[screen_path].items
        if not page_path in items:
            items[page_path] = page.GetTitle()
            self.rebuild_desktop_component()
        
    def _indicator_options_changed(self, client, connection_id, entry, args):
        self.options_changed()
    
    def _theme_changed(self, theme):
        self.icons_changed()
        
        
class G15GtkMenuPanelComponent(G15DesktopComponent):
    
    def __init__(self):
        self.screen_number = 0
        self.devices = []
        self.notify_message = None
        G15DesktopComponent.__init__(self)
        
    def about_info(self, widget):     
        about = gtk.AboutDialog()
        about.set_name("Gnome15")
        about.set_version(g15globals.version)
        about.set_license(GPL)
        about.set_authors(AUTHORS)
        about.set_documenters(["Brett Smith <tanktarta@blueyonder.co.uk>"])
        about.set_logo(gtk.gdk.pixbuf_new_from_file(g15util.get_app_icon(self.conf_client, "gnome15", 128)))
        about.set_comments(_("Desktop integration for Logitech 'G' keyboards."))
        about.run()
        about.hide()
        
    def scroll_event(self, widget, event):
        
        direction = event.direction
        if direction == gtk.gdk.SCROLL_UP:
            screen = self._get_active_screen_object()
            self._close_notify_message()
            screen.ClearPopup() 
            screen.Cycle(1)
        elif direction == gtk.gdk.SCROLL_DOWN:
            screen = self._get_active_screen_object()
            self._close_notify_message()
            screen.ClearPopup() 
            screen.Cycle(-1)
        else:
            """
            If there is only one device, right scroll cycles the backlight color,
            otherwise toggle between the devices (used to select what to scroll with up
            and down) 
            """
            if direction == gtk.gdk.SCROLL_LEFT:
                self._get_active_screen_object().CycleKeyboard(-1)
            elif direction == gtk.gdk.SCROLL_RIGHT:
                if len(self.screens) > 1:
                    if self.screen_number >= len(self.screens) - 1:
                        self.screen_number = 0
                    else:
                        self.screen_number += 1
                        
                    self._set_active_screen_number()
                else:
                    self._get_active_screen_object().CycleKeyboard(1)
            
    def rebuild_desktop_component(self):
        logger.debug("Removing old menu items")
        for item in self.last_items:
            item.get_parent().remove(item)
            item.destroy()
            
        self.last_items = []
        i = 0
        
        # Remove the notify handles used for the previous cycle components
        logger.debug("Removing old notify handles")
        for h in self.notify_handles:
            self.conf_client.notify_remove(h)
        self.notify_handles = []
        
        logger.debug("Building new menu")
        if self.service and self.connected:
            
            item = gtk.MenuItem(_("Stop Desktop Service"))
            item.connect("activate", self.stop_desktop_service)
            self.add_service_item(item)
            self.add_service_item(gtk.MenuItem())
        
            try:
                devices = self.service.GetDevices()
                for device_path in devices:
                    remote_device = self.session_bus.get_object('org.gnome15.Gnome15', device_path)
                    screen_path = remote_device.GetScreen()
                    
                    screen = self.screens[screen_path] if len(screen_path) > 0 and screen_path in self.screens else None
                    
                    if screen:
                        if i > 0:
                            logger.debug("Adding separator")
                            self._append_item(gtk.MenuItem())
                        # Disable
                        if len(devices) > 1:
                            item = gtk.MenuItem("Disable %s"  % screen.device_model_fullname)
                            item.connect("activate", self._disable, remote_device)
                            self.add_service_item(item)
                        
                        # Cycle screens
                        item = gtk.CheckMenuItem(_("Cycle screens automatically"))
                        item.set_active(g15util.get_bool_or_default(self.conf_client, "/apps/gnome15/%s/cycle_screens" % screen.device_uid, True))
                        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/%s/cycle_screens" % screen.device_uid, self._cycle_screens_option_changed))
                        item.connect("toggled", self._cycle_screens_changed, screen.device_uid)
                        self._append_item(item)
                        
                        # Alert message            
                        if screen.message:
                            self._append_item(gtk.MenuItem(screen.message))
                        
                        logger.debug("Adding items")
                        
                        
                        sorted_x = sorted(screen.items.iteritems(), key=operator.itemgetter(1))
                        for item_key, text in sorted_x:
                            logger.debug("Adding item %s = %s " % (item_key, text ) )
                            item = gtk.MenuItem(text)
                            item.connect("activate", self._show_page, item_key)
                            self._append_item(item)
                    else:
                        # Enable
                        if len(devices) > 1:
                            item = gtk.MenuItem(_("Enable %s") % remote_device.GetModelFullName())
                            item.connect("activate", self._enable, remote_device)
                            self.add_service_item(item)
                    i += 1
            except Exception as e:
                logger.debug("Failed to find devices, service probably stopped. %s", str(e))
                self.connected = False
                self.rebuild_desktop_component()
                
            self.devices = devices
        else:
            self.devices = []
            self.add_start_desktop_service()

        self.menu.show_all()
        self.check_attention()
        
    def add_start_desktop_service(self):
        item = gtk.MenuItem(_("Start Desktop Service"))
        item.connect("activate", self.start_desktop_service)
        self.add_service_item(item)
        
    def add_service_item(self, item):
        self._append_item(item)
        
    def initialise_desktop_component(self):
        
        self.last_items = []
        self.start_service_item = None
        self.attention_item = None
        self.notify_handles = []
        
        # Indicator menu
        self.menu = gtk.Menu()
        self.create_component()
        self.menu.show_all()
        
    def create_component(self):
        raise Exception("Not implemented")
        
    def remove_attention_menu_item(self):              
        if self.attention_item != None:
            self.menu.remove(self.attention_item)
            self.attention_item.destroy()
            self.menu.show_all()
            self.attention_item = None
        
    def options_changed(self):
        self.check_attention()
        
    """
    Private
    """
        
    def _get_active_screen_object(self):        
        screen = list(self.screens.values())[self.screen_number]
        return self.session_bus.get_object('org.gnome15.Gnome15', screen.path)
                
    def _set_active_screen_number(self):
        self._close_notify_message()
        screen = list(self.screens.values())[self.screen_number]
        body = _("%s is now the active keyboard. Use mouse wheel up and down to cycle screens on this device") % screen.device_model_fullname
        self.notify_message = g15notify.notify(screen.device_model_fullname, body, "preferences-desktop-keyboard-shortcuts")
        
    def _close_notify_message(self):
        if self.notify_message is not None:
            try:
                self.notify_message.close()
            except Exception as e:
                logger.debug("Failed to close message. %s" % str(e))
            self.notify_message = None
       
    def _append_item(self, item, menu = None):
        self.last_items.append(item)
        if menu is None:
            menu = self.menu
        menu.append(item)
        
    def _show_page(self,event, page_path):
        self.show_page(page_path)            
        
    def _cycle_screens_changed(self, widget, device_uid):
        self.conf_client.set_bool("/apps/gnome15/%s/cycle_screens" % device_uid, widget.get_active())
        
if __name__ == "__main__":
    print "g15-systemtray installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-systemtray"), is_autostart_application("g15-systemtray") )
    print "g15-desktop-service installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-desktop-service"), is_autostart_application("g15-desktop-service") )
    print "g15-indicator installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-indicator"), is_autostart_application("g15-indicator") )
    print "dropbox installed = %s, enabled = %s" % ( is_desktop_application_installed("dropbox"), is_autostart_application("dropbox") )
    print "xdropbox installed = %s, enabled = %s" % ( is_desktop_application_installed("xdropbox"), is_autostart_application("xdropbox") )
    print "nepomukserver installed = %s, enabled = %s" % ( is_desktop_application_installed("nepomukserver"), is_autostart_application("nepomukserver") )
    set_autostart_application("g15-indicator", False)
    print "g15-indicator installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-indicator"), is_autostart_application("g15-indicator") )
    set_autostart_application("g15-indicator", True)
    print "g15-indicator installed = %s, enabled = %s" % ( is_desktop_application_installed("g15-indicator"), is_autostart_application("g15-indicator") )
