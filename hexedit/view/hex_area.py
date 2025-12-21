"""The 'View' Module of the application: The HEX area.

This file contains the implementation for the HEX area:

+--------+--------------+-------+
| Offset | Hex          | ASCII |
+--------+--------------+-------+
| Offset | Hex          | ASCII |
| Area   | Area         | Area  |
|        |              |       |
+--------+--------------+-------+

The hex area displays the hex representation of the file.

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
import tkinter as tk
from tkinter import ttk

from typing import Dict, Callable, Optional
from io import StringIO

import queue

from .events import *
from .menus import *

from ..common import *
from ..utils import *

TAG_JUSTIFY_RIGHT = 'justify_right'
TAG_HIGHLIGHT = 'highlight'
TAG_SELECTION = 'selection'
TAG_GOTO = 'goto'
TAG_HIGHLIGHT_CUSTOM1 = 'highlight_c1'
TAG_HIGHLIGHT_CUSTOM2 = 'highlight_c2'
TAG_HIGHLIGHT_CUSTOM3 = 'highlight_c3'

TAGS = [
    TAG_JUSTIFY_RIGHT, TAG_HIGHLIGHT, TAG_SELECTION, TAG_GOTO, 
    TAG_HIGHLIGHT_CUSTOM1, TAG_HIGHLIGHT_CUSTOM2, TAG_HIGHLIGHT_CUSTOM3
]

class HexAreaView():
    """Implements the view for the hex area."""

    # Bytes to show per row in hex view
    ADDRESS_SIZE = 8
    BYTES_PER_ROW = 16
    REPR_CHARS_PER_BYTE_HEX = 3 # Two chars for hex representation + one space
    REPR_CHARS_PER_BYTE_ASCII = 1

    def __init__(self, root, parent, callbacks: Dict[Events, Callable[..., None]]):
        """Instantiate the class.
        
        Args:
            root:
                Root tk class.
                
            parent: 
                Parent tk class.
                            
            callbacks:
                Dictionary of callbacks to call when an event from Events occurs
                
        """
        self.root = root
        self.parent = parent
        self.callbacks = callbacks

        # Track custom selection state
        self.selection_start_byte = None  # Starting byte offset of selection
        self.selection_end_byte = None    # Ending byte offset of selection
        self.is_selecting = False         # Whether user is currently dragging to select

        # Create the widgets
        
        self.top_frame = tk.Frame(parent, bg = 'white')
        self.textbox_header_address = tk.Text(self.top_frame, height = 1, width = self.ADDRESS_SIZE, padx = 10, wrap = tk.NONE, bd = 0)
        self.textbox_header_address.pack(side = tk.LEFT, fill = tk.Y, expand = False)
        self.textbox_header_address.tag_configure(TAG_JUSTIFY_RIGHT, justify = tk.RIGHT)
        self.textbox_header_address.tag_configure("color", foreground="blue")
        self.textbox_header_address.insert(tk.END, " Offset", "color")

        self.textbox_header_hex = tk.Text(self.top_frame, height = 1, width = (self.BYTES_PER_ROW * 3)-1, padx = 10, wrap = tk.NONE, bd = 0)
        self.textbox_header_hex.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.textbox_header_hex.tag_configure("color", foreground="blue")
        self.textbox_header_hex.insert(tk.END, " 0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F", "color")

        self.textbox_header_ascii = tk.Text(self.top_frame, height = 1, width = self.BYTES_PER_ROW, padx = 10, wrap = tk.NONE, bd = 0)
        self.textbox_header_ascii.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.textbox_header_ascii.tag_configure("color", foreground="blue")
        self.textbox_header_ascii.insert(tk.END, "      ANSI ASCII", "color")

        self.main_frame = tk.Frame(parent, bg = 'white')
        self.textbox_address = tk.Text(self.main_frame, width = self.ADDRESS_SIZE, padx = 10, wrap = tk.NONE, bd = 0)
        self.textbox_address.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.textbox_address.tag_configure(TAG_JUSTIFY_RIGHT, justify = tk.RIGHT)
        self.textbox_address.tag_configure("color", foreground="blue")

        self.textbox_hex = tk.Text(self.main_frame, width = (self.BYTES_PER_ROW * 3)-1, padx = 10, wrap = tk.NONE, bd = 0)
        self.textbox_hex.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.textbox_hex.tag_config(TAG_HIGHLIGHT_CUSTOM1, background='khaki1')
        self.textbox_hex.tag_config(TAG_HIGHLIGHT_CUSTOM2, background='DarkSeaGreen1')
        self.textbox_hex.tag_config(TAG_HIGHLIGHT_CUSTOM3, background='thistle1')
        self.textbox_hex.tag_config(TAG_HIGHLIGHT, background='gold3') # Must be last of highlight tags
        self.textbox_hex.tag_config(TAG_GOTO, background='CornflowerBlue')
        self.textbox_hex.tag_config(TAG_SELECTION, background='lightgray')

        self.textbox_ascii = tk.Text(self.main_frame, width = self.BYTES_PER_ROW, padx = 10, wrap = tk.NONE, bd = 0)
        self.textbox_ascii.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.textbox_ascii.tag_config(TAG_HIGHLIGHT_CUSTOM1, background='khaki1')
        self.textbox_ascii.tag_config(TAG_HIGHLIGHT_CUSTOM2, background='DarkSeaGreen1')
        self.textbox_ascii.tag_config(TAG_HIGHLIGHT_CUSTOM3, background='thistle1')
        self.textbox_ascii.tag_config(TAG_HIGHLIGHT, background='gold3') # Must be last of highlight tags
        self.textbox_ascii.tag_config(TAG_GOTO, background='CornflowerBlue')
        self.textbox_ascii.tag_config(TAG_SELECTION, background='lightgray')

        self.textboxes = [self.textbox_address, self.textbox_hex, self.textbox_ascii]
        self.textboxes_without_selection = [self.textbox_header_address, self.textbox_header_hex, self.textbox_header_ascii, self.textbox_address]

        self.scrollbar_frame = ttk.Frame(parent)
        self.scrollbar = tk.Scrollbar(self.scrollbar_frame)
        #self.scrollbar = tk.Scrollbar(self.main_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand = False)

        # Change the settings to make the scrolling work
        self.scrollbar['command'] = self._on_scrollbar
        for textbox in self.textboxes:
            textbox['yscrollcommand'] = self._on_textscroll

        # Disable selection on some area
        for textbox in self.textboxes_without_selection:
            textbox.bindtags((str(textbox), "TEntry", "PostEvent", ".", "all"))
            textbox.bind_class("PostEvent", "<ButtonPress-1><Motion>", self._on_select_locked)

        self.top_frame.grid(row=0, sticky="NSEW")
        self.main_frame.grid(row=1, sticky="NSEW")
        self.scrollbar_frame.grid(row=0, column=1, rowspan=2, sticky="NSEW")

        # Configure parent grid to expand properly
        parent.grid_rowconfigure(0, weight=0)  # top_frame - fixed height
        parent.grid_rowconfigure(1, weight=1)  # main_frame - expands
        parent.grid_columnconfigure(0, weight=1)  # main content column - expands
        parent.grid_columnconfigure(1, weight=0)  # scrollbar column - fixed width

        # Disable default text selection and implement custom byte-aligned selection
        self.textbox_hex.bind("<<Selection>>", lambda e: "break")  # Disable default selection event
        self.textbox_ascii.bind("<<Selection>>", lambda e: "break")

        # Custom selection handling for byte-aligned selection in HEX
        self.textbox_hex.bind("<ButtonPress-1>", self._on_hex_mouse_down)
        self.textbox_hex.bind("<B1-Motion>", self._on_hex_mouse_drag)
        self.textbox_hex.bind("<ButtonRelease-1>", self._on_hex_mouse_up)

        # Custom selection handling for ASCII
        self.textbox_ascii.bind("<ButtonPress-1>", self._on_ascii_mouse_down)
        self.textbox_ascii.bind("<B1-Motion>", self._on_ascii_mouse_drag)
        self.textbox_ascii.bind("<ButtonRelease-1>", self._on_ascii_mouse_up)

        # Bind modification events
        self.textbox_hex.bind("<Key>", self._on_hex_key_press)
        self.textbox_hex.bind("<Left>", self._on_hex_left_arrow)
        self.textbox_hex.bind("<Right>", self._on_hex_right_arrow)
        self.textbox_hex.bind("<Up>", self._on_hex_up_arrow)
        self.textbox_hex.bind("<Down>", self._on_hex_down_arrow)
        self.textbox_ascii.bind("<Key>", self._on_ascii_key_press)
        self.textbox_ascii.bind("<Up>", self._on_ascii_up_arrow)
        self.textbox_ascii.bind("<Down>", self._on_ascii_down_arrow)

        # Bind Shift + arrow keys for selection in HEX view
        self.textbox_hex.bind("<Shift-Left>", self._on_hex_shift_left)
        self.textbox_hex.bind("<Shift-Right>", self._on_hex_shift_right)
        self.textbox_hex.bind("<Shift-Up>", self._on_hex_shift_up)
        self.textbox_hex.bind("<Shift-Down>", self._on_hex_shift_down)

        # Bind Shift + arrow keys for selection in ASCII view
        self.textbox_ascii.bind("<Shift-Left>", self._on_ascii_shift_left)
        self.textbox_ascii.bind("<Shift-Right>", self._on_ascii_shift_right)
        self.textbox_ascii.bind("<Shift-Up>", self._on_ascii_shift_up)
        self.textbox_ascii.bind("<Shift-Down>", self._on_ascii_shift_down)

        # Bind Ctrl+A for Select All in both views
        self.textbox_hex.bind("<Control-a>", self._on_select_all)
        self.textbox_ascii.bind("<Control-a>", self._on_select_all)

        # Bind Ctrl+C for Copy in both views
        self.textbox_hex.bind("<Control-c>", self._on_copy)
        self.textbox_ascii.bind("<Control-c>", self._on_copy)

        #self.hex_rightclick_menu = HexAreaMenu(self.parent, {
        #   HexAreaMenu.Events.GET_XREF: self._get_hex_xref
        #})

        self.textbox_hex.bind("<Button-3>", self._show_rightclick_hex_menu)

    def _on_scrollbar(self, *args) -> None:
        """Scroll all text widgets when the scrollbar is moved."""
        for textbox in self.textboxes:
            textbox.yview(*args)

    def _on_textscroll(self, *args) -> None:
        """Move the scrollbar and scroll text widgets when the mousewheel is moved on a text widget."""
        self.scrollbar.set(*args)
        self._on_scrollbar('moveto', args[0])

    def _on_select_locked(self, event = None) -> None:
        # Clear selected text
        event.widget.selection_clear()

    def _on_hex_mouse_down(self, event) -> str:
        """Handle mouse button down in hex view - prepare for potential selection."""
        # Get the position clicked
        index = self.textbox_hex.index(f"@{event.x},{event.y}")
        line, col = map(int, index.split("."))

        # Calculate byte offset from position (byte-aligned)
        # Check if clicked on the space after a byte (position 2 in each 3-char group)
        pos_in_group = col % self.REPR_CHARS_PER_BYTE_HEX
        if pos_in_group == 2:
            # Clicked on space - select the next byte
            byte_in_line = (col // self.REPR_CHARS_PER_BYTE_HEX) + 1
        else:
            # Clicked on hex digit - select this byte
            byte_in_line = col // self.REPR_CHARS_PER_BYTE_HEX

        byte_offset = ((line - 1) * self.BYTES_PER_ROW) + byte_in_line

        # Save the old selection state
        self.saved_selection_start = self.selection_start_byte
        self.saved_selection_end = self.selection_end_byte

        # Prepare for potential new selection (don't clear or select yet)
        self.selection_start_byte = byte_offset
        self.selection_end_byte = None  # Will be set when dragging starts
        self.is_selecting = True

        # Move cursor to the start of this byte
        cursor_col = byte_in_line * self.REPR_CHARS_PER_BYTE_HEX
        self.textbox_hex.mark_set(tk.INSERT, f"{line}.{cursor_col}")
        self.textbox_hex.focus_set()

        return "break"  # Prevent default behavior

    def _on_hex_mouse_drag(self, event) -> str:
        """Handle mouse drag in hex view - extend byte-aligned selection."""
        if not self.is_selecting:
            return "break"

        # Get current position
        index = self.textbox_hex.index(f"@{event.x},{event.y}")
        line, col = map(int, index.split("."))

        # Calculate byte offset (byte-aligned)
        # Check if dragging over the space after a byte (position 2 in each 3-char group)
        pos_in_group = col % self.REPR_CHARS_PER_BYTE_HEX
        if pos_in_group == 2:
            # On space - select the next byte
            byte_in_line = (col // self.REPR_CHARS_PER_BYTE_HEX) + 1
        else:
            # On hex digit - select this byte
            byte_in_line = col // self.REPR_CHARS_PER_BYTE_HEX

        byte_offset = ((line - 1) * self.BYTES_PER_ROW) + byte_in_line

        # Update selection end
        self.selection_end_byte = byte_offset

        # Re-render selection
        self._clear_custom_selection()
        self._render_custom_selection()

        return "break"

    def _on_hex_mouse_up(self, event) -> str:
        """Handle mouse button release in hex view - finish selection."""
        # If we didn't drag (selection_end_byte is still None), restore old selection
        if self.selection_end_byte is None:
            self.selection_start_byte = self.saved_selection_start
            self.selection_end_byte = self.saved_selection_end

        self.is_selecting = False
        return "break"

    def _on_ascii_mouse_down(self, event) -> str:
        """Handle mouse button down in ASCII view - prepare for potential selection."""
        # Get the position clicked
        index = self.textbox_ascii.index(f"@{event.x},{event.y}")
        line, col = map(int, index.split("."))

        # Calculate byte offset
        byte_offset = ((line - 1) * self.BYTES_PER_ROW) + col

        # Save the old selection state
        self.saved_selection_start = self.selection_start_byte
        self.saved_selection_end = self.selection_end_byte

        # Prepare for potential new selection (don't clear or select yet)
        self.selection_start_byte = byte_offset
        self.selection_end_byte = None  # Will be set when dragging starts
        self.is_selecting = True

        # Move cursor
        self.textbox_ascii.mark_set(tk.INSERT, f"{line}.{col}")
        self.textbox_ascii.focus_set()

        return "break"

    def _on_ascii_mouse_drag(self, event) -> str:
        """Handle mouse drag in ASCII view - extend selection."""
        if not self.is_selecting:
            return "break"

        # Get current position
        index = self.textbox_ascii.index(f"@{event.x},{event.y}")
        line, col = map(int, index.split("."))

        # Calculate byte offset
        byte_offset = ((line - 1) * self.BYTES_PER_ROW) + col

        # Update selection end
        self.selection_end_byte = byte_offset

        # Re-render selection
        self._clear_custom_selection()
        self._render_custom_selection()

        return "break"

    def _on_ascii_mouse_up(self, event) -> str:
        """Handle mouse button release in ASCII view - finish selection."""
        # If we didn't drag (selection_end_byte is still None), restore old selection
        if self.selection_end_byte is None:
            self.selection_start_byte = self.saved_selection_start
            self.selection_end_byte = self.saved_selection_end

        self.is_selecting = False
        return "break"

    def _clear_custom_selection(self) -> None:
        """Clear custom selection highlighting."""
        self.textbox_hex.tag_remove(TAG_SELECTION, "1.0", tk.END)
        self.textbox_ascii.tag_remove(TAG_SELECTION, "1.0", tk.END)

    def _render_custom_selection(self) -> None:
        """Render custom byte-aligned selection."""
        if self.selection_start_byte is None or self.selection_end_byte is None:
            self.root.update_clear_block_menu(False)
            return

        # Ensure start < end
        start = min(self.selection_start_byte, self.selection_end_byte)
        end = max(self.selection_start_byte, self.selection_end_byte)

        # Calculate positions for highlighting
        start_line = (start // self.BYTES_PER_ROW) + 1
        start_col_in_line = start % self.BYTES_PER_ROW

        end_line = (end // self.BYTES_PER_ROW) + 1
        end_col_in_line = end % self.BYTES_PER_ROW

        # Highlight in HEX view (byte-aligned)
        hex_start_col = start_col_in_line * self.REPR_CHARS_PER_BYTE_HEX
        hex_end_col = (end_col_in_line * self.REPR_CHARS_PER_BYTE_HEX) + 2  # +2 for the two hex digits

        hex_start = f"{start_line}.{hex_start_col}"
        hex_end = f"{end_line}.{hex_end_col}"
        self.textbox_hex.tag_add(TAG_SELECTION, hex_start, hex_end)

        # Highlight in ASCII view
        ascii_start = f"{start_line}.{start_col_in_line}"
        ascii_end = f"{end_line}.{end_col_in_line + 1}"  # +1 because end is exclusive
        self.textbox_ascii.tag_add(TAG_SELECTION, ascii_start, ascii_end)

        # Update menu state
        has_selection = (start != end)
        self.root.update_clear_block_menu(has_selection)

    def select_all(self) -> None:
        """Select all bytes in the document."""
        if not hasattr(self, 'data') or len(self.data) == 0:
            return

        # Select from first byte to last byte
        self.selection_start_byte = 0
        self.selection_end_byte = len(self.data) - 1

        self._clear_custom_selection()
        self._render_custom_selection()

        # Set cursor to the beginning
        self.textbox_hex.mark_set(tk.INSERT, "1.0")
        self.textbox_hex.see("1.0")

    def _on_select_all(self, event) -> str:
        """Handle Ctrl+A event - select all bytes."""
        self.select_all()
        return "break"  # Prevent default behavior

    def _on_copy(self, event) -> str:
        """Handle Ctrl+C event - copy selection or all."""
        from .events import Events
        # Get selection range
        selection_range = self._get_selection_range()
        if selection_range:
            # Copy selected block
            start, end = selection_range
            self.callbacks[Events.COPY_SELECTION]((start, end))
        else:
            # Copy all data
            self.callbacks[Events.COPY_SELECTION]((0, None))
        return "break"  # Prevent default behavior

    def _get_current_byte_offset_hex(self) -> int:
        """Get the byte offset of current cursor position in hex view."""
        cursor_pos = self.textbox_hex.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))
        byte_in_line = col // self.REPR_CHARS_PER_BYTE_HEX
        return ((line - 1) * self.BYTES_PER_ROW) + byte_in_line

    def _get_current_byte_offset_ascii(self) -> int:
        """Get the byte offset of current cursor position in ASCII view."""
        cursor_pos = self.textbox_ascii.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))
        return ((line - 1) * self.BYTES_PER_ROW) + col

    def _on_hex_shift_left(self, event) -> str:
        """Handle Shift+Left in hex view - extend selection left by one byte."""
        current_byte = self._get_current_byte_offset_hex()

        # Start selection if not already selecting
        if self.selection_start_byte is None:
            self.selection_start_byte = current_byte
            self.selection_end_byte = current_byte

        # Move cursor left (skip spaces)
        cursor_pos = self.textbox_hex.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))
        pos_in_byte = col % self.REPR_CHARS_PER_BYTE_HEX

        if col > 0:
            if pos_in_byte == 0:
                new_col = col - 1
            else:
                new_col = col - 1
            self.textbox_hex.mark_set(tk.INSERT, f"{line}.{new_col}")

        # Update selection end to new byte position (after cursor moved)
        new_byte = self._get_current_byte_offset_hex()
        self.selection_end_byte = new_byte

        self._clear_custom_selection()
        self._render_custom_selection()
        return "break"

    def _on_hex_shift_right(self, event) -> str:
        """Handle Shift+Right in hex view - extend selection right by one byte."""
        current_byte = self._get_current_byte_offset_hex()

        # Start selection if not already selecting
        if self.selection_start_byte is None:
            self.selection_start_byte = current_byte
            self.selection_end_byte = current_byte

        # Move cursor right (skip spaces)
        cursor_pos = self.textbox_hex.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))
        pos_in_byte = col % self.REPR_CHARS_PER_BYTE_HEX

        if pos_in_byte == 1:
            new_col = col + 2  # Skip space
        else:
            new_col = col + 1

        self.textbox_hex.mark_set(tk.INSERT, f"{line}.{new_col}")

        # Update selection end to new byte position (after cursor moved)
        new_byte = self._get_current_byte_offset_hex()
        self.selection_end_byte = new_byte

        self._clear_custom_selection()
        self._render_custom_selection()
        return "break"

    def _on_hex_shift_up(self, event) -> str:
        """Handle Shift+Up in hex view - extend selection up by one row."""
        current_byte = self._get_current_byte_offset_hex()

        # Start selection if not already selecting
        if self.selection_start_byte is None:
            self.selection_start_byte = current_byte
            self.selection_end_byte = current_byte

        # Move cursor up
        cursor_pos = self.textbox_hex.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))

        if line > 1:
            self.textbox_hex.mark_set(tk.INSERT, f"{line - 1}.{col}")

        # Update selection end
        new_byte = max(0, current_byte - self.BYTES_PER_ROW)
        self.selection_end_byte = new_byte

        self._clear_custom_selection()
        self._render_custom_selection()
        return "break"

    def _on_hex_shift_down(self, event) -> str:
        """Handle Shift+Down in hex view - extend selection down by one row."""
        current_byte = self._get_current_byte_offset_hex()

        # Start selection if not already selecting
        if self.selection_start_byte is None:
            self.selection_start_byte = current_byte
            self.selection_end_byte = current_byte

        # Move cursor down
        cursor_pos = self.textbox_hex.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))

        self.textbox_hex.mark_set(tk.INSERT, f"{line + 1}.{col}")

        # Update selection end
        new_byte = current_byte + self.BYTES_PER_ROW
        self.selection_end_byte = new_byte

        self._clear_custom_selection()
        self._render_custom_selection()
        return "break"

    def _on_ascii_shift_left(self, event) -> str:
        """Handle Shift+Left in ASCII view - extend selection left by one byte."""
        current_byte = self._get_current_byte_offset_ascii()

        # Start selection if not already selecting
        if self.selection_start_byte is None:
            self.selection_start_byte = current_byte
            self.selection_end_byte = current_byte

        # Move cursor left
        cursor_pos = self.textbox_ascii.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))

        if col > 0:
            self.textbox_ascii.mark_set(tk.INSERT, f"{line}.{col - 1}")

        # Update selection end
        new_byte = max(0, current_byte - 1)
        self.selection_end_byte = new_byte

        self._clear_custom_selection()
        self._render_custom_selection()
        return "break"

    def _on_ascii_shift_right(self, event) -> str:
        """Handle Shift+Right in ASCII view - extend selection right by one byte."""
        current_byte = self._get_current_byte_offset_ascii()

        # Start selection if not already selecting
        if self.selection_start_byte is None:
            self.selection_start_byte = current_byte
            self.selection_end_byte = current_byte

        # Move cursor right
        cursor_pos = self.textbox_ascii.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))

        self.textbox_ascii.mark_set(tk.INSERT, f"{line}.{col + 1}")

        # Update selection end
        new_byte = current_byte + 1
        self.selection_end_byte = new_byte

        self._clear_custom_selection()
        self._render_custom_selection()
        return "break"

    def _on_ascii_shift_up(self, event) -> str:
        """Handle Shift+Up in ASCII view - extend selection up by one row."""
        current_byte = self._get_current_byte_offset_ascii()

        # Start selection if not already selecting
        if self.selection_start_byte is None:
            self.selection_start_byte = current_byte
            self.selection_end_byte = current_byte

        # Move cursor up
        cursor_pos = self.textbox_ascii.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))

        if line > 1:
            self.textbox_ascii.mark_set(tk.INSERT, f"{line - 1}.{col}")

        # Update selection end
        new_byte = max(0, current_byte - self.BYTES_PER_ROW)
        self.selection_end_byte = new_byte

        self._clear_custom_selection()
        self._render_custom_selection()
        return "break"

    def _on_ascii_shift_down(self, event) -> str:
        """Handle Shift+Down in ASCII view - extend selection down by one row."""
        current_byte = self._get_current_byte_offset_ascii()

        # Start selection if not already selecting
        if self.selection_start_byte is None:
            self.selection_start_byte = current_byte
            self.selection_end_byte = current_byte

        # Move cursor down
        cursor_pos = self.textbox_ascii.index(tk.INSERT)
        line, col = map(int, cursor_pos.split("."))

        self.textbox_ascii.mark_set(tk.INSERT, f"{line + 1}.{col}")

        # Update selection end
        new_byte = current_byte + self.BYTES_PER_ROW
        self.selection_end_byte = new_byte

        self._clear_custom_selection()
        self._render_custom_selection()
        return "break"

    def _on_ascii_selection(self, event) -> None:
        """Highlight HEX view upon selection of ASCII view."""
        self.textbox_ascii.tag_remove(TAG_SELECTION, "1.0", tk.END)
        self.textbox_hex.tag_remove(TAG_SELECTION, "1.0", tk.END)
        has_selection = False
        try:
            ascii_start_line, ascii_start_char = map(int, self.textbox_ascii.index(tk.SEL_FIRST).split("."))
            ascii_end_line,   ascii_end_char   = map(int, self.textbox_ascii.index(tk.SEL_LAST).split("."))
            hex_start = f"{ascii_start_line}.{ascii_start_char * self.REPR_CHARS_PER_BYTE_HEX}"
            hex_end   = f"{ascii_end_line}.{( (ascii_end_char - 1) * self.REPR_CHARS_PER_BYTE_HEX) + self.REPR_CHARS_PER_BYTE_HEX - 1}"
            self.textbox_hex.tag_add(TAG_SELECTION, hex_start, hex_end)
            has_selection = True
        except Exception:
            pass
        finally:
            # Update menu state
            self.root.update_clear_block_menu(has_selection)
            
    def _on_hex_selection(self, event) -> None:
        """Highlight ASCII view upon selection of HEX view."""
        self.textbox_ascii.tag_remove(TAG_SELECTION, "1.0", tk.END)
        self.textbox_hex.tag_remove(TAG_SELECTION, "1.0", tk.END)
        has_selection = False
        try:
            hex_start_line, hex_start_char = map(int, self.textbox_hex.index(tk.SEL_FIRST).split("."))
            hex_end_line,   hex_end_char   = map(int, self.textbox_hex.index(tk.SEL_LAST).split("."))
            ascii_start = f"{hex_start_line}.{hex_start_char // self.REPR_CHARS_PER_BYTE_HEX}"
            ascii_end   = f"{hex_end_line}.{( (hex_end_char - 1) // self.REPR_CHARS_PER_BYTE_HEX) + 1}"
            self.textbox_ascii.tag_add(TAG_SELECTION, ascii_start, ascii_end)
            has_selection = True
        except Exception:
            pass
        finally:
            # Update menu state
            self.root.update_clear_block_menu(has_selection)

    def _get_selection_range(self) -> tuple:
        """Get the byte offset range of current selection.

        Returns:
            Tuple of (start_offset, end_offset) or None if no selection.
        """
        # Use custom selection tracking
        if self.selection_start_byte is None or self.selection_end_byte is None:
            return None

        # Ensure start < end
        start = min(self.selection_start_byte, self.selection_end_byte)
        end = max(self.selection_start_byte, self.selection_end_byte)

        # Only return range if there's an actual selection (not just a click)
        if start == end:
            return None

        return (start, end + 1)  # +1 to make end exclusive for slicing

    def has_selection(self) -> bool:
        """Check if there is currently a selection.

        Returns:
            True if there is a selection, False otherwise.
        """
        return self._get_selection_range() is not None

    def _show_rightclick_hex_menu(self, event) -> None:
        """Show the Right-Click menu for the hex area.

        Args:
            event:
                A tkinter event containing the (x,y) coordinates
                of where the user right-clicked to get the X-Ref.
        """
        assert(self.textbox_hex.index(tk.CURRENT) == self.textbox_hex.index(f"@{event.x},{event.y}"))
        #self.hex_rightclick_menu.show(event)

    def _on_hex_left_arrow(self, event) -> str:
        """Handle left arrow key in hex view - skip spaces."""
        # Clear selection when using arrow keys without Shift
        self.selection_start_byte = None
        self.selection_end_byte = None
        self._clear_custom_selection()
        self.root.update_clear_block_menu(False)

        try:
            cursor_pos = self.textbox_hex.index(tk.INSERT)
            line, col = map(int, cursor_pos.split("."))

            # Calculate position within byte (0, 1, or 2 for space)
            pos_in_byte = col % self.REPR_CHARS_PER_BYTE_HEX

            if col > 0:
                if pos_in_byte == 0:
                    # At start of byte, move to end of previous byte (skip space)
                    self.textbox_hex.mark_set(tk.INSERT, f"{line}.{col - 1}")
                else:
                    # Within byte, just move left
                    self.textbox_hex.mark_set(tk.INSERT, f"{line}.{col - 1}")
                return "break"
        except Exception:
            pass
        return None

    def _on_hex_right_arrow(self, event) -> str:
        """Handle right arrow key in hex view - skip spaces."""
        # Clear selection when using arrow keys without Shift
        self.selection_start_byte = None
        self.selection_end_byte = None
        self._clear_custom_selection()
        self.root.update_clear_block_menu(False)

        try:
            cursor_pos = self.textbox_hex.index(tk.INSERT)
            line, col = map(int, cursor_pos.split("."))

            # Get line length to check bounds
            line_end = self.textbox_hex.index(f"{line}.end")
            line_end_col = int(line_end.split(".")[1])

            if col < line_end_col:
                # Calculate position within byte (0, 1, or 2 for space)
                pos_in_byte = col % self.REPR_CHARS_PER_BYTE_HEX

                if pos_in_byte == 1:
                    # At end of byte, skip space and move to next byte
                    self.textbox_hex.mark_set(tk.INSERT, f"{line}.{col + 2}")
                else:
                    # Otherwise just move right
                    self.textbox_hex.mark_set(tk.INSERT, f"{line}.{col + 1}")
                return "break"
        except Exception:
            pass
        return None

    def _on_hex_up_arrow(self, event) -> str:
        """Handle up arrow key in hex view - clear selection."""
        # Clear selection when using arrow keys without Shift
        self.selection_start_byte = None
        self.selection_end_byte = None
        self._clear_custom_selection()
        self.root.update_clear_block_menu(False)
        return None  # Let default behavior handle navigation

    def _on_hex_down_arrow(self, event) -> str:
        """Handle down arrow key in hex view - clear selection."""
        # Clear selection when using arrow keys without Shift
        self.selection_start_byte = None
        self.selection_end_byte = None
        self._clear_custom_selection()
        self.root.update_clear_block_menu(False)
        return None  # Let default behavior handle navigation

    def _on_ascii_up_arrow(self, event) -> str:
        """Handle up arrow key in ASCII view - clear selection."""
        # Clear selection when using arrow keys without Shift
        self.selection_start_byte = None
        self.selection_end_byte = None
        self._clear_custom_selection()
        self.root.update_clear_block_menu(False)
        return None  # Let default behavior handle navigation

    def _on_ascii_down_arrow(self, event) -> str:
        """Handle down arrow key in ASCII view - clear selection."""
        # Clear selection when using arrow keys without Shift
        self.selection_start_byte = None
        self.selection_end_byte = None
        self._clear_custom_selection()
        self.root.update_clear_block_menu(False)
        return None  # Let default behavior handle navigation

    def _on_hex_key_press(self, event) -> str:
        """Handle hex textbox key press with overwrite mode."""
        try:
            # Only handle hex characters and navigation
            char = event.char.upper()

            # Handle Delete key separately
            if event.keysym == 'Delete':
                from tkinter import messagebox

                # Check if there's a selection
                selection_range = self._get_selection_range()
                if selection_range:
                    # Block deletion
                    start_offset, end_offset = selection_range
                    if messagebox.askyesno("Delete Block", "Removing the current block will decrease the file size. Continue?"):
                        self.callbacks[Events.DELETE_BYTE]((start_offset, end_offset))
                else:
                    # Single byte deletion
                    cursor_pos = self.textbox_hex.index(tk.INSERT)
                    line, col = map(int, cursor_pos.split("."))
                    byte_in_line = col // self.REPR_CHARS_PER_BYTE_HEX
                    offset = ((line - 1) * self.BYTES_PER_ROW) + byte_in_line

                    if messagebox.askyesno("Delete Byte", "Removing the current byte will decrease the file size. Continue?"):
                        self.callbacks[Events.DELETE_BYTE](offset)
                return "break"

            # Allow navigation keys and backspace, and ignore F-keys and Control combinations
            if (event.keysym in ['Left', 'Right', 'Up', 'Down', 'Home', 'End', 'Prior', 'Next',
                                'BackSpace', 'Tab', 'F3', 'F5',
                                'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R',
                                'Win_L', 'Win_R', 'Super_L', 'Super_R', 'Caps_Lock', 'Num_Lock',
                                'Scroll_Lock', 'Escape', 'Insert', 'Pause', 'Print'] or
                event.keysym.startswith('F') or
                (event.state & 0x4)):  # Control key pressed
                return None

            # Only allow hex characters
            if char not in '0123456789ABCDEF':
                return "break"

            # Get current cursor position
            cursor_pos = self.textbox_hex.index(tk.INSERT)
            line, col = map(int, cursor_pos.split("."))

            # Calculate position within byte (0 or 1 for first or second hex digit)
            pos_in_byte = col % self.REPR_CHARS_PER_BYTE_HEX

            # If cursor is on a space, move to next byte
            if pos_in_byte == 2:
                col += 1
                pos_in_byte = 0
                cursor_pos = f"{line}.{col}"
                self.textbox_hex.mark_set(tk.INSERT, cursor_pos)

            # Calculate byte offset
            byte_in_line = col // self.REPR_CHARS_PER_BYTE_HEX
            offset = ((line - 1) * self.BYTES_PER_ROW) + byte_in_line

            # Get the current hex value for this byte
            start_col = byte_in_line * self.REPR_CHARS_PER_BYTE_HEX
            hex_pos_start = f"{line}.{start_col}"
            hex_pos_end = f"{line}.{start_col + 2}"
            current_hex = self.textbox_hex.get(hex_pos_start, hex_pos_end)

            # Build new hex value (overwrite at cursor position)
            if pos_in_byte == 0:
                new_hex = char + (current_hex[1] if len(current_hex) > 1 else '0')
            else:
                new_hex = (current_hex[0] if len(current_hex) > 0 else '0') + char

            # Delete old value and insert new
            self.textbox_hex.delete(hex_pos_start, hex_pos_end)
            self.textbox_hex.insert(hex_pos_start, new_hex)

            # Update buffer
            if Events.HEX_MODIFIED in self.callbacks:
                if self.callbacks[Events.HEX_MODIFIED](offset, new_hex):
                    # Update ASCII view
                    byte_val = int(new_hex, 16)
                    ascii_char = chr(byte_val) if 32 <= byte_val <= 127 else "."
                    ascii_pos = f"{line}.{byte_in_line}"

                    # Keep ASCII editable - just update the content
                    self.textbox_ascii.delete(ascii_pos, f"{ascii_pos}+1c")
                    self.textbox_ascii.insert(ascii_pos, ascii_char)

            # Move cursor to next position
            if pos_in_byte == 0:
                # Move to second hex digit
                self.textbox_hex.mark_set(tk.INSERT, f"{line}.{col + 1}")
            else:
                # Move to next byte (skip space)
                next_col = start_col + 3
                # Check if we need to go to next line
                if byte_in_line >= self.BYTES_PER_ROW - 1:
                    self.textbox_hex.mark_set(tk.INSERT, f"{line + 1}.0")
                else:
                    self.textbox_hex.mark_set(tk.INSERT, f"{line}.{next_col}")

            # Prevent default key behavior
            return "break"

        except Exception:
            return "break"

    def _on_ascii_key_press(self, event) -> str:
        """Handle ASCII textbox key press with overwrite mode."""
        try:
            # Get the character pressed
            char = event.char

            # Handle Delete key separately
            if event.keysym == 'Delete':
                from tkinter import messagebox

                # Check if there's a selection
                selection_range = self._get_selection_range()
                if selection_range:
                    # Block deletion
                    start_offset, end_offset = selection_range
                    if messagebox.askyesno("Delete Block", "Removing the current block will decrease the file size. Continue?"):
                        self.callbacks[Events.DELETE_BYTE]((start_offset, end_offset))
                else:
                    # Single byte deletion
                    cursor_pos = self.textbox_ascii.index(tk.INSERT)
                    line, col = map(int, cursor_pos.split("."))
                    offset = ((line - 1) * self.BYTES_PER_ROW) + col

                    if messagebox.askyesno("Delete Byte", "Removing the current byte will decrease the file size. Continue?"):
                        self.callbacks[Events.DELETE_BYTE](offset)
                return "break"

            # Allow navigation keys and ignore F-keys and Control combinations
            if (event.keysym in ['Left', 'Right', 'Up', 'Down', 'Home', 'End', 'Prior', 'Next',
                                'BackSpace', 'Tab', 'F3', 'F5',
                                'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R',
                                'Win_L', 'Win_R', 'Super_L', 'Super_R', 'Caps_Lock', 'Num_Lock',
                                'Scroll_Lock', 'Escape', 'Insert', 'Pause', 'Print'] or
                event.keysym.startswith('F') or
                (event.state & 0x4)):  # Control key pressed
                return None

            # Only allow printable characters
            if not char or len(char) != 1:
                return "break"

            # Get current cursor position
            cursor_pos = self.textbox_ascii.index(tk.INSERT)
            line, col = map(int, cursor_pos.split("."))

            # Calculate byte offset
            offset = ((line - 1) * self.BYTES_PER_ROW) + col

            # Check if we're within bounds
            if col >= self.BYTES_PER_ROW:
                return "break"

            # Overwrite the character at current position
            ascii_pos = f"{line}.{col}"
            self.textbox_ascii.delete(ascii_pos, f"{ascii_pos}+1c")
            self.textbox_ascii.insert(ascii_pos, char)

            # Update buffer
            if Events.ASCII_MODIFIED in self.callbacks:
                if self.callbacks[Events.ASCII_MODIFIED](offset, char):
                    # Update hex view
                    byte_val = ord(char)
                    hex_str = f"{byte_val:02X}"

                    start_col = col * self.REPR_CHARS_PER_BYTE_HEX
                    hex_pos_start = f"{line}.{start_col}"
                    hex_pos_end = f"{line}.{start_col + 2}"

                    # Keep hex editable - just update the content
                    self.textbox_hex.delete(hex_pos_start, hex_pos_end)
                    self.textbox_hex.insert(hex_pos_start, hex_str)

            # Move cursor to next position
            if col < self.BYTES_PER_ROW - 1:
                self.textbox_ascii.mark_set(tk.INSERT, f"{line}.{col + 1}")
            else:
                # Move to next line
                self.textbox_ascii.mark_set(tk.INSERT, f"{line + 1}.0")

            # Prevent default key behavior
            return "break"

        except Exception:
            return "break"
        

    def reset(self):
        """Reset the text widgets to the original state."""
        self.abort_load = True
        for textbox in self.textboxes:
            textbox.config(state = tk.NORMAL)
            textbox.delete('1.0', tk.END)
            for tag in TAGS:
                textbox.tag_remove(tag, "1.0", tk.END)

        # Clear custom selection state
        self.selection_start_byte = None
        self.selection_end_byte = None
        self.is_selecting = False

        # Clear data reference
        self.data = None

        # Update menu state to reflect no selection
        self.root.update_clear_block_menu(False)

    @property
    def widget(self) -> tk.Frame:
        """Return the actual widget."""
        return self.main_frame

    def populate_hex_view(self, byte_arr: bytes, done_cb: Callable[[], None]) -> None:
        """Populate the hex view with the content of the file.

        Args:
            byte_arr:
                The contents of the file, as a binary array.

            done_cb:
                A callback to call when the hex view is fully populated.

        """
        self.abort_load = False

        # Store the byte array so we can use it for select_all
        self.data = byte_arr

        self.hex_content_done_cb = done_cb
        self.hex_thread_queue = queue.Queue()
        start_deamon(function = self._create_hex_view_content, args = (byte_arr, self.hex_thread_queue))
        self.root.after(50, self._add_content_to_hex_view)

    def _create_hex_view_content(self, byte_arr: bytes, queue: queue.Queue) -> None:
        """Create the content to be insterted into the hex view and pass it to the given queue.

        This function runs is a separate thread, and feeds the queue with chunks of content to be 
        appended to the hex view.

        Args:
            byte_arr:
                The byte array to be formatted into the hex view.

            queue:
                The output queue to which the chunks of formatted text need to be sent to.
        
        """
        try:
            chars_per_byte = 2
            format_pad_len = 8 * chars_per_byte

            # Increased chunk size for faster loading (64KB instead of 4KB)
            chunk_size = 0x10000

            # Pre-create ASCII translation table for better performance
            ascii_chars = bytearray(range(256))
            for i in range(256):
                if i < 32 or i > 127:
                    ascii_chars[i] = ord('.')

            for i, chunk_external in enumerate(chunker(byte_arr, chunk_size)):
                if self.abort_load:
                    break

                # String concatenation is faster with StringIO
                textbox_hex_content = StringIO()
                textbox_ascii_content = StringIO()
                textbox_address_content = StringIO()
                base_addr = chunk_size * i

                for j, chunk_16b in enumerate(chunker(chunk_external, self.BYTES_PER_ROW)):

                    if self.abort_load:
                        break

                    hex_format = chunk_16b.hex(" ").upper()
                    textbox_hex_content.write(hex_format + "\n")

                    # Use translate for faster ASCII conversion
                    ascii_format = chunk_16b.translate(ascii_chars).decode('ascii')
                    textbox_ascii_content.write(ascii_format + "\n")

                    textbox_address_content.write(format(base_addr + (j * self.BYTES_PER_ROW), 'X').rjust(format_pad_len, '0') + "\n")

                queue.put((textbox_address_content, textbox_hex_content, textbox_ascii_content))

            queue.put(None)
        except Exception as e:
            queue.put(e)

    def _add_content_to_hex_view(self) -> None:
        """Listens to the hex content thread queue and appends content to the hex view.
        
        This function runs in the context of the View, reads formatted text from the content
        creation thread and appends it to the hex view.

        If needed, this function reschedules itself to run again.
        """
        
        try:
            queue_item = self.hex_thread_queue.get(block = False)

            if queue_item is None or self.abort_load: 
                self._cleanup_hex_content(is_success = not self.abort_load)
                return
            elif isinstance(queue_item, Exception):
                raise queue_item

            textbox_address_content, textbox_hex_content, textbox_ascii_content = queue_item

            self.textbox_hex.insert(tk.END, textbox_hex_content.getvalue())
            self.textbox_ascii.insert(tk.END, textbox_ascii_content.getvalue())
            self.textbox_address.insert(tk.END, textbox_address_content.getvalue(), "color")
            self.textbox_address.tag_add(TAG_JUSTIFY_RIGHT, 1.0, tk.END)
            self.root.after_idle(self._add_content_to_hex_view)
        except tk.TclError as e:
            self._cleanup_hex_content(is_success = False)
            if not self.abort_load:
                raise e
        except queue.Empty:
            self.root.after_idle(self._add_content_to_hex_view)
        except Exception as e:
            self._cleanup_hex_content(is_success = False)
            self.callbacks[Events.SHOW_ERROR](f"Error: {str(e)}")

    def _cleanup_hex_content(self, is_success: bool) -> None:
        # Remove trailing newline from all textboxes if present
        if is_success:
            # Remove last character if it's a newline
            for textbox in [self.textbox_address, self.textbox_hex, self.textbox_ascii]:
                content_end = textbox.index(tk.END)
                # tk.END is always one past the last character
                last_char_index = textbox.index(f"{tk.END}-1c")
                last_char = textbox.get(last_char_index, tk.END)
                if last_char == '\n':
                    textbox.delete(last_char_index, tk.END)

        self.textbox_address.config(state = tk.DISABLED)
        # Keep hex and ASCII textboxes editable
        self.textbox_hex.config(state = tk.NORMAL)
        self.textbox_ascii.config(state = tk.NORMAL)

        # Set cursor to beginning of hex textbox
        if is_success:
            self.textbox_hex.mark_set(tk.INSERT, "1.0")
            self.textbox_hex.focus_set()

        self.hex_content_done_cb(is_success)
        self.hex_content_done_cb = None
        self.hex_thread_queue = None

    @classmethod
    def _offset_to_line_column(cls, chars_per_byte: int, offset: int, adjust_column: int = 0) -> str:
        """Translate an offset in a text box to tkinter line.column notation.
        
        Args:
            chars_per_byte:
                Number of characters in the text box needed to represent a single byte.
            offset:
                Offset to translate from.
            adjust_column:
                Can be used to adjust the column value after the initial calculation.
        
        Returns:
            Offset in tkinter line.column notation.
        """
        line = (offset // cls.BYTES_PER_ROW) + 1 # Line is 1-based
        column = ((offset % cls.BYTES_PER_ROW) * chars_per_byte)
        return f"{line}.{column + adjust_column}"
    
    @staticmethod
    def _highlight_to_tag(highlight_type: HighlightType):
        """Mapping of highlighter to tag."""
        tag = {
            HighlightType.DEFAULT: TAG_HIGHLIGHT,
            HighlightType.CUSTOM1: TAG_HIGHLIGHT_CUSTOM1,    
            HighlightType.CUSTOM2: TAG_HIGHLIGHT_CUSTOM2,
            HighlightType.CUSTOM3: TAG_HIGHLIGHT_CUSTOM3    
        }.get(highlight_type)

        return tag

    def unmark_range(self, start_offset: int, end_offset: int, highlight_type: HighlightType = HighlightType.DEFAULT) -> None:
        """Unmarks the given range for the given highlighter."""
        tag = self._highlight_to_tag(highlight_type)

        self.textbox_hex.tag_remove(tag, 
            self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_HEX, start_offset) if start_offset is not None else "1.0", 
            self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_HEX, end_offset, -1) if end_offset is not None else tk.END)
        self.textbox_ascii.tag_remove(tag, 
            self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_ASCII, start_offset) if start_offset is not None else "1.0", 
            self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_ASCII, end_offset) if end_offset is not None else tk.END)


    def mark_range(self, start_offset: int, end_offset: int, mark: bool, highlight_type: HighlightType = HighlightType.DEFAULT) -> None:
        """Highlight a range between the given offsets, and optionally jump to it.
        
        Args:
            start_offset:
                Offset to highlight from (absolute index of byte in file)
            end_offset:
                Offset to highlight to (absolute index of byte in file)
            highlight_type:
                Type of highlight to use. Use HighlightType.DEFAULT for selection, 
                or HighlightType.CUSTOMx for user triggered custom highlights
        """

        tag = self._highlight_to_tag(highlight_type)

        if start_offset is not None and end_offset is not None:
            # Mark in hex view:
            self.textbox_hex.tag_add(tag, 
                                     self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_HEX, start_offset), 
                                     self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_HEX, end_offset, -1)) # Remove trailing space

            # Mark in ASCII view:
            self.textbox_ascii.tag_add(tag, 
                                       self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_ASCII, start_offset), 
                                       self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_ASCII, end_offset))

    def make_visible(self, offset: Optional[int], length: int = 1, highlight: bool = False) -> None:
        """Jump to a given offset in the HEX viewer, and optionally highlight it.

        Args:
            offset:
                The offset to jump to. If is None, will clear the highlight.
            length:
                Length of sequence to highlight, if selected.
            highlight:
                In addition, highlight the location.
        """
        self.textbox_hex.tag_remove(TAG_GOTO, "1.0", tk.END)
        self.textbox_ascii.tag_remove(TAG_GOTO, "1.0", tk.END)

        if offset is None:
            return

        # Validate offset is non-negative
        if offset < 0:
            return

        location = self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_HEX, offset)

        # Verify the location exists in the textbox before trying to see it
        try:
            self.textbox_hex.see(location)
        except tk.TclError:
            # Offset is out of bounds, silently return
            return

        if highlight:
            self.textbox_hex.tag_add(TAG_GOTO, location, f"{location}+{(length * self.REPR_CHARS_PER_BYTE_HEX) - 1}c")

            # Also highlight in ASCII view
            location_ascii = self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_ASCII, offset)
            self.textbox_ascii.tag_add(TAG_GOTO, location_ascii, f"{location_ascii}+{length}c")

        