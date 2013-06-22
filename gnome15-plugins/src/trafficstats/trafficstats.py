#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) 2013 NoXPhasma <noxphasma@live.de>                            |
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

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("trafficstats", modfile = __file__).ugettext

import gnome15.g15screen as g15screen
import gnome15.g15theme as g15theme
import gnome15.util.g15uigconf as g15uigconf
import gnome15.util.g15gconf as g15gconf
import gnome15.util.g15os as g15os
import gnome15.g15actions as g15actions
import gnome15.g15devices as g15devices
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15text as g15text
import gnome15.g15plugin as g15plugin
import time
import datetime
try:
    import gtop
except:
    # API compatible work around for Ubuntu 12.10
    import gnome15.g15top as gtop
import os
import gtk
import locale

# Plugin details - All of these must be provided
id="trafficstats"
name=_("Traffic Stats")
description=_("Displays network traffic stats. Either of actual session or from vnstat.")
author="NoXPhasma <noxphasma@live.de>"
copyright=_("Copyright (C)2013 NoXPhasma")
site="http://www.russo79.com/gnome15"
has_preferences=True
default_enabled=True
ICON=os.path.join(os.path.dirname(__file__), 'trafficstats.png')
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={
         g15driver.PREVIOUS_SELECTION : _("Switch daily/monthly stats (Only vnstat)"),
         g15driver.NEXT_SELECTION : _("Switch network device")
         }

#
# This plugin displays the network traffic stats
#

'''
This function must create your plugin instance. You are provided with
a GConf client and a Key prefix to use if your plugin has preferences
'''
def create(gconf_key, gconf_client, screen):
    return G15TrafficStats(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "trafficstats.glade"))
    dialog = widget_tree.get_object("TrafficStats")
    g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/use_vnstat", "UseVnstat", os.path.isfile("/usr/bin/vnstat"), widget_tree)
    ndevice = widget_tree.get_object("NetDevice")
    for netdev in gtop.netlist():
        ndevice.append([netdev])
    g15uigconf.configure_combo_from_gconf(gconf_client, gconf_key + "/networkdevice", "NetworkDevice", "lo", widget_tree)
    g15uigconf.configure_adjustment_from_gconf(gconf_client, gconf_key + "/refresh_interval", "RefreshingScale", 10.0, widget_tree)
    dialog.set_transient_for(parent)
    dialog.run()
    dialog.hide()

class G15TrafficStats(g15plugin.G15RefreshingPlugin):

    '''
    ******************************************************************
    * Lifecycle functions. You must provide activate and deactivate, *
    * the constructor and destroy function are optional              *
    ******************************************************************
    '''

    def __init__(self, gconf_key, gconf_client, screen):
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        g15plugin.G15RefreshingPlugin.__init__(self, gconf_client, gconf_key, \
                                               screen, ICON, id, name, g15gconf.get_float_or_default(self.gconf_client, self.gconf_key + "/refresh_interval", 10.0))
        self.hidden = False

    def activate(self):
        '''
        The activate function is invoked when gnome15 starts up, or the plugin is re-enabled
        after it has been disabled. When extending any of the provided base plugin classes,
        you nearly always want to call the function in the supoer class as well
        '''
        self._load_configuration()

        g15plugin.G15RefreshingPlugin.activate(self)

        '''
        Most plugins will delegate their drawing to a 'Theme'. A theme usually consists of an SVG file, one
        for each model that is supported, and optionally a fragment of Python for anything that can't
        be done with SVG and the built in theme facilities
        '''
        self._reload_theme()

        self.watch(None, self._config_changed)

        self.page.title = "Traffic Stats"

        '''
        Once created, we should always ask for the screen to be drawn (even if another higher
        priority screen is actually active. If the canvas is not displayed immediately,
        the on_shown function will be invoked when it finally is.
        '''
        self.screen.redraw(self.page)

        self.screen.key_handler.action_listeners.append(self)

    def deactivate(self):
        g15plugin.G15RefreshingPlugin.deactivate(self)
        self.screen.key_handler.action_listeners.remove(self)

    def action_performed(self, binding):
        if self.page and self.page.is_visible():
            if binding.action == g15driver.PREVIOUS_SELECTION and self.use_vnstat is True:
                if self.loadpage == 'vnstat_daily':
                    self.gconf_client.set_string(self.gconf_key + "/vnstat_view", "vnstat_monthly")
                else:
                    self.gconf_client.set_string(self.gconf_key + "/vnstat_view", "vnstat_daily")
                return True
            elif binding.action == g15driver.NEXT_SELECTION:
                if self.networkdevice is not None:
                    # get all network devices
                    self.net_data = gtop.netlist()
                    # set network device id +1, to get next device
                    idx = self.net_data.index(self.networkdevice) + 1
                    # if next device id is not present, take first device
                    if idx >= len(self.net_data):
                        idx = 0
                    self.gconf_client.set_string(self.gconf_key + "/networkdevice", self.net_data[idx])
                    return True

    def destroy(self):
        '''
        Invoked when the plugin is disabled or the applet is stopped
        '''
        pass

    def _config_changed(self, client, connection_id, entry, args):

        '''
        Load the gconf configuration
        '''
        self._load_configuration()

        '''
        This is called when the gconf configuration changes. See add_notify and remove_notify in
        the plugin's activate and deactive functions.
        '''
        self.do_refresh()

        '''
        Reload the theme as the layout required may have changed (i.e. with the 'show date'
        option has been change)
        '''
        self._reload_theme()

        '''
        In this case, we temporarily raise the priority of the page. This will force
        the page to be painted (i.e. the paint function invoked). After the specified time,
        the page will revert it's priority. Only one revert timer is active at any one time,
        so it is safe to call this function in quick succession
        '''
        self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)

    def _load_configuration(self):
        self.use_vnstat = g15gconf.get_bool_or_default(self.gconf_client, self.gconf_key + "/use_vnstat", os.path.isfile("/usr/bin/vnstat"))
        self.networkdevice = g15gconf.get_string_or_default(self.gconf_client, self.gconf_key + "/networkdevice", 'lo')
        self.loadpage = g15gconf.get_string_or_default(self.gconf_client, self.gconf_key + "/vnstat_view", "vnstat_daily")
        self.refresh_interval = g15gconf.get_float_or_default(self.gconf_client, self.gconf_key + "/refresh_interval", 10.0)

    '''
    ***********************************************************
    * Functions specific to plugin                            *
    ***********************************************************
    '''

    def _reload_theme(self):
        variant = None
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), variant)

    '''
    Get the properties dictionary
    '''

    def get_theme_properties(self):
        properties = { }

        def convert_bytes(bytes):
            bytes = float(bytes)
            if bytes >= 1099511627776:
                terabytes = bytes / 1099511627776
                size = '%.2fT' % terabytes
            elif bytes >= 1073741824:
                gigabytes = bytes / 1073741824
                size = '%.2fG' % gigabytes
            elif bytes >= 1048576:
                megabytes = bytes / 1048576
                size = '%.2fM' % megabytes
            elif bytes >= 1024:
                kilobytes = bytes / 1024
                size = '%.2fK' % kilobytes
            else:
                size = '%.2fb' % bytes
            return size

        # Split vnstat data into array
        def get_traffic_data(dataType, dataValue, vn):
            line=''
            for item in vn.split("\n"):
                if "%s;%d;" % (dataType, dataValue) in item:
                    line = item.strip().split(';')
                    break
            return line

        # convert MiB and KiB into KB
        def cb(mib, kib):
            return (int(mib) * 1000000) + (int(kib) * 1000)

        '''
        Get the details to display and place them as properties which are passed to
        the theme
        '''

        if self.use_vnstat is False:
            bootup = datetime.datetime.fromtimestamp(int(gtop.uptime().boot_time)).strftime('%d.%m.%y %H:%M')
            sd = gtop.netload(self.networkdevice)
            properties["sdn"] = "DL: " +convert_bytes(sd.bytes_in)
            properties["sup"] = "UL: " +convert_bytes(sd.bytes_out)
            properties["des1"] = "Traffic since: " +bootup
            properties["title"] = self.networkdevice + " Traffic"

        else:
            vnstat, vn = g15os.get_command_output('vnstat -i ' + self.networkdevice + ' --dumpdb')
            if vnstat != 0:
                properties["message"] = "vnstat is not installed!"
            else:
                chErr = str(vn.find("Error"));
                if chErr != "-1":
                    properties["message"] = "No stats for device " + self.networkdevice
                else:
                    properties["title"] = self.networkdevice +" Traffic (U/D)"

                    def get_data(kind, period):
                        # get vnstat data as array, array content: 2 = unixtime, 4 = up MiB, 6 = up KiB, 3 = dn MiB, 5 = dn KiB
                        line = get_traffic_data(kind, period, vn)
                        if line[7] == '1':
                            up = convert_bytes(cb(line[4], line[6]))
                            dn = convert_bytes(cb(line[3], line[5]))
                            des = int(line[2])
                            return [up, dn, des]
                        else:
                            return None

                    if self.loadpage == 'vnstat_daily':
                        k = "d"
                        fmt = '%A'
                    elif self.loadpage == 'vnstat_monthly':
                        k = "m"
                        fmt = '%B'

                    for p in range(0,3):
                        data = get_data(k,p)
                        if data is not None:
                            properties["d"] = "/"
                            properties["dup" + str(p + 1)] = data[0]
                            properties["ddn" + str(p + 1)] = data[1]
                            properties["des" + str(p + 1)] = datetime.datetime.fromtimestamp(data[2]).strftime(fmt)

        return properties
