const St = imports.gi.St;
const Main = imports.ui.main;
const Tweener = imports.ui.tweener;
const DBus = imports.dbus;
const Lang = imports.lang;
const PanelMenu = imports.ui.panelMenu;
const PopupMenu = imports.ui.popupMenu;
const GLib = imports.gi.GLib;

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
		this._gnome15Button = new AppMenu(key, modelId, modelFullName, hasScreen);
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
	
	_cleanUp: function() {
		if(this._gnome15Button._screen != null) {
			for(let key in this._buttonSignals) {
				this._gnome15Button._screen.disconnect(this._buttonSignals[key]);
			}
			this._buttonSignals.splice(0, this._buttonSignals.length);
			this._gnome15Button._screen = null;
		}
	},
	
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
	
	close : function(pages) {
		this._gnome15Button.destroy();
	}
});

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

const AppMenuItem = new Lang.Class({
    Name: 'AppMenuItem',
    Extends: PopupMenu.PopupBaseMenuItem,

	_init : function(lblText, lblId, appMenu, page_proxy) {
		this.parent();
		this.label = new St.Label({
			text : lblText
		});
		this.addActor(this.label);
		this._pageProxy = page_proxy;
		this._text = lblText;
		this._idTxt = lblId;
		this._appMenu = appMenu;
	},

	activate : function(event) {
		this._pageProxy.CycleToRemote();
		this.parent(event);
	},
});

const PreferencesMenuItem = new Lang.Class({
    Name: 'PreferencesMenuItem',
    Extends: PopupMenu.PopupMenuItem,

	_init : function(deviceUid) {
		this.parent("Configuration");
		this._deviceUid = deviceUid
	},

	activate : function(event) {
        GLib.spawn_command_line_async("g15-config -d " + this._deviceUid);
        this.parent(event);
	},
});

const AppMenu = new Lang.Class({
    Name: 'AppMenu',
    Extends: PanelMenu.SystemStatusButton,

	_init : function(devicePath, model_id, model_name) {
		this._itemMap = {};
		this.parent('logitech-' + model_id);
		this._cyclingEnabled = false;
		this._devicePath = devicePath;
		this._item_list = new Array();
		this._model_id = model_id;
		this._model_name = model_name;
		this._screen = null;
        this._iconActor.add_style_class_name('device-icon');
        this._iconActor.set_icon_size(24);
        this._iconActor.add_style_class_name('device-button');
	},
	
	setCyclingEnabled: function(cycle) {
		this._cyclingEnabled = cycle;
		this.reset();
	},
	
	deletePage: function(pagePath) {
		let idx = this._item_list.indexOf(pagePath);
		if(idx > 0) {
			this._item_list.splice(idx, 1);
		}
		this._itemMap[pagePath].destroy();
		delete this._itemMap[pagePath];
	},

	clearPages : function() {
		this._item_list = new Array();
		this.reset();
	},

	handleEvent : function(eventId) {
		_showGlobalText(eventId);
//		if ("AppMenuRefresh" == eventId) {
//			gnome15System.GetMenuRemote('Refresh', _refreshScreenIdList);
//		}
	},

	addPage : function(pagePath) {
		this._item_list.push(pagePath);
		this._addPage(pagePath);
	},

	reset : function() {
		this.menu.removeAll();
		this.menu.addMenuItem(new EnableDisableMenuItem(this._devicePath, this._model_name, this._screen));
		this.menu.addMenuItem(new CyclePagesMenuItem(this._cyclingEnabled, this._screen));
		this.menu.addMenuItem(new PreferencesMenuItem());
		this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
		for (let key in this._item_list) {
			this._addPage(this._item_list[key]);
		}
	},
	
	_addPage : function(pagePath) {
		let Gnome15PageProxy = DBus.makeProxyClass(Gnome15PageInterface);
		let pageProxy = new Gnome15PageProxy(DBus.session, 'org.gnome15.Gnome15', pagePath);
		pageProxy.GetTitleRemote(Lang.bind(this, function(title) {
			let item = new AppMenuItem(title, title, this, pageProxy);
			this._itemMap[pagePath] = item;
			this.menu.addMenuItem(item);
		}));
	}
});

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

//	this.enable();
}

function enable() {
	gnome15System.GetDevicesRemote(_refreshDeviceList);
}

function disable() {
	for(let key in devices) {
        _deviceRemoved(key)
	}
}

function _onDesktopServiceStarted() {
	gnome15System.GetDevicesRemote(_refreshDeviceList);
}

function _onDesktopServiceStopping() {
	for(let key in devices) {
        _deviceRemoved(key)
	}
}

function _refreshDeviceList(msg) {
	for (let key in msg) {
		_deviceAdded(msg[key])
	}
}

function _deviceAdded(key) {
	devices[key] = new DeviceItem(key)
}

function _deviceRemoved(key) {
	devices[key].close()
	delete devices[key]
}

// CallBack from the StatusChanged event
function _statusChanged(object, msg) {
}

// Method to show a status message to the user, usable anywhere in this script.
function _showGlobalText(label) {
	_hideGlobalText();
	// Add the notification message to the desktop
	currNotification = new St.Label({
		style_class : 'helloworld-label',
		text : label
	});
	Main.uiGroup.add_actor(currNotification);
	currNotification.opacity = 255;

	// Place the message in the center of the screen
	let monitor = Main.layoutManager.primaryMonitor;
	currNotification.set_position(Math.floor(monitor.width / 2
			- currNotification.width / 2), Math.floor(monitor.height / 2
			- currNotification.height / 2));

	// Add a transition to remove the message shortly after it appears
	Tweener.addTween(currNotification, {
		opacity : 0,
		time : 3.0,
		transition : 'easeOutQuad',
		onComplete : _hideGlobalText
	});
}

// Callback to remove the notification message after the transition
function _hideGlobalText() {
	if(currNotification) {
		Main.uiGroup.remove_actor(currNotification);
	}
	currNotification = null;
}

function _createScreen(path) {
	let Gnome15ScreenProxy = DBus.makeProxyClass(Gnome15ScreenInterface);
	return new Gnome15ScreenProxy(DBus.session,
			'org.gnome15.Gnome15', path);
}

function _createDevice(path) {
	let Gnome15DeviceProxy = DBus.makeProxyClass(Gnome15DeviceInterface);
	return new Gnome15DeviceProxy(DBus.session,
			'org.gnome15.Gnome15', path);
}
