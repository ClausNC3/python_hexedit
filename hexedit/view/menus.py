"""The 'View' Module of the application: Various menus.

This file contains the implementation for the different menus
of the View.

License:
    MIT License

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""
from typing import Dict, Callable
from functools import partial

import tkinter as tk
import enum
import importlib.resources
from ..common import *


class BaseHexAreaMenu():
    """Base class for a menu in the Hex area."""
    def __init__(self, parent):
        self.parent = parent

    def show(self, event) -> None:
        """Show the menu."""
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()


class MenuBar(tk.Menu):
    """The main application menu."""
    
    class Events(enum.Enum):
        """Events that can be triggered by the menu."""

        # User wants to refresh the view
        REFRESH                 = enum.auto()

        # User wants to jump to offset
        GOTO                    = enum.auto()

        # User wants to create a new file
        NEW                     = enum.auto()

        # User wants to open file
        OPEN                    = enum.auto()

        # User wants to save the file
        SAVE                    = enum.auto()

        # User wants to save the file with a new name
        SAVE_AS                 = enum.auto()

        # User wants to undo last change
        UNDO                    = enum.auto()

        # User wants to clear selected block
        CLEAR_BLOCK             = enum.auto()

        # User wants to search file
        SEARCH                  = enum.auto()

        # User wants to find the next occurrance of the search term
        FIND_NEXT               = enum.auto()

        # User wants to find the previous occurrance of the search term
        FIND_PREV               = enum.auto()

        # User wants to view "about" window
        ABOUT                   = enum.auto()

    def __init__(self, parent, callbacks: Dict[Events, Callable[..., None]]):
        """Instantiate the class.
        
        Args:
            parent: 
                Parent tk class.
                
            callbacks:
                Dictionary of callbacks to call when an event from Events occurs
                
        """
        super().__init__(parent)

        if callbacks.keys() != set(self.Events):
            raise KeyError(f"Callbacks must contain all events in {set(self.Events)} ")

        self.callbacks = callbacks

        self.commands_require_file = {}

        # Create icons for menu items
        # Simple new icon
        self.icon_new = tk.PhotoImage(width=16, height=16)
        # Hvid fyld (dokumentets indre)
        self.icon_new.put("#FFFFFF", to=(3, 1, 11, 3))     # Toppen af dokumentet
        self.icon_new.put("#FFFFFF", to=(3, 3, 13, 14))    # Bunden af dokumentet
        # Hovedlinjer (sort)
        self.icon_new.put("#000000", to=(2, 0, 9, 1))      # Top kant
        self.icon_new.put("#000000", to=(2, 0, 3, 15))     # Venstre kant
        self.icon_new.put("#000000", to=(13, 4, 14, 14))   # Højre kant
        self.icon_new.put("#000000", to=(3, 14, 14, 15))   # Bund kant
        self.icon_new.put("#000000", to=(13, 4, 10, 5))    # Fold bund
        self.icon_new.put("#000000", to=(9, 0, 10, 5))     # Fold venstre
        self.icon_new.put("#000000", to=(10, 1, 11, 2))    # Diagonal 1
        self.icon_new.put("#000000", to=(11, 2, 12, 3))    # Diagonal 2
        self.icon_new.put("#000000", to=(12, 3, 13, 4))    # Diagonal 3
        
        # Simple open icon
        self.icon_open = tk.PhotoImage(width=16, height=16)
        # Mappe fyld (gul/beige for mappe-look)
        self.icon_open.put("#F0C050", to=(1, 2, 13, 5))     # Mappe top fyld
        self.icon_open.put("#E8B840", to=(3, 5, 14, 9))     # Åbning fyld (lidt mørkere)
        self.icon_open.put("#F0C050", to=(2, 9, 13, 14))    # Mappe bund fyld
        # Highlight (lysere kant for 3D effekt)
        self.icon_open.put("#F8D878", to=(1, 1, 2, 14))     # Venstre indre highlight
        self.icon_open.put("#F8D878", to=(2, 1, 6, 2))      # Tab indre highlight
        # Hovedlinjer (sort)
        self.icon_open.put("#000000", to=(1, 0, 6, 1))      # Tab top
        self.icon_open.put("#000000", to=(0, 1, 1, 14))     # Venstre kant
        self.icon_open.put("#000000", to=(6, 1, 7, 2))      # Tab højre side
        self.icon_open.put("#000000", to=(7, 2, 13, 3))     # Top kant højre
        self.icon_open.put("#000000", to=(13, 3, 14, 4))    # Højre top hjørne
        self.icon_open.put("#000000", to=(3, 4, 14, 5))     # Åbning top kant
        self.icon_open.put("#000000", to=(14, 5, 15, 9))    # Åbning højre kant
        self.icon_open.put("#000000", to=(13, 9, 14, 14))   # Højre kant bund
        self.icon_open.put("#000000", to=(1, 14, 13, 15))   # Bund kant
        self.icon_open.put("#000000", to=(1, 9, 2, 14))     # Venstre kant bund
        self.icon_open.put("#000000", to=(2, 5, 3, 9))      # Indre venstre kant

        # Simple save icon
        self.icon_save = tk.PhotoImage(width=16, height=16)
        # Diskette fyld (blå)
        self.icon_save.put("#4040A0", to=(2, 2, 12, 3))     # Diskette krop
        self.icon_save.put("#4040A0", to=(2, 3, 13, 13))     # Diskette krop
        # Label fyld (hvid)
        self.icon_save.put("#FFFFFF", to=(4, 8, 11, 13))    # Label fyld
        # Hovedlinjer (sort) - ydre kant
        self.icon_save.put("#000000", to=(1, 1, 11, 2))     # Top kant
        self.icon_save.put("#000000", to=(1, 2, 2, 14))     # Venstre kant
        self.icon_save.put("#000000", to=(13, 4, 14, 14))   # Højre kant
        self.icon_save.put("#000000", to=(2, 13, 14, 14))   # Bund kant
        # Diagonal hjørne (top højre)
        self.icon_save.put("#000000", to=(10, 1, 11, 2))    # Diagonal 1
        self.icon_save.put("#000000", to=(11, 2, 12, 3))    # Diagonal 2
        self.icon_save.put("#000000", to=(12, 3, 13, 4))    # Diagonal 3
        # Label område (bund)
        self.icon_save.put("#000000", to=(3, 7, 12, 8))     # Label top kant
        self.icon_save.put("#000000", to=(3, 8, 4, 13))     # Label venstre kant
        self.icon_save.put("#000000", to=(11, 8, 12, 13))   # Label højre kant
        # Metal shutter (top)
        self.icon_save.put("#000000", to=(4, 1, 5, 4))      # Shutter venstre
        self.icon_save.put("#000000", to=(9, 1, 10, 4))     # Shutter højre
        self.icon_save.put("#000000", to=(4, 4, 10, 5))     # Shutter bund
        # Metal shutter fyld (sølv)
        self.icon_save.put("#C0C0C0", to=(5, 2, 9, 4))      # Shutter fyld
        self.icon_save.put("#A0A0A0", to=(7, 2, 8, 4))      # Shutter sliding hole
        
        def add_command(menu, requires_file: bool, **kwargs) -> None:
            self.commands_require_file[(menu, kwargs['label'])] = requires_file
            menu.add_command(**kwargs)

        filemenu = tk.Menu(self, tearoff=0)
        add_command(filemenu, False, label = "New...",
                    command = lambda: self.callbacks[self.Events.NEW](None), accelerator = "Ctrl+N",
                    image = self.icon_new, compound = tk.LEFT)
        add_command(filemenu, False, label = "Open...",
                    command = lambda: self.callbacks[self.Events.OPEN](None), accelerator = "Ctrl+O",
                    image = self.icon_open, compound = tk.LEFT)
        add_command(filemenu, True, label = "Save",
                    command = lambda: self.callbacks[self.Events.SAVE](None), accelerator = "Ctrl+S",
                    image = self.icon_save, compound = tk.LEFT)
        add_command(filemenu, True, label = "Save As...",
                    command = lambda: self.callbacks[self.Events.SAVE_AS](None), accelerator = "Ctrl+Shift+S")
        filemenu.add_separator()
        add_command(filemenu, False, label = "Exit",
                    command = parent.quit, accelerator = "Alt+F4")
        self.add_cascade(label = "File", menu = filemenu)

        editmenu = tk.Menu(self, tearoff = 0)
        add_command(editmenu, True, label = "Undo",
                    command = lambda: self.callbacks[self.Events.UNDO](None), accelerator = "Ctrl+Z")
        editmenu.add_separator()
        # Clear Block should NOT be in commands_require_file, it has its own enable/disable logic
        editmenu.add_command(label = "Clear Block",
                             command = lambda: self.callbacks[self.Events.CLEAR_BLOCK](None),
                             accelerator = "Delete")
        self.add_cascade(label = "Edit", menu = editmenu)

        # Store reference to edit menu and Clear Block index for enabling/disabling
        self.editmenu = editmenu
        self.clear_block_index = 2  # Index of Clear Block in Edit menu (after separator)

        searchmenu = tk.Menu(self, tearoff = 0)
        add_command(searchmenu, True, label = "Find...", 
                    command = lambda: self.callbacks[self.Events.SEARCH](None), accelerator = "Ctrl+F")
        add_command(searchmenu, True, label = "Find Next", 
                    command = lambda: self.callbacks[self.Events.FIND_NEXT](None), accelerator = "F3")
        add_command(searchmenu, True, label = "Find Previous", 
                    command = lambda: self.callbacks[self.Events.FIND_PREV](None), accelerator = "Shift+F3")
        searchmenu.add_separator()
        add_command(searchmenu, True, label = "Go to...", 
                    command = lambda: self.callbacks[self.Events.GOTO](None), accelerator = "Ctrl+G")
        self.add_cascade(label = "Search", menu = searchmenu)
        
        viewmenu = tk.Menu(self, tearoff = 0)
        add_command(viewmenu, True, label = "Refresh", 
                    command = lambda: self.callbacks[self.Events.REFRESH](None), accelerator = "F5")

        helpmenu = tk.Menu(self, tearoff = 0)
        add_command(helpmenu, False, label = "About...", command = self.show_about)
        self.add_cascade(label = "Help", menu = helpmenu)

        self.toggle_loaded_file_commands(enable = False)

    def show_about(self) -> None:
        """Show the "About" window."""
        self.callbacks[self.Events.ABOUT]()

    def toggle_loaded_file_commands(self, enable: bool) -> None:
        """Enables/disables menu options which require an open file."""
        target = tk.NORMAL if enable else tk.DISABLED
        for (menu, label), requires_file in self.commands_require_file.items():
            if requires_file:
                menu.entryconfigure(label, state = target)

    def update_clear_block_state(self, has_selection: bool) -> None:
        """Enable or disable the Clear Block menu item based on selection state.

        Args:
            has_selection: True if there is a selection, False otherwise.
        """
        state = tk.NORMAL if has_selection else tk.DISABLED
        self.editmenu.entryconfigure(self.clear_block_index, state=state)

class HexAreaMenu(BaseHexAreaMenu):
    class Events(enum.Enum):
        """Events that can be triggered by the menu."""
        
        # Show cross-reference for current byte
        GET_XREF = enum.auto()

    def __init__(self, parent, callbacks: Dict[Events, Callable[..., None]]):
        """Instantiate the class.
        
        Args:
            parent: 
                Parent tk class.
                
            callbacks:
                Dictionary of callbacks to call when an event from Events occurs
                
        """
        super().__init__(parent)

        self.parent = parent

        self.menu = tk.Menu(self.parent, tearoff = 0)

        if callbacks.keys() != set(self.Events):
            raise KeyError(f"Callbacks must contain all events in {set(self.Events)} ")
        self.callbacks = callbacks

        self.menu.add_command(label = "Show X-Ref", 
                              command = lambda: self.callbacks[self.Events.GET_XREF](self._current_event))

    def show(self, event) -> None:
        """Show the menu."""
        self._current_event = event
        super().show(event)
