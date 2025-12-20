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
import struct
import datetime

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

        self.textbox_header_decoded = tk.Text(self.top_frame, height = 1, width = 25, padx = 10, wrap = tk.NONE, bd = 0)
        self.textbox_header_decoded.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.textbox_header_decoded.tag_configure("color", foreground="blue")
        self.textbox_header_decoded.insert(tk.END, " Decoded", "color")

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

        # Decoded section - fixed panel showing two-column list format
        # Create a frame for the decoded section (fixed, doesn't scroll)
        parent_bg = parent.cget('bg')
        decoded_panel_frame = tk.Frame(self.main_frame, bg=parent_bg)
        decoded_panel_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        
        # Endianness toggle button frame
        endian_frame = tk.Frame(decoded_panel_frame, bg=parent_bg)
        endian_frame.pack(fill=tk.X, padx=5, pady=2)
        
        
        tk.Label(endian_frame, text="Endian:", bg=parent_bg).pack(side=tk.LEFT)
        self.endian_var = tk.StringVar(value='LE')
        self.endian_button = tk.Button(endian_frame, textvariable=self.endian_var, width=4,
                                       command=self._toggle_endian)
        self.endian_button.pack(side=tk.LEFT, padx=2)
        
        self.textbox_decoded = tk.Text(decoded_panel_frame, width = 25, height=20, padx = 10, wrap = tk.NONE, relief=tk.SUNKEN)
        self.textbox_decoded.pack(fill=tk.BOTH, expand=True)
        self.textbox_decoded.tag_config("label", foreground="gray")
        self.textbox_decoded.tag_config("value", foreground="white")
        self.textbox_decoded.config(state=tk.DISABLED)  # Read-only
        
        # Store reference to file buffer for decoding
        self.file_buffer = None
        self.use_little_endian = True  # Default to little endian

        self.textboxes = [self.textbox_address, self.textbox_hex, self.textbox_ascii]
        self.textboxes_without_selection = [self.textbox_header_address, self.textbox_header_hex, self.textbox_header_ascii, self.textbox_header_decoded, self.textbox_address]

        self.scrollbar_frame = ttk.Frame(parent)
        self.scrollbar = tk.Scrollbar(self.scrollbar_frame)
        #self.scrollbar = tk.Scrollbar(self.main_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand = False)

        # Change the settings to make the scrolling work
        self.scrollbar['command'] = self._on_scrollbar
        for textbox in self.textboxes:
            textbox['yscrollcommand'] = self._on_textscroll
        
        # Bind cursor movement events to update decoded section
        self.textbox_hex.bind("<KeyRelease>", self._on_cursor_move)
        self.textbox_hex.bind("<Button-1>", self._on_cursor_move)
        self.textbox_ascii.bind("<KeyRelease>", self._on_cursor_move)
        self.textbox_ascii.bind("<Button-1>", self._on_cursor_move)

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

        self.textbox_hex.bind("<<Selection>>", self._on_hex_selection)
        self.textbox_ascii.bind("<<Selection>>", self._on_ascii_selection)

        # Bind modification events
        self.textbox_hex.bind("<Key>", self._on_hex_key_press)
        self.textbox_hex.bind("<Left>", self._on_hex_left_arrow)
        self.textbox_hex.bind("<Right>", self._on_hex_right_arrow)
        self.textbox_ascii.bind("<Key>", self._on_ascii_key_press)

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
            
            # Update decoded section based on selection
            start_offset = ((ascii_start_line - 1) * self.BYTES_PER_ROW) + ascii_start_char
            end_offset = ((ascii_end_line - 1) * self.BYTES_PER_ROW) + ascii_end_char
            self._update_decoded_section(start_offset, end_offset)
        except Exception:
            # No selection, update based on cursor position
            self._update_decoded_section_from_cursor()
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
            
            start_byte_in_line = hex_start_char // self.REPR_CHARS_PER_BYTE_HEX
            start_offset = ((hex_start_line - 1) * self.BYTES_PER_ROW) + start_byte_in_line
            end_byte_in_line = ((hex_end_char - 1) // self.REPR_CHARS_PER_BYTE_HEX) + 1
            end_offset = ((hex_end_line - 1) * self.BYTES_PER_ROW) + end_byte_in_line
            self._update_decoded_section(start_offset, end_offset)
        except Exception:
            self._update_decoded_section_from_cursor()
        finally:
            # Update menu state
            self.root.update_clear_block_menu(has_selection)

    def _get_selection_range(self) -> tuple:
        """Get the byte offset range of current selection.

        Returns:
            Tuple of (start_offset, end_offset) or None if no selection.
        """
        try:
            # Try to get selection from hex view first
            hex_start_line, hex_start_char = map(int, self.textbox_hex.index(tk.SEL_FIRST).split("."))
            hex_end_line, hex_end_char = map(int, self.textbox_hex.index(tk.SEL_LAST).split("."))

            # Calculate byte offsets
            start_byte_in_line = hex_start_char // self.REPR_CHARS_PER_BYTE_HEX
            start_offset = ((hex_start_line - 1) * self.BYTES_PER_ROW) + start_byte_in_line

            # SEL_LAST is after the last selected char, so we need to adjust
            # Use same logic as _on_hex_selection for consistency
            end_byte_in_line = ((hex_end_char - 1) // self.REPR_CHARS_PER_BYTE_HEX) + 1
            end_offset = ((hex_end_line - 1) * self.BYTES_PER_ROW) + end_byte_in_line

            return (start_offset, end_offset)
        except tk.TclError:
            # No selection in hex view, try ASCII view
            try:
                ascii_start_line, ascii_start_char = map(int, self.textbox_ascii.index(tk.SEL_FIRST).split("."))
                ascii_end_line, ascii_end_char = map(int, self.textbox_ascii.index(tk.SEL_LAST).split("."))

                start_offset = ((ascii_start_line - 1) * self.BYTES_PER_ROW) + ascii_start_char
                end_offset = ((ascii_end_line - 1) * self.BYTES_PER_ROW) + ascii_end_char

                return (start_offset, end_offset)
            except tk.TclError:
                return None

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
                    # Update decoded section
                    self._update_decoded_section(offset)

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
                    self.textbox_hex.delete(hex_pos_start, hex_pos_end)
                    self.textbox_hex.insert(hex_pos_start, hex_str)
                    self._update_decoded_section(offset)

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
        self.textbox_decoded.config(state = tk.NORMAL)
        self.textbox_decoded.delete('1.0', tk.END)
        self.textbox_decoded.config(state = tk.DISABLED)
        self.file_buffer = None

        # Update menu state to reflect no selection
        self.root.update_clear_block_menu(False)

    @property
    def widget(self) -> tk.Frame:
        """Return the actual widget."""
        return self.main_frame

    def _toggle_endian(self) -> None:
        """Toggle between little endian and big endian."""
        self.use_little_endian = not self.use_little_endian
        self.endian_var.set('LE' if self.use_little_endian else 'BE')
        # Update decoded section with new endianness
        try:
            cursor_pos = self.textbox_hex.index(tk.INSERT)
            line, col = map(int, cursor_pos.split("."))
            byte_in_line = col // self.REPR_CHARS_PER_BYTE_HEX
            offset = ((line - 1) * self.BYTES_PER_ROW) + byte_in_line
            self._update_decoded_section(offset)
        except:
            self._update_decoded_section_from_cursor()
    
    def _decode_bytes_at_offset(self, offset: int, max_bytes: int = 16) -> Dict[str, str]:
        """Decode bytes at a specific offset into various formats.
        
        Args:
            offset: Byte offset in the file buffer
            max_bytes: Maximum number of bytes to use for decoding
            
        Returns:
            Dictionary mapping format names to decoded values
        """
        if self.file_buffer is None or offset < 0 or offset >= len(self.file_buffer):
            return {}
        
        decoded = {}
        available_bytes = min(max_bytes, len(self.file_buffer) - offset)
        chunk = bytes(self.file_buffer[offset:offset + available_bytes])
        endian = '<' if self.use_little_endian else '>'
        
        # Binary (8 bit)
        if available_bytes >= 1:
            decoded['binary'] = format(chunk[0], '08b')
        
        # uint8_t / int8_t
        if available_bytes >= 1:
            decoded['uint8_t'] = str(chunk[0])
            decoded['int8_t'] = str(struct.unpack('b', chunk[0:1])[0])
        
        # uint16_t / int16_t
        if available_bytes >= 2:
            try:
                decoded['uint16_t'] = str(struct.unpack(f'{endian}H', chunk[0:2])[0])
                decoded['int16_t'] = str(struct.unpack(f'{endian}h', chunk[0:2])[0])
            except:
                pass
        
        # uint24_t / int24_t (3 bytes)
        if available_bytes >= 3:
            try:
                if self.use_little_endian:
                    u24_bytes = chunk[0:3] + b'\x00'
                    decoded['uint24_t'] = str(struct.unpack('<I', u24_bytes)[0])
                    i24_val = struct.unpack('<i', u24_bytes)[0]
                    if i24_val > 0x7FFFFF:
                        i24_val -= 0x1000000
                    decoded['int24_t'] = str(i24_val)
                else:
                    u24_bytes = b'\x00' + chunk[0:3]
                    decoded['uint24_t'] = str(struct.unpack('>I', u24_bytes)[0])
                    i24_val = struct.unpack('>i', u24_bytes)[0]
                    if i24_val > 0x7FFFFF:
                        i24_val -= 0x1000000
                    decoded['int24_t'] = str(i24_val)
            except:
                pass
        
        # uint32_t / int32_t
        if available_bytes >= 4:
            try:
                decoded['uint32_t'] = str(struct.unpack(f'{endian}I', chunk[0:4])[0])
                decoded['int32_t'] = str(struct.unpack(f'{endian}i', chunk[0:4])[0])
            except:
                pass
        
        # uint48_t / int48_t (6 bytes)
        if available_bytes >= 6:
            try:
                if self.use_little_endian:
                    u48_bytes = chunk[0:6] + b'\x00\x00'
                    decoded['uint48_t'] = str(struct.unpack('<Q', u48_bytes)[0])
                    i48_val = struct.unpack('<q', u48_bytes)[0]
                    if i48_val > 0x7FFFFFFFFFFF:
                        i48_val -= 0x1000000000000
                    decoded['int48_t'] = str(i48_val)
                else:
                    u48_bytes = b'\x00\x00' + chunk[0:6]
                    decoded['uint48_t'] = str(struct.unpack('>Q', u48_bytes)[0])
                    i48_val = struct.unpack('>q', u48_bytes)[0]
                    if i48_val > 0x7FFFFFFFFFFF:
                        i48_val -= 0x1000000000000
                    decoded['int48_t'] = str(i48_val)
            except:
                pass
        
        # uint64_t / int64_t
        if available_bytes >= 8:
            try:
                decoded['uint64_t'] = str(struct.unpack(f'{endian}Q', chunk[0:8])[0])
                decoded['int64_t'] = str(struct.unpack(f'{endian}q', chunk[0:8])[0])
            except:
                pass
        
        # half float (16 bit)
        if available_bytes >= 2:
            try:
                # Python doesn't have native half float, approximate using struct
                u16 = struct.unpack(f'{endian}H', chunk[0:2])[0]
                # Convert to float approximation
                sign = (u16 >> 15) & 0x1
                exp = (u16 >> 10) & 0x1F
                mantissa = u16 & 0x3FF
                if exp == 0:
                    val = mantissa / 1024.0 * (2.0 ** -14)
                elif exp == 31:
                    val = float('inf') if mantissa == 0 else float('nan')
                else:
                    val = (1.0 + mantissa / 1024.0) * (2.0 ** (exp - 15))
                if sign:
                    val = -val
                if val == val:  # Check for NaN
                    decoded['half_float'] = f"{val:.6g}"
            except:
                pass
        
        # float (32 bit)
        if available_bytes >= 4:
            try:
                f32 = struct.unpack(f'{endian}f', chunk[0:4])[0]
                if f32 == f32:  # Check for NaN
                    decoded['float'] = f"{f32:.6g}"
            except:
                pass
        
        # double (64 bit)
        if available_bytes >= 8:
            try:
                f64 = struct.unpack(f'{endian}d', chunk[0:8])[0]
                if f64 == f64:  # Check for NaN
                    decoded['double'] = f"{f64:.10g}"
            except:
                pass
        
        # long double (128 bit) - approximate as double precision
        if available_bytes >= 16:
            try:
                # Most systems use 80-bit or 64-bit for long double, approximate
                f64 = struct.unpack(f'{endian}d', chunk[0:8])[0]
                if f64 == f64:
                    decoded['long_double'] = f"{f64:.10g}"
            except:
                pass
        
        # Signed/Unsigned LEB128
        if available_bytes >= 1:
            try:
                # Unsigned LEB128
                result = 0
                shift = 0
                for i in range(min(10, available_bytes)):
                    byte = chunk[i]
                    result |= (byte & 0x7F) << shift
                    if (byte & 0x80) == 0:
                        decoded['uleb128'] = str(result)
                        break
                    shift += 7
                
                # Signed LEB128
                result = 0
                shift = 0
                for i in range(min(10, available_bytes)):
                    byte = chunk[i]
                    result |= (byte & 0x7F) << shift
                    if (byte & 0x80) == 0:
                        if byte & 0x40:
                            result |= -((1 << shift) << 7)
                        decoded['sleb128'] = str(result)
                        break
                    shift += 7
            except:
                pass
        
        # bool
        if available_bytes >= 1:
            decoded['bool'] = 'true' if chunk[0] != 0 else 'false'
        
        # ASCII Character
        if available_bytes >= 1:
            char = chunk[0]
            if 32 <= char <= 126:
                decoded['ascii_char'] = f"'{chr(char)}'"
            else:
                decoded['ascii_char'] = f"\\x{char:02x}"
        
        # Wide Character (UTF-16)
        if available_bytes >= 2:
            try:
                wchar = struct.unpack(f'{endian}H', chunk[0:2])[0]
                if 32 <= wchar <= 126 or wchar > 127:
                    try:
                        decoded['wide_char'] = f"'{chr(wchar)}'"
                    except:
                        decoded['wide_char'] = f"U+{wchar:04X}"
                else:
                    decoded['wide_char'] = f"U+{wchar:04X}"
            except:
                pass
        
        # UTF-8 code point
        if available_bytes >= 1:
            try:
                if chunk[0] < 0x80:
                    decoded['utf8'] = f"U+{chunk[0]:04X}"
                elif chunk[0] < 0xE0 and available_bytes >= 2:
                    code_point = ((chunk[0] & 0x1F) << 6) | (chunk[1] & 0x3F)
                    decoded['utf8'] = f"U+{code_point:04X}"
                elif chunk[0] < 0xF0 and available_bytes >= 3:
                    code_point = ((chunk[0] & 0x0F) << 12) | ((chunk[1] & 0x3F) << 6) | (chunk[2] & 0x3F)
                    decoded['utf8'] = f"U+{code_point:04X}"
                elif available_bytes >= 4:
                    code_point = ((chunk[0] & 0x07) << 18) | ((chunk[1] & 0x3F) << 12) | ((chunk[2] & 0x3F) << 6) | (chunk[3] & 0x3F)
                    decoded['utf8'] = f"U+{code_point:04X}"
            except:
                pass
        
        # String (null-terminated ASCII)
        if available_bytes >= 1:
            try:
                end_idx = chunk.find(0)
                if end_idx > 0:
                    decoded['string'] = chunk[0:end_idx].decode('ascii', errors='replace')
                elif chunk[0] >= 32 and chunk[0] <= 126:
                    # Show first few chars if no null terminator
                    decoded['string'] = chunk[0:min(20, available_bytes)].decode('ascii', errors='replace')
            except:
                pass
        
        # Wide String (null-terminated UTF-16)
        if available_bytes >= 2:
            try:
                null_pos = -1
                for i in range(0, available_bytes - 1, 2):
                    if struct.unpack(f'{endian}H', chunk[i:i+2])[0] == 0:
                        null_pos = i
                        break
                if null_pos > 0:
                    decoded['wide_string'] = chunk[0:null_pos].decode('utf-16-le' if self.use_little_endian else 'utf-16-be', errors='replace')
            except:
                pass
        
        # time_t (Unix timestamp)
        if available_bytes >= 4:
            try:
                timestamp = struct.unpack(f'{endian}i', chunk[0:4])[0]
                if 0 <= timestamp <= 2147483647:  # Valid range
                    dt = datetime.datetime.fromtimestamp(timestamp)
                    decoded['time_t'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # DOS Date
        if available_bytes >= 2:
            try:
                dos_date = struct.unpack(f'{endian}H', chunk[0:2])[0]
                day = dos_date & 0x1F
                month = (dos_date >> 5) & 0x0F
                year = 1980 + ((dos_date >> 9) & 0x7F)
                if 1 <= day <= 31 and 1 <= month <= 12:
                    decoded['dos_date'] = f"{year:04d}-{month:02d}-{day:02d}"
            except:
                pass
        
        # DOS Time
        if available_bytes >= 2:
            try:
                dos_time = struct.unpack(f'{endian}H', chunk[0:2])[0]
                seconds = (dos_time & 0x1F) * 2
                minutes = (dos_time >> 5) & 0x3F
                hours = (dos_time >> 11) & 0x1F
                if hours < 24 and minutes < 60 and seconds < 60:
                    decoded['dos_time'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            except:
                pass
        
        return decoded
    
    def _update_decoded_section(self, start_offset: int, end_offset: int = None) -> None:
        """Update the decoded section based on selected byte range.
        
        Args:
            start_offset: Starting byte offset
            end_offset: Ending byte offset (if None, uses start_offset)
        """
        if end_offset is None:
            end_offset = start_offset
        
        # Use start_offset for decoding (show values starting from selection start)
        decoded = self._decode_bytes_at_offset(start_offset)
        format_labels = [
            ('binary', 'Binary (8 bit)'),
            ('uint8_t', 'uint8_t'),
            ('int8_t', 'int8_t'),
            ('uint16_t', 'uint16_t'),
            ('int16_t', 'int16_t'),
            ('uint24_t', 'uint24_t'),
            ('int24_t', 'int24_t'),
            ('uint32_t', 'uint32_t'),
            ('int32_t', 'int32_t'),
            ('uint48_t', 'uint48_t'),
            ('int48_t', 'int48_t'),
            ('uint64_t', 'uint64_t'),
            ('int64_t', 'int64_t'),
            ('half_float', 'half float (16 bit)'),
            ('float', 'float (32 bit)'),
            ('double', 'double (64 bit)'),
            ('long_double', 'long double (128 bit)'),
            ('sleb128', 'Signed LEB128'),
            ('uleb128', 'Unsigned LEB128'),
            ('bool', 'bool'),
            ('ascii_char', 'ASCII Character'),
            ('wide_char', 'Wide Character'),
            ('utf8', 'UTF-8 code point'),
            ('string', 'String'),
            ('wide_string', 'Wide String'),
            ('time_t', 'time_t'),
            ('dos_date', 'DOS Date'),
            ('dos_time', 'DOS Time'),
        ]
        
        self.textbox_decoded.config(state=tk.NORMAL)
        self.textbox_decoded.delete('1.0', tk.END)
        
        for fmt_key, fmt_label in format_labels:
            if fmt_key in decoded:
                # Format as: "uint8_t    : 123"
                label_text = f"{fmt_label:<20}: "
                value_text = decoded[fmt_key]
                self.textbox_decoded.insert(tk.END, label_text, "label")
                self.textbox_decoded.insert(tk.END, value_text + "\n", "value")
        
        self.textbox_decoded.config(state=tk.DISABLED)
    
    def _update_decoded_section_from_cursor(self) -> None:
        """Update decoded section based on current cursor position."""
        try:
            # Try to get cursor from hex view first
            cursor_pos = self.textbox_hex.index(tk.INSERT)
            line, col = map(int, cursor_pos.split("."))
            byte_in_line = col // self.REPR_CHARS_PER_BYTE_HEX
            offset = ((line - 1) * self.BYTES_PER_ROW) + byte_in_line
            self._update_decoded_section(offset)
        except:
            try:
                # Try ASCII view
                cursor_pos = self.textbox_ascii.index(tk.INSERT)
                line, col = map(int, cursor_pos.split("."))
                offset = ((line - 1) * self.BYTES_PER_ROW) + col
                self._update_decoded_section(offset)
            except:
                # Clear decoded section if we can't determine position
                self.textbox_decoded.config(state=tk.NORMAL)
                self.textbox_decoded.delete('1.0', tk.END)
                self.textbox_decoded.config(state=tk.DISABLED)
    
    def _on_cursor_move(self, event) -> None:
        """Handle cursor movement to update decoded section."""
        # Small delay to ensure cursor position is updated
        self.root.after_idle(self._update_decoded_section_from_cursor)

    def populate_hex_view(self, byte_arr: bytes, done_cb: Callable[[], None]) -> None:
        """Populate the hex view with the content of the file.

        Args:
            byte_arr:
                The contents of the file, as a binary array.

            done_cb:
                A callback to call when the hex view is fully populated.

        """
        self.abort_load = False
        
        if isinstance(byte_arr, bytearray):
            self.file_buffer = byte_arr
        else:
            self.file_buffer = bytearray(byte_arr)

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
            self.root.after_idle(self._update_decoded_section_from_cursor)
            
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
        # Decoded textbox is read-only
        self.textbox_decoded.config(state = tk.DISABLED)

        # Set cursor to beginning of hex textbox and update decoded section
        if is_success:
            self.textbox_hex.mark_set(tk.INSERT, "1.0")
            self.textbox_hex.focus_set()
            self._update_decoded_section(0)

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
            self.textbox_decoded.config(state=tk.NORMAL)
            self.textbox_decoded.delete('1.0', tk.END)
            self.textbox_decoded.config(state=tk.DISABLED)
            return

        location = self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_HEX, offset)
        self.textbox_hex.see(location)
        self._update_decoded_section(offset)

        if highlight:
            self.textbox_hex.tag_add(TAG_GOTO, location, f"{location}+{(length * self.REPR_CHARS_PER_BYTE_HEX) - 1}c")

            # Also highlight in ASCII view
            location_ascii = self._offset_to_line_column(self.REPR_CHARS_PER_BYTE_ASCII, offset)
            self.textbox_ascii.tag_add(TAG_GOTO, location_ascii, f"{location_ascii}+{length}c")

        