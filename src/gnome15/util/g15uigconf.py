#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2010 Brett Smith <tanktarta@blueyonder.co.uk>
#  Copyright (C) 2013 Nuno Araujo <nuno.araujo@russo79.com>
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

import g15convert

'''
Set of utility methods to ease the binding between UI widgets and gconf settings
'''

def configure_colorchooser_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, default_alpha = None):
    """
    Sets the color and alpha values of a colorchooser widget from a gconf key
    and initialize an event to store the value set by the user in the same
    gconf key

    gconf_client:  Instance of GConfClient to communicate with GConf
    gconf_key:     Name of the key having the value
    widget_id:     Id of the widget
    default_value: Default value to set if it isn't set in GConf
    widget_tree:   Widget tree containing the widget to setup
    default_alpha: If different than None, the alpha value for the color is read
                   from the gconf_key + "_opacity" key.
    """
    widget = widget_tree.get_object(widget_id)
    if widget == None:
        raise Exception("No widget with id %s." % widget_id)
    val = gconf_client.get_string(gconf_key)
    if val == None or val == "":
        col  = g15convert.to_color(default_value)
    else:
        col = g15convert.to_color(g15convert.to_rgb(val))
    if default_alpha != None:
        alpha = gconf_client.get_int(gconf_key + "_opacity")
        widget.set_use_alpha(True)
        widget.set_alpha(alpha << 8)
    else:
        widget.set_use_alpha(False)
    widget.set_color(col)
    handler_id = widget.connect("color-set", color_changed, gconf_client, gconf_key)
    return handler_id

def color_changed(widget, gconf_client, key):
    val = widget.get_color()
    gconf_client.set_string(key, "%d,%d,%d" % ( val.red >> 8, val.green >> 8, val.blue >> 8 ))
    if widget.get_use_alpha():
        gconf_client.set_int(key + "_opacity", widget.get_alpha() >> 8)

def configure_spinner_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, decimal = False):
    """
    Sets the value of a spinner from a gconf key and initializes an event to
    store the spinner value in the same gconf key when changed by the user.

    gconf_client:  Instance of GConfClient to communicate with GConf
    gconf_key:     Name of the key having the value
    widget_id:     Id of the widget
    default_value: Default value to set if it isn't set in GConf
    widget_tree:   Widget tree containing the widget to set up
    decimal:       If True, then the spinner value is a float else an int
    """
    widget = widget_tree.get_object(widget_id)
    if widget == None:
        raise Exception("No widget with id %s." % widget_id)
    model = widget.get_adjustment()
    entry = gconf_client.get(gconf_key)
    val = default_value
    if entry != None:
        if decimal:
            val = entry.get_float()
        else:
            val = entry.get_int()
    model.set_value(val)
    handler_id = widget.connect("value-changed", spinner_changed, gconf_client, gconf_key, model)
    return handler_id


def spinner_changed(widget, gconf_client, key, model, decimal = False):
    if decimal:
        gconf_client.set_float(key, widget.get_value())
    else:
        gconf_client.set_int(key, int(widget.get_value()))

def configure_combo_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree):
    """
    Selects an item of a combobox from a gconf key and initializes an event to
    store the current selected item value in the same gconf key when changed by
    the user.

    gconf_client:  Instance of GConfClient to communicate with GConf
    gconf_key:     Name of the key having the value
    widget_id:     Id of the widget
    default_value: Default value to set if it isn't set in GConf.
                   This value can either be an int or a string.
                   When an int, it represents the index of the combobox item to select.
                   When a string, it represents the value that must be selected.
    widget_tree:   Widget tree containing the widget to set up
    """
    widget = widget_tree.get_object(widget_id)
    if widget == None:
        raise Exception("No widget with id %s." % widget_id)
    model = widget.get_model()
    handler_id = widget.connect("changed", combo_box_changed, gconf_client, gconf_key, model, default_value)

    if isinstance(default_value, int):
        e = gconf_client.get(gconf_key)
        if e:
            val = e.get_int()
        else:
            val = default_value
    else:
        val = gconf_client.get_string(gconf_key)
        if val == None or val == "":
            val = default_value
    idx = 0
    for row in model:
        if isinstance(default_value, int):
            row_val = int(row[0])
        else:
            row_val = str(row[0])
        if row_val == val:
            widget.set_active(idx)
        idx += 1

    return handler_id

def combo_box_changed(widget, gconf_client, key, model, default_value):
    if isinstance(default_value, int):
        gconf_client.set_int(key, int(model[widget.get_active()][0]))
    else:
        gconf_client.set_string(key, model[widget.get_active()][0])

def configure_checkbox_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, watch_changes = False):
    """
    Sets the state of a checkbox from a gconf key and initializes an event to
    store the current state in the same gconf key when changed by the user.

    gconf_client:  Instance of GConfClient to communicate with GConf
    gconf_key:     Name of the key having the value
    widget_id:     Id of the widget
    default_value: Default value to set if it isn't set in GConf.
    widget_tree:   Widget tree containing the widget to set up
    watch_changes: If True, then keeps updating the state of the checkbox when
                   the value of the gconf key changes.
    """
    widget = widget_tree.get_object(widget_id)
    entry = gconf_client.get(gconf_key)
    connection_id = None
    if entry != None:
        widget.set_active(entry.get_bool())
    else:
        widget.set_active(default_value)
    handler_id = widget.connect("toggled", checkbox_changed, gconf_key, gconf_client)
    if watch_changes:
        connection_id = gconf_client.notify_add(gconf_key, boolean_conf_value_change,( widget, gconf_key ));
    return (handler_id, connection_id)

def boolean_conf_value_change(client, connection_id, entry, args):
    widget, key = args
    widget.set_active( entry.get_value().get_bool())

def checkbox_changed(widget, key, gconf_client):
    gconf_client.set_bool(key, widget.get_active())

def configure_text_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, watch_changes = False):
    """
    Sets the text of a text entry widget from a gconf key and initializes an
    event to store the text in the same gconf key when changed by the user.

    gconf_client:  Instance of GConfClient to communicate with GConf
    gconf_key:     Name of the key having the value
    widget_id:     Id of the widget
    default_value: Default value to set if it isn't set in GConf.
    widget_tree:   Widget tree containing the widget to set up
    watch_changes: If True, then keeps updating the value of the text entry when
                   the value of the gconf key changes.
    """
    widget = widget_tree.get_object(widget_id)
    entry = gconf_client.get(gconf_key)
    connection_id = None
    if entry != None:
        widget.set_text(entry.get_string())
    else:
        widget.set_text(default_value)
    handler_id = widget.connect("changed", text_changed, gconf_key, gconf_client)
    if watch_changes:
        connection_id = gconf_client.notify_add(gconf_key, text_conf_value_change,( widget, gconf_key ));
    return (handler_id, connection_id)

def text_conf_value_change(client, connection_id, entry, args):
    widget, key = args
    widget.set_text( entry.get_value().get_string())

def text_changed(widget, key, gconf_client):
    gconf_client.set_string(key, widget.get_text())

def configure_radio_from_gconf(gconf_client, gconf_key, widget_ids, gconf_values, default_value, widget_tree, watch_changes = False):
    """
    Sets the checked state of a set of radioboxes from a gconf key and initializes
    an event to store their state in the same gconf key when changed by the user.

    gconf_client:  Instance of GConfClient to communicate with GConf
    gconf_key:     Name of the key having the value
    widget_ids:    Ids of the widgets
    gconf_values:  The values that should be read from the gconf_key to activate the
                   radiobox
    default_value: Default value to set if it isn't set in GConf.
    widget_tree:   Widget tree containing the widget to set up
    watch_changes: If True, then keeps updating the value of the text entry when
                   the value of the gconf key changes.
    """
    entry = gconf_client.get(gconf_key)
    handles = []
    sel_entry = entry.get_string() if entry else None
    for i in range(0, len(widget_ids)):
        gconf_value = gconf_values[i]
        active = ( entry != None and gconf_value == sel_entry ) or ( entry == None and default_value == gconf_value )
        widget_tree.get_object(widget_ids[i]).set_active(active)

    for i in range(0, len(widget_ids)):
        widget = widget_tree.get_object(widget_ids[i])
        handler_id = widget.connect("toggled", radio_changed, gconf_key, gconf_client, gconf_values[i])
        if watch_changes:
            handles.append(gconf_client.notify_add(gconf_key, radio_conf_value_change,( widget, gconf_key, gconf_values[i] )))
    return (handler_id, handles)

def radio_conf_value_change(client, connection_id, entry, args):
    widget, key, gconf_value = args
    str_value = entry.get_value().get_string()
    widget.set_active(str_value == gconf_value)

def radio_changed(widget, key, gconf_client, gconf_value):
    gconf_client.set_string(key, gconf_value)

def configure_adjustment_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree):
    """
    Sets the value of a adjustment from a gconf key and initializes an event to
    store the value in the same gconf key when changed by the user.

    gconf_client:  Instance of GConfClient to communicate with GConf
    gconf_key:     Name of the key having the value
    widget_id:     Id of the widget
    default_value: Default value to set if it isn't set in GConf
    widget_tree:   Widget tree containing the widget to set up
    """
    adj = widget_tree.get_object(widget_id)
    entry = gconf_client.get(gconf_key)
    if entry != None:
        if isinstance(default_value, int):
            adj.set_value(entry.get_int())
        else:
            adj.set_value(entry.get_float())
    else:
        adj.set_value(default_value)
    handler_id = adj.connect("value-changed", adjustment_changed, gconf_key, gconf_client, isinstance(default_value, int))
    return handler_id

def adjustment_changed(adjustment, key, gconf_client, integer = True):
    if integer:
        gconf_client.set_int(key, int(adjustment.get_value()))
    else:
        gconf_client.set_float(key, adjustment.get_value())

