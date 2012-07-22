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
Manages registration of 'actions'. Each device will support default bindings
to these actions based on the keys they have available.

Additionally, plugins may register new actions that may be bound to macro
keys. 
"""

import g15driver

"""
Some screen related actions that may be mapped to additional keys
"""
NEXT_SCREEN = "next-screen"
PREVIOUS_SCREEN = "previous-screen"
NEXT_BACKLIGHT = "next-backlight"
PREVIOUS_BACKLIGHT = "previous-backlight"
CANCEL_MACRO = "cancel-macro"

"""
Global the plugins and other subsystems may add new actions too. The list
here is the minimum a device must support to be useful.
"""
actions = [           
        g15driver.NEXT_SELECTION,
        g15driver.PREVIOUS_SELECTION,
        g15driver.NEXT_PAGE,
        g15driver.PREVIOUS_PAGE,
        g15driver.SELECT,
        g15driver.VIEW,
        g15driver.CLEAR,
        g15driver.MENU,
        g15driver.MEMORY_1,
        g15driver.MEMORY_2,
        g15driver.MEMORY_3,
        NEXT_SCREEN,
        PREVIOUS_SCREEN,
        NEXT_BACKLIGHT,
        PREVIOUS_BACKLIGHT,
        CANCEL_MACRO
        ]


class ActionBinding():
    """
    Created when an action is invoked and contains the keys that activated
    the action (if any), the state they were in and the action ID
    """
    def __init__(self, action, keys, state):
        self.action = action
        self.state = state
        self.keys = keys
        
    def __cmp__(self, other):
        f = cmp(self.keys, other.keys)
        return f if f != 0 else cmp(self.state, other.state)