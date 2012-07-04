// +-----------------------------------------------------------------------------+
// | GPL                                                                         |
// +-----------------------------------------------------------------------------+
// | Copyright (c) Brett Smith <tanktarta@blueyonder.co.uk>                      |
// |                                                                             |
// | This program is free software; you can redistribute it and/or               |
// | modify it under the terms of the GNU General Public License                 |
// | as published by the Free Software Foundation; either version 2              |
// | of the License, or (at your option) any later version.                      |
// |                                                                             |
// | This program is distributed in the hope that it will be useful,             |
// | but WITHOUT ANY WARRANTY; without even the implied warranty of              |
// | MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               |
// | GNU General Public License for more details.                                |
// |                                                                             |
// | You should have received a copy of the GNU General Public License           |
// | along with this program; if not, write to the Free Software                 |
// | Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA. |
// +-----------------------------------------------------------------------------+

/*
 * Gnome15 - The Logitech Keyboard Manager for Linux
 *
 * This GNOME Shell extension allows control of all supported and connected
 * Logitech devices from the shell's top panel. A menu button is added for
 * each device, providing options to enable/disable the device, enable/disable
 * screen cycling, and make a particular page the currently visible one.
 */

const St = imports.gi.St;
const Main = imports.ui.main;
const Tweener = imports.ui.tweener;
const DBus = imports.dbus;
const Lang = imports.lang;
const PanelMenu = imports.ui.panelMenu;
const PopupMenu = imports.ui.popupMenu;
const GLib = imports.gi.GLib;
const Clutter = imports.gi.Clutter;

let currNotification, gnome15System, devices;

/*
 * Remote object definitions. This is just a sub-set of the full API 
 * available, just enough to do the job
 */ 

const Gnome15ServiceInterface = {
	name : 'org.gnome15.Service',
	methods : [ {
		name : 'GetDevices',
		inSignature : '',
		outSignature : 'as'
	}, {
		name : 'GetScreens',
		inSignature : '',
		outSignature : 'as'
	}, {
		name : 'GetServerInformation',
		inSignature : '',
		outSignature : 'ssss'
	},{
		name : 'IsStarted',
		inSignature : '',
		outSignature : 'b'
	},{
		name : 'IsStarting',
		inSignature : '',
		outSignature : 'b'
	},{
		name : 'IsStopping',
		inSignature : '',
		outSignature : 'b'
	},{
		name : 'Stop',
		inSignature : '',
		outSignature : ''
	},{
		name : 'Stop',
		inSignature : '',
		outSignature : ''
	}, ],
	signals : [ {
		name : 'ScreenAdded',
		inSignature : 's'
	},{
		name : 'ScreenRemoved',
		inSignature : 's'
	},{
		name : 'Started'
	},{
		name : 'Starting'
	},{
		name : 'Stopped'
	},{
		name : 'Stopping'
	} ]
};


const Gnome15ScreenInterface = {
	name : 'org.gnome15.Screen',
	methods : [ {
		name : 'GetPages',
		inSignature : '',
		outSignature : 'as'
	}, {
		name : 'IsConnected',
		inSignature : '',
		outSignature : 'b'
	}, {
		name : 'GetDriverInformation',
		inSignature : '',
		outSignature : 'ssnnn'
	}, {
		name : 'IsCyclingEnabled',
		inSignature : '',
		outSignature : 'b'
	}, {
		name : 'SetCyclingEnabled',
		inSignature : 'b',
		outSignature : ''
	}, {
		name : 'Cycle',
		/* No idea why, but this signature is actually 'n', but this causes
		 * an exception when calling with JavaScript integer. 
		 */ 
		inSignature : 'i',
		outSignature : ''
	}, {
		name : 'CycleKeyboard',
		/* No idea why, but this signature is actually 'n', but this causes
		 * an exception when calling with JavaScript integer. 
		 */ 
		inSignature : 'i',
		outSignature : ''
	} ],
	signals : [ {
		name : 'PageCreated',
		inSignature : 'ss'
	},{
		name : 'PageDeleted',
		inSignature : 's'
	},{
		name : 'PageDeleting',
		inSignature : 's'
	},{
		name : 'PageChanged',
		inSignature : 's'
	},{
		name : 'PageTitleChanged',
		inSignature : 'ss'
	},{
		name : 'Connected',
		inSignature : 's'
	},{
		name : 'Disconnected',
		inSignature : 's'
	}, {
		name: 'CyclingChanged',
		inSignature : 'b'
	} ]
};


const Gnome15DeviceInterface = {
	name : 'org.gnome15.Device',
	methods : [ {
		name : 'GetScreen',
		inSignature : '',
		outSignature : 's'
	},{
		name : 'GetModelFullName',
		inSignature : '',
		outSignature : 's'
	},{
		name : 'GetUID',
		inSignature : '',
		outSignature : 's'
	},{
		name : 'GetModelId',
		inSignature : '',
		outSignature : 's'
	},{
		name : 'Enable',
		inSignature : '',
		outSignature : ''
	}, {
		name : 'Disable',
		inSignature : '',
		outSignature : ''
	} ],
	signals : [ {
		name : 'ScreenAdded',
		inSignature : 's'
	},{
		name : 'ScreenRemoved',
		inSignature : 's'
	} ]
};

const Gnome15PageInterface = {
	name : 'org.gnome15.Page',
	methods : [ {
		name : 'GetTitle',
		inSignature : '',
		outSignature : 's'
	},{
		name : 'GetId',
		inSignature : '',
		outSignature : 's'
	}, {
		name : 'CycleTo',
		inSignature : '',
		outSignature : ''
	} ]
};

/**
 * Instances of this class are responsible for managing a single device.
 * A single button is created and added to the top panel, various attributes
 * about the device attached are read, and if the device currently has
 * a screen (i.e. is enabled), the initial page list is loaded. 
 * 
 * Signals are also setup to watch for the screen being enable / disabled
 * externally.
 */
const DeviceItem = new Lang.Class({
    Name: 'DeviceItem',
	_init : function(key) {
		this.parent();
		this._buttonSignals = new Array();
		let gnome15Device = _createDevice(key);
		gnome15Device.GetModelFullNameRemote(Lang.bind(this, function(msg) {
			let modelFullName = msg;
			gnome15Device.GetModelIdRemote(Lang.bind(this, function(msg) {
				let uid = msg;
				gnome15Device.GetScreenRemote(Lang.bind(this, function(msg) {
					gnome15Device.connect("ScreenAdded", Lang.bind(this, function(src, screenPath) {
						this._getPages(screenPath);
					}));
					gnome15Device.connect("ScreenRemoved", Lang.bind(this, function(src, screenPath) {
						this._cleanUp();
						this._gnome15Button.clearPages();
					}));
					this._addButton(key, modelFullName, uid, msg);
				}));
			}));
		}));
	},
	
	_addButton: function(key, modelFullName, modelId, screen) {
		let hasScreen = screen != null && screen.length > 0;
		this._gnome15Button = new DeviceButton(key, modelId, modelFullName, hasScreen);
		Main.panel._rightBox.insert_child_at_index(this._gnome15Button.actor, 1);
		Main.panel._rightBox.child_set(this._gnome15Button.actor, {
			y_fill : true
		});
		Main.panel._menus.addMenu(this._gnome15Button.menu);
		if(hasScreen) {
			/* If this device already has a screen (i.e. is enabled, load the
			 * pages now). Otherwise, we wait for ScreenAdded to come in
			 * in extension itself
			 */
			this._getPages(screen);
		}
		else {
			this._gnome15Button.reset();	
		}
	},
	
	/**
	 * Removes the signals that are being watched for this device and 
	 * mark the button so that the enabled switch is turned off when
	 * the menu is reset 
	 */
	_cleanUp: function() {
		if(this._gnome15Button._screen != null) {
			for(let key in this._buttonSignals) {
				this._gnome15Button._screen.disconnect(this._buttonSignals[key]);
			}
			this._buttonSignals.splice(0, this._buttonSignals.length);
			this._gnome15Button._screen = null;
		}
	},
	
	/**
	 * Callback that receives the full list of pages currently showing on
	 * this device and adds them to the button. It then starts watching for
	 * new pages appearing, or pages being deleted and acts accordingly.
	 */
	_getPages: function(screen) {
		this._cleanUp();
		this._gnome15Button._screen = _createScreen(screen);
		this._gnome15Button._screen.GetPagesRemote(Lang.bind(this, function(pages) {
			this._gnome15Button.clearPages();
			for(let key in pages) {
		        this._gnome15Button.addPage(pages[key]);
			}
			this._gnome15Button._screen.IsCyclingEnabledRemote(Lang.bind(this, function(cyclingEnabled) {
				this._gnome15Button._cyclingEnabled = cyclingEnabled;
				this._buttonSignals.push(this._gnome15Button._screen.connect("PageCreated", Lang.bind(this, function(src, pagePath, title) {
					this._gnome15Button.addPage(pagePath);
				})));
				this._buttonSignals.push(this._gnome15Button._screen.connect("PageDeleting", Lang.bind(this, function(src, pagePath) {
					this._gnome15Button.deletePage(pagePath);
				})));
				this._buttonSignals.push(this._gnome15Button._screen.connect("CyclingChanged", Lang.bind(this, function(src, cycle) {
					this._gnome15Button.setCyclingEnabled(cycle);
				})));
			}));			
		}));
		
		
	},
	
	/**
	 * Called as a result of the service disappearing or the extension being
	 * disabled. The button is removed from the top panel.
	 */
	close : function(pages) {
		this._gnome15Button.destroy();
	}
});

/**
 * A switch menu item that allows a single device to be enabled or disabled.
 */
const EnableDisableMenuItem = new Lang.Class({
    Name: 'EnableDisableMenuItem',
    Extends: PopupMenu.PopupSwitchMenuItem,

	_init : function(devicePath, modelName, screen) {
		this.parent(modelName);
		this.setToggleState(screen != null);
		this.connect('toggled', Lang.bind(this, function() {
			if(this.state) {
				_createDevice(devicePath).EnableRemote();
			}
			else {
				_createDevice(devicePath).DisableRemote();
			}
		}));
	},

	activate : function(event) {
		this.parent(event);
	},
});

/**
 * A switch menu item that allows automatic page cycling to be enabled or
 * disabled.
 */
const CyclePagesMenuItem = new Lang.Class({
    Name: 'CyclePagesMenuItem',
    Extends: PopupMenu.PopupSwitchMenuItem,

	_init : function(selected, screen) {
		this.parent("Cycle pages automatically");
		this.setToggleState(selected);
		this._screen = screen;
	},

	activate : function(event) {
		this._screen.SetCyclingEnabledRemote(!this.state);
		this.parent(event);
	},
});

/**
 * A menu item that represents a single page on a single device. Activating
 * this item causes the page to be displayed. 
 */
const PageMenuItem = new Lang.Class({
    Name: 'PageMenuItem',
    Extends: PopupMenu.PopupBaseMenuItem,

	_init : function(lblText, lblId, page_proxy) {
		this.parent();
		this.label = new St.Label({
			text : lblText
		});
		this.addActor(this.label);
		this._pageProxy = page_proxy;
		this._text = lblText;
		this._idTxt = lblId;
	},

	activate : function(event) {
		this._pageProxy.CycleToRemote();
		this.parent(event);
	},
});

/**
 * A menu item that that activates g15-config. It will open with provided
 * device UID open (via the -d option of g15-config). 
 */
const PreferencesMenuItem = new Lang.Class({
    Name: 'PreferencesMenuItem',
    Extends: PopupMenu.PopupMenuItem,

	_init : function(deviceUid) {
		this.parent("Configuration");
		this._deviceUid = deviceUid
	},

	activate : function(event) {
        GLib.spawn_command_line_async('g15-config -d ' + this._deviceUid);
        this.parent(event);
	},
});

/**
 * Shell top panel "System Status Button" that represents a single Gnome15
 * device.  
 */
const DeviceButton = new Lang.Class({
    Name: 'DeviceButton',
    Extends: PanelMenu.SystemStatusButton,

	_init : function(devicePath, modelId, modelName) {
		this._deviceUid = devicePath.substring(devicePath.lastIndexOf('/') + 1);
		this._itemMap = {};
		this.parent('logitech-' + modelId);
		this._cyclingEnabled = false;
		this._devicePath = devicePath;
		this._itemList = new Array();
		this._modelId = modelId;
		this._modelName = modelName;
		this._screen = null;
        this._iconActor.add_style_class_name('device-icon');
        this._iconActor.set_icon_size(24);
        this._iconActor.add_style_class_name('device-button');
        
        // Mouse whell events
        this.actor.connect('scroll-event', Lang.bind(this, this._onScrollEvent));
	},
	
	/**
	 * Set whether cycling is enabled for this device
	 * 
	 * @param cycle enable cycling
	 */
	setCyclingEnabled: function(cycle) {
		this._cyclingEnabled = cycle;
		this.reset();
	},

	/**
	 * Remove the menu item for a page given it's path.
	 * 
	 * @param pagePath path of page
	 */
	deletePage: function(pagePath) {
		let idx = this._itemList.indexOf(pagePath);
		if(idx > 0) {
			this._itemList.splice(idx, 1);
			this._itemMap[pagePath].destroy();
			delete this._itemMap[pagePath];
		}
	},

	/**
	 * Clear all pages from this menu.
	 */
	clearPages : function() {
		this._itemList = new Array();
		this.reset();
	},

	/**
	 * Add a new page to the menu given it's path.
	 * 
	 * @param pagePath page of page to add
	 */
	addPage : function(pagePath) {
		this._itemList.push(pagePath);
		this._addPage(pagePath);
	},

	/**
	 * Rebuild the entire menu. 
	 */
	reset : function() {
		this.menu.removeAll();
		this.menu.addMenuItem(new EnableDisableMenuItem(this._devicePath, this._modelName, this._screen));
		this.menu.addMenuItem(new CyclePagesMenuItem(this._cyclingEnabled, this._screen));
		this.menu.addMenuItem(new PreferencesMenuItem(this._deviceUid));
		this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
		for (let key in this._itemList) {
			this._addPage(this._itemList[key]);
		}
	},
	
	/**
	 * Add the menu items for a single page given it's page. Various attributes
	 * about the page are read via dbus and the menu item constructed and
	 * added to the menu compent.
	 * 
	 * @param pagePath page of page.
	 */
	_addPage : function(pagePath) {
		let Gnome15PageProxy = DBus.makeProxyClass(Gnome15PageInterface);
		let pageProxy = new Gnome15PageProxy(DBus.session, 'org.gnome15.Gnome15', pagePath);
		pageProxy.GetTitleRemote(Lang.bind(this, function(title) {
			let item = new PageMenuItem(title, title, pageProxy);
			this._itemMap[pagePath] = item;
			this.menu.addMenuItem(item);
		}));
	},
	
	/**
	 * Handle mouse wheel events by cycling pages.
	 * 
	 * @param actor source of event
	 * @param event event
	 */
	_onScrollEvent: function(actor, event) {
        let direction = event.get_scroll_direction();
        if(this._screen != null) {
	        if (direction == Clutter.ScrollDirection.DOWN) {
	        	this._screen.CycleRemote(-1);
	        }
	        else if (direction == Clutter.ScrollDirection.UP) {
	        	this._screen.CycleRemote(1);
	        }
	        if (direction == Clutter.ScrollDirection.LEFT) {
	        	this._screen.CycleKeyboardRemote(-1);
	        }
	        else if (direction == Clutter.ScrollDirection.RIGHT) {
	        	this._screen.CycleKeyboardRemote(1);
	        }
        }
    },
});

/*
 * GNOME Shell Extension API functions
 */

function init() {
	devices = {}
	let Gnome15ServiceProxy = DBus.makeProxyClass(Gnome15ServiceInterface);
	
	/* The "Service" is the core of Gnome, so connect to it and watch for some
	 * signals
	 */
	gnome15System = new Gnome15ServiceProxy(DBus.session,
			'org.gnome15.Gnome15', '/org/gnome15/Service');

	gnome15System.connect("Started", _onDesktopServiceStarted);
	gnome15System.connect("Stopping", _onDesktopServiceStopping);

}

function enable() {
	DBus.session.watch_name('org.gnome15.Gnome15',
	                       false, // do not launch a name-owner if none exists
	                       _onDesktopServiceAppeared,
	                       _onDesktopServiceVanished);

	gnome15System.IsStartedRemote(Lang.bind(this, function(started) {
		if(started) {
			gnome15System.GetDevicesRemote(_refreshDeviceList);	
		}
	}));
}

function disable() {
	for(let key in devices) {
        _deviceRemoved(key)
	}
}

/*
 * Private functions
 */

/**
 * Callback invoked when the DBus name owner changes (added). We don't actually care
 * about this one as we load pages on other signals
 */
function _onDesktopServiceAppeared() {
}

/**
 * Callback invoked when the DBus name owner changes (removed). This occurs
 * when the service disappears, evens when it dies unexpectedly. 
 */
function _onDesktopServiceVanished() {
	_onDesktopServiceStopping();
}

/**
 * Callback invoked when the Gnome15 service starts. We get the initial device
 * list at this point. 
 */
function _onDesktopServiceStarted() {
	gnome15System.GetDevicesRemote(_refreshDeviceList);
}

/**
 * Invoked when the Gnome15 desktop service starts shutting down (as a result
 * of user selectint "Stop Service" most probably).
 */
function _onDesktopServiceStopping() {
	for(let key in devices) {
        _deviceRemoved(key)
	}
}

/**
 * Callback from GetDevicesRemote that reads the returned device list and
 * creates a button for each one.
 */
function _refreshDeviceList(msg) {
	for (let key in msg) {
		_deviceAdded(msg[key])
	}
}

/**
 * Gnome15 doesn't yet send DBus events when devices are hot-plugged, but it
 * soon will and this function will add new device when they appear.
 */
function _deviceAdded(key) {
	devices[key] = new DeviceItem(key)
}

/**
 * Gnome15 doesn't yet send DBus events when devices are hot-plugged, but it
 * soon will and this function will add new device when they are removed.
 */
function _deviceRemoved(key) {
	devices[key].close()
	delete devices[key]
}

/**
 * Utility for creating a org.gnome15.Screen instance given it's path.
 * 
 * @param path
 * @returns {Gnome15ScreenProxy}
 */
function _createScreen(path) {
	let Gnome15ScreenProxy = DBus.makeProxyClass(Gnome15ScreenInterface);
	return new Gnome15ScreenProxy(DBus.session,
			'org.gnome15.Gnome15', path);
}

/**
 * Utility for creating an org.gnome15.Device instance given it's path.
 * 
 * @param path
 * @returns {Gnome15DeviceProxy}
 */
function _createDevice(path) {
	let Gnome15DeviceProxy = DBus.makeProxyClass(Gnome15DeviceInterface);
	return new Gnome15DeviceProxy(DBus.session,
			'org.gnome15.Gnome15', path);
}
