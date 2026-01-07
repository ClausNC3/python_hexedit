"""The 'Controller' module, connecting between the 'View' and 'Model'.

The application module acts as the 'Controller' and is responsible for
connecting between the 'View' and the 'Model' in the MVC pattern.

It receives user-triggered events from the View via callbacks, translates
them to operations which need to be performed by the Model, and updates
the View when the operations are completed.

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
from pathlib import Path
from typing import Tuple, Union, Dict, Optional

import enum
import queue
import random

from . import view as v

from . import utils

from .common import *
from .utils import *
from .nand import get_config_by_name, extract_data_from_page, extract_ecc_from_page
from .ecc import (
    ECCType,
    calculate_bch_ecc, verify_bch_ecc, correct_bch_errors,
    calculate_hamming_ecc, verify_hamming_ecc, correct_hamming_errors
)

class SearchContext:
    """Context for searching in binary data."""

    def __init__(self, data: bytes, term: bytes):
        """Initialize search context.

        Args:
            data: Binary data to search in
            term: Search term as bytes
        """
        self.data = data
        self.term = term
        self.last_position = 0

    def find_next(self, reverse: bool = False) -> int:
        """Find next occurrence of the search term.

        Args:
            reverse: Search backwards

        Returns:
            Offset of the match, or -1 if not found
        """
        if reverse:
            # Search backwards from last position
            pos = self.data.rfind(self.term, 0, max(0, self.last_position))
            if pos >= 0:
                self.last_position = pos
                return pos
            return -1
        else:
            # Search forwards from last position
            pos = self.data.find(self.term, self.last_position + 1)
            if pos >= 0:
                self.last_position = pos
                return pos
            # Try from beginning
            pos = self.data.find(self.term, 0)
            if pos >= 0:
                self.last_position = pos
                return pos
            return -1

class Application():
    class Task(enum.Enum):
        POPULATE_HEX_AREA  = enum.auto()

    def __init__(self, file: Optional[str]):

        # These callbacks are used to notify the application
        #  of events from the view
        callbacks = {
            v.Events.REFRESH:                self.cb_refresh,
            v.Events.GOTO:                   self.cb_goto,
            v.Events.NEW:                    self.cb_new,
            v.Events.OPEN:                   self.cb_open,
            v.Events.SAVE:                   self.cb_save,
            v.Events.SAVE_AS:                self.cb_save_as,
            v.Events.UNDO:                   self.cb_undo,
            v.Events.DELETE_BYTE:            self.cb_delete_byte,
            v.Events.COPY_SELECTION:         self.cb_copy_selection,
            v.Events.COPY_HEX_VALUES:        self.cb_copy_hex_values,
            v.Events.COPY_EDITOR_DISPLAY:    self.cb_copy_editor_display,
            v.Events.COPY_GREP_HEX:          self.cb_copy_grep_hex,
            v.Events.COPY_C_SOURCE:          self.cb_copy_c_source,
            v.Events.COPY_PASCAL_SOURCE:     self.cb_copy_pascal_source,
            v.Events.NAND_SELECT:            self.cb_nand_select,
            v.Events.NAND_CALCULATE_ECC:     self.cb_nand_calculate_ecc,
            v.Events.GET_CWD:                self.cb_get_cwd,
            v.Events.CANCEL_LOAD:            self.cb_cancel_load,
            v.Events.SEARCH:                 self.cb_search,
            v.Events.FIND_NEXT:              self.cb_find_next,
            v.Events.FIND_PREV:              lambda: self.cb_find_next(reverse = True),
            v.Events.HEX_MODIFIED:           self.cb_hex_modified,
            v.Events.ASCII_MODIFIED:         self.cb_ascii_modified,
        }

        self.current_file_path = None
        # Stack to hold undo operations
        # Each item is a tuple: ('modify', offset, old_value) or ('delete', start_offset, deleted_bytes)
        self.undo_stack = []
        self.is_modified = False  # Track if file has been modified

        self.view = v.View(title = APP_NAME, callbacks = callbacks)

        self.highlight_context = {ht: set() for ht in HighlightType if HighlightType.is_custom(ht)}

        self.work_item = utils.WorkItem()

        if (file is not None):
            # Need to run populate_view in the View context, *after* the View mainloop is in action 
            self.view.schedule_function(time_ms = 100, callback = lambda: self.populate_view(file))

    def run(self) -> None:
        """Runs the application."""
        self.view.mainloop()

    def init_per_parse_members(self) -> None:
        """Initialize members which are coupled with a single parsing attempt."""
        self.work_item_tasks = dict()

    def populate_view(self, path_file: Union[str, Path]) -> None:
        """Populates the View for the given file.
        
        Args:
            path_file:
                Path to the file to be parsed.
            format:
                Dictionary containing the type of format to use for parsing the file.
                The file will be parsed based on the format type.
                Dictionary should contain one of the following pairs:
                    (-) kaitai_format -> Name of Kaitai format module from format folder
        """
        self.abort_load = False

        self.background_tasks = BackgroundTasks()
        self.background_tasks.start_task(self.Task.POPULATE_HEX_AREA)
        
        self.init_per_parse_members()

        self.view.set_current_file_path("")
        self.search_context = None

        self.view.show_loading()

        self.current_file_path = Path(path_file).resolve()

        def abort_cb():
            return self.abort_load

        def done_loading_hex(is_success: bool) -> None:
            self.background_tasks.task_done(self.Task.POPULATE_HEX_AREA, is_success)
            self._finalize_load()

        # Close old mmap if it exists to prevent resource leak
        if hasattr(self, 'file_mmap') and self.file_mmap is not None:
            self.file_mmap.close()
            self.file_mmap = None

        self.file_mmap = utils.memory_map(path_file)
        # Create a mutable buffer from the file
        self.file_buffer = bytearray(self.file_mmap)
        self.is_modified = False
        self.view.populate_hex_view(self.file_mmap, done_loading_hex)
    
    def _finalize_load(self) -> None:
        """Finalize loading by performing cleanups and any other action needed at end of load."""
        if self.background_tasks.all_done():
            self.tree_parents = None
            self.tree_thread_queue = None
            self.view.hide_loading()

        if self.background_tasks.all_succeeded():
            self.view.set_status("Loaded")
            self.view.set_current_file_path(self.current_file_path)
            #self._submit_work_item(self.xref_manager.finalize, (), None)

    # TODO: Push into workitem class?
    def _submit_work_item(self, work_function: Callable, work_args: Tuple, done_callback: Optional[Callable[[Any], None]]) -> None:
        """Submit a job to the work-item thread together with a callback to be called with the result.
        
        Args:
            work_function:
                Function to be called in the work-item thread.

            work_args:
                Arguments for the function.

            done_callback:
                Callback to be called with the result (or None if not needed).
        
        """
        # A random handle is used to track whether a result belongs to the current session 
        # or a previous one.
        handle = random.getrandbits(32)

        pending_work_items = len(self.work_item_tasks) > 0
        self.work_item_tasks[handle] = done_callback

        self.work_item.submit_job(handle, work_function, work_args)

        if not pending_work_items:
            # If there weren't already work-item jobs, start polling for the result
            self.view.start_worker(self._poll_work_item)

    def _poll_work_item(self) -> bool:
        """Wait for work-item jobs to end and call the callback.
        
        Returns:
            True if there are still pending jobs (function needs to be called again).
        """
        item = self.work_item.get_done_job()
        if item is None:
            # Nothing to handle currently
            return len(self.work_item_tasks) > 0

        handle, result = item
        if handle in self.work_item_tasks:
            callback = self.work_item_tasks[handle]
            if callback is not None:
                callback(result)
            del self.work_item_tasks[handle]
        # else: Handle belongs to previous session, just discard
        
        return len(self.work_item_tasks) > 0


    def cb_refresh(self) -> None:
        """Callback for an event where the user refreshes the view."""
        self.view.reset()
        self.view.set_status("Refreshing...")
        if self.current_file_path is not None:
            self.populate_view(self.current_file_path)
    
    def cb_goto(self, offset: int) -> None:
        """Callback for an event where the user wants to jump to a given offset."""
        # Use file_buffer if available (for modified files), otherwise use file_mmap
        buffer_to_check = self.file_buffer if hasattr(self, 'file_buffer') else self.file_mmap

        if offset < 0 or offset >= len(buffer_to_check):
            raise ValueError("Offset out of range")
        self.view.make_visible(offset, highlight = True)
        self.view.set_status(f"Jumping to offset {hex(offset)} ({offset})")

    def cb_new(self, size: int) -> None:
        """Callback for an event where the user wants to create a new file.

        Args:
            size: Size of the new file in bytes
        """
        try:
            # Create a new buffer filled with 0x00
            self.file_buffer = bytearray(size)

            # Create a temporary file path (will need Save As to get actual name)
            self.current_file_path = None

            # Clear undo stack for new file
            self.undo_stack = []
            self.is_modified = False

            # Populate the view with the new buffer
            def done_loading_hex(is_success: bool) -> None:
                if is_success:
                    self.view.set_status(f"New file created with {size} bytes")
                    self.view.is_file_open = True
                    self.view.menubar.toggle_loaded_file_commands(enable=True)

            self.view.reset()
            self.view.populate_hex_view(self.file_buffer, done_loading_hex)
            self.view.set_current_file_path("New File")
        except Exception as e:
            self.view.display_error(f"Failed to create new file:\n{str(e)}")
            self.view.set_status("New file creation failed")

    def cb_open(self, path: str) -> None:
        """Callback for an event where the user wants to open a new file."""
        self.view.reset()
        self.populate_view(path)
        self.view.set_status(f"Opening {Path(path).resolve()}")

    def cb_get_cwd(self) -> str:
        """Callback for getting the current working directory.
        The CWD is defined as the parent directory of the last file opened,
        or the current directory if no file was previously opened.
        """
        if self.current_file_path is not None:
            return Path(self.current_file_path).parent

        return "."

    def cb_cancel_load(self) -> None:
        """Callback for an event where the user aborts loading."""
        self.abort_load = True
        self.view.hide_loading()
        self.view.reset()
        self.view.set_status(f"Aborted")
        self.view.set_current_file_path("")

    def cb_search(self, term: bytes) -> None:
        """Callback for an event where the user wants to search the binary."""
        self.search_context = SearchContext(self.file_buffer, term)
        self.cb_find_next()

    def cb_find_next(self, reverse: bool = False) -> None:
        """Callback for an event where the user wants to find the next occurrence of the term.

        Args:
            reverse:
                Search in reverse direction.
        """

        if self.search_context is None:
            # If there is no term, open the original "Search" dialog
            self.view.show_search()
            return

        # Search directly (no need for work item thread for small searches)
        offset = self.search_context.find_next(reverse)

        if offset >= 0:
            self.view.make_visible(offset, length = len(self.search_context.term), highlight = True)
            self.view.set_status(f"Found at offset {hex(offset)} ({offset})")
        else:
            self.view.make_visible(None)
            self.view.set_status(f"Search term not found")
            self.view.display_error("Search term not found")

    def cb_hex_modified(self, offset: int, hex_value: str) -> bool:
        """Callback when hex value is modified.

        Args:
            offset: Byte offset in the file
            hex_value: New hex value (2 characters)

        Returns:
            True if modification was valid and applied
        """
        if not hasattr(self, 'file_buffer'):
            return False

        try:
            # Validate and convert hex string to byte
            byte_value = int(hex_value, 16)
            if byte_value < 0 or byte_value > 255:
                return False

            # Save old value for undo
            old_value = self.file_buffer[offset]
            self.undo_stack.append(('modify', offset, old_value))

            # Update buffer
            self.file_buffer[offset] = byte_value
            self.is_modified = True
            return True
        except (ValueError, IndexError):
            return False

    def cb_ascii_modified(self, offset: int, ascii_char: str) -> bool:
        """Callback when ASCII value is modified.

        Args:
            offset: Byte offset in the file
            ascii_char: New ASCII character

        Returns:
            True if modification was valid and applied
        """
        if not hasattr(self, 'file_buffer'):
            return False

        try:
            # Convert character to byte
            byte_value = ord(ascii_char)
            if byte_value > 255:
                return False

            # Save old value for undo
            old_value = self.file_buffer[offset]
            self.undo_stack.append(('modify', offset, old_value))

            # Update buffer
            self.file_buffer[offset] = byte_value
            self.is_modified = True
            return True
        except (ValueError, IndexError):
            return False

    def cb_save(self) -> None:
        """Callback for saving the file with modifications."""
        if not hasattr(self, 'file_buffer'):
            return

        # If this is a new file without a path, prompt for Save As
        if self.current_file_path is None:
            self.view.save_file_as()
            return

        try:
            # Close the memory map before writing
            if hasattr(self, 'file_mmap') and self.file_mmap is not None:
                self.file_mmap.close()
                self.file_mmap = None

            # Write the buffer back to the file
            with open(self.current_file_path, 'wb') as f:
                f.write(self.file_buffer)

            # Reopen the file as memory map
            self.file_mmap = utils.memory_map(self.current_file_path)

            self.is_modified = False
            self.view.set_status(f"Saved {len(self.file_buffer)} bytes to {self.current_file_path}")
        except Exception as e:
            self.view.display_error(f"Failed to save file:\n{str(e)}")
            self.view.set_status("Save failed")

    def cb_save_as(self, new_file_path: str) -> None:
        """Callback for saving the file with a new name.

        Args:
            new_file_path: Path to save the file to
        """
        if not hasattr(self, 'file_buffer'):
            return

        try:
            # Close the old memory map before writing
            if hasattr(self, 'file_mmap') and self.file_mmap is not None:
                self.file_mmap.close()
                self.file_mmap = None

            # Write the buffer to the new file
            with open(new_file_path, 'wb') as f:
                f.write(self.file_buffer)

            # Update current file path
            self.current_file_path = Path(new_file_path).resolve()

            # Open the new file as memory map
            self.file_mmap = utils.memory_map(self.current_file_path)

            # Update the view with new file path
            self.view.set_current_file_path(self.current_file_path)
            self.is_modified = False
            self.view.set_status(f"Saved {len(self.file_buffer)} bytes to {self.current_file_path}")
        except Exception as e:
            self.view.display_error(f"Failed to save file:\n{str(e)}")
            self.view.set_status("Save As failed")

    def cb_undo(self) -> None:
        """Callback for undoing the last change."""
        if not hasattr(self, 'file_buffer') or not self.undo_stack:
            self.view.set_status("Nothing to undo")
            return

        try:
            # Pop the last operation from the undo stack
            operation = self.undo_stack.pop()

            if operation[0] == 'modify':
                # Undo a byte modification
                _, offset, old_value = operation
                self.file_buffer[offset] = old_value

                # Update the view to reflect the change
                self.view.reset()
                self.view.populate_hex_view(self.file_buffer, lambda success: None)
                self.view.make_visible(offset, highlight=True)

                self.view.set_status(f"Undid change at offset 0x{offset:X}")

            elif operation[0] == 'delete':
                # Undo a deletion by re-inserting the deleted bytes
                _, start_offset, deleted_bytes = operation

                # Re-insert the deleted bytes
                self.file_buffer[start_offset:start_offset] = deleted_bytes

                # Update the view to reflect the change
                self.view.reset()
                self.view.populate_hex_view(self.file_buffer, lambda success: None)
                self.view.make_visible(start_offset, highlight=True)

                self.view.set_status(f"Undid deletion at offset 0x{start_offset:X}, restored {len(deleted_bytes)} bytes")

            # If undo stack is empty, file is no longer modified
            if not self.undo_stack:
                self.is_modified = False

        except Exception as e:
            self.view.display_error(f"Failed to undo:\n{str(e)}")
            self.view.set_status("Undo failed")

    def cb_delete_byte(self, offset) -> None:
        """Callback for deleting a byte or block at the specified offset.

        Args:
            offset: Either an int for single byte deletion, or a tuple (start, end) for block deletion.
        """
        if not hasattr(self, 'file_buffer') or len(self.file_buffer) == 0:
            self.view.set_status("No file loaded")
            return

        try:
            # Check if it's a block deletion (tuple) or single byte deletion (int)
            if isinstance(offset, tuple):
                # Block deletion
                start_offset, end_offset = offset

                if start_offset < 0 or end_offset > len(self.file_buffer) or start_offset >= end_offset:
                    self.view.set_status("Invalid offset range")
                    return

                bytes_to_delete = end_offset - start_offset

                # Save deleted bytes for undo
                deleted_bytes = bytearray(self.file_buffer[start_offset:end_offset])
                self.undo_stack.append(('delete', start_offset, deleted_bytes))

                # Remove the block from the buffer
                del self.file_buffer[start_offset:end_offset]

                self.is_modified = True

                # Update the view to reflect the change
                self.view.reset()
                self.view.populate_hex_view(self.file_buffer, lambda success: None)

                # Make the start offset visible
                if start_offset < len(self.file_buffer):
                    self.view.make_visible(start_offset, highlight=True)
                elif len(self.file_buffer) > 0:
                    self.view.make_visible(len(self.file_buffer) - 1, highlight=True)

                self.view.set_status(f"Deleted {bytes_to_delete} bytes at offset 0x{start_offset:X}, file size now {len(self.file_buffer)} bytes")
            else:
                # Single byte deletion
                if offset < 0 or offset >= len(self.file_buffer):
                    self.view.set_status("Invalid offset")
                    return

                # Save deleted byte for undo
                deleted_bytes = bytearray([self.file_buffer[offset]])
                self.undo_stack.append(('delete', offset, deleted_bytes))

                # Remove the byte from the buffer
                del self.file_buffer[offset]

                self.is_modified = True

                # Update the view to reflect the change
                self.view.reset()
                self.view.populate_hex_view(self.file_buffer, lambda success: None)

                # Make the same offset visible (which now contains the next byte)
                if offset < len(self.file_buffer):
                    self.view.make_visible(offset, highlight=True)
                elif len(self.file_buffer) > 0:
                    self.view.make_visible(len(self.file_buffer) - 1, highlight=True)

                self.view.set_status(f"Deleted byte at offset 0x{offset:X}, file size now {len(self.file_buffer)} bytes")
        except Exception as e:
            self.view.display_error(f"Failed to delete:\n{str(e)}")
            self.view.set_status("Delete failed")

    def cb_copy_selection(self, range_tuple) -> None:
        """Callback for copying selection or all data to clipboard.

        Args:
            range_tuple: Tuple of (start_offset, end_offset) or (0, None) for all data.
        """
        if not hasattr(self, 'file_buffer') or len(self.file_buffer) == 0:
            self.view.set_status("No file loaded")
            return

        try:
            start, end = range_tuple

            if end is None:
                # Copy all data
                data_to_copy = bytes(self.file_buffer)
                self.view.set_status(f"Copied {len(data_to_copy)} bytes to clipboard")
            else:
                # Copy selected range
                if start < 0 or end > len(self.file_buffer) or start >= end:
                    self.view.set_status("Invalid offset range")
                    return

                data_to_copy = bytes(self.file_buffer[start:end])
                self.view.set_status(f"Copied {len(data_to_copy)} bytes to clipboard")

            # Copy to clipboard
            self.view.copy_to_clipboard(data_to_copy)

        except Exception as e:
            self.view.display_error(f"Failed to copy:\n{str(e)}")
            self.view.set_status("Copy failed")

    def cb_copy_hex_values(self, range_tuple) -> None:
        """Callback for copying selection or all data as hex values string.

        Args:
            range_tuple: Tuple of (start_offset, end_offset) or (0, None) for all data.
        """
        if not hasattr(self, 'file_buffer') or len(self.file_buffer) == 0:
            self.view.set_status("No file loaded")
            return

        try:
            start, end = range_tuple

            if end is None:
                # Copy all data
                data_to_copy = bytes(self.file_buffer)
            else:
                # Copy selected range
                if start < 0 or end > len(self.file_buffer) or start >= end:
                    self.view.set_status("Invalid offset range")
                    return

                data_to_copy = bytes(self.file_buffer[start:end])

            # Format as hex values string: 4CF6406C987144398FBBCD410000
            hex_values = "".join([f"{byte:02X}" for byte in data_to_copy])

            # Copy to clipboard
            self.view.copy_to_clipboard_text(hex_values)
            self.view.set_status(f"Copied {len(data_to_copy)} bytes as hex values to clipboard")

        except Exception as e:
            self.view.display_error(f"Failed to copy:\n{str(e)}")
            self.view.set_status("Copy failed")

    def cb_copy_grep_hex(self, range_tuple) -> None:
        """Callback for copying selection or all data as GREP hex format.

        Args:
            range_tuple: Tuple of (start_offset, end_offset) or (0, None) for all data.
        """
        if not hasattr(self, 'file_buffer') or len(self.file_buffer) == 0:
            self.view.set_status("No file loaded")
            return

        try:
            start, end = range_tuple

            if end is None:
                # Copy all data
                data_to_copy = bytes(self.file_buffer)
            else:
                # Copy selected range
                if start < 0 or end > len(self.file_buffer) or start >= end:
                    self.view.set_status("Invalid offset range")
                    return

                data_to_copy = bytes(self.file_buffer[start:end])

            # Format as GREP hex: \xF6\x40\x6C\x98...
            grep_hex = "".join([f"\\x{byte:02X}" for byte in data_to_copy])

            # Copy to clipboard
            self.view.copy_to_clipboard_text(grep_hex)
            self.view.set_status(f"Copied {len(data_to_copy)} bytes as GREP hex to clipboard")

        except Exception as e:
            self.view.display_error(f"Failed to copy:\n{str(e)}")
            self.view.set_status("Copy failed")

    def cb_copy_c_source(self, range_tuple) -> None:
        """Callback for copying selection or all data as C source array.

        Args:
            range_tuple: Tuple of (start_offset, end_offset) or (0, None) for all data.
        """
        if not hasattr(self, 'file_buffer') or len(self.file_buffer) == 0:
            self.view.set_status("No file loaded")
            return

        try:
            start, end = range_tuple

            if end is None:
                # Copy all data
                data_to_copy = bytes(self.file_buffer)
            else:
                # Copy selected range
                if start < 0 or end > len(self.file_buffer) or start >= end:
                    self.view.set_status("Invalid offset range")
                    return

                data_to_copy = bytes(self.file_buffer[start:end])

            # Format as C source array
            c_source = f"unsigned char data[{len(data_to_copy)}] = {{\n"

            # Add hex values, 16 bytes per line
            for i in range(0, len(data_to_copy), 16):
                # Get up to 16 bytes for this line
                line_bytes = data_to_copy[i:i+16]
                hex_values = [f"0x{byte:02X}" for byte in line_bytes]

                # Add line with proper indentation
                c_source += "\t" + ", ".join(hex_values)

                # Add comma if not the last line
                if i + 16 < len(data_to_copy):
                    c_source += ","

                c_source += "\n"

            c_source += "};"

            # Copy to clipboard
            self.view.copy_to_clipboard_text(c_source)
            self.view.set_status(f"Copied {len(data_to_copy)} bytes as C source array to clipboard")

        except Exception as e:
            self.view.display_error(f"Failed to copy:\n{str(e)}")
            self.view.set_status("Copy failed")

    def cb_copy_pascal_source(self, range_tuple) -> None:
        """Callback for copying selection or all data as Pascal source array.

        Args:
            range_tuple: Tuple of (start_offset, end_offset) or (0, None) for all data.
        """
        if not hasattr(self, 'file_buffer') or len(self.file_buffer) == 0:
            self.view.set_status("No file loaded")
            return

        try:
            start, end = range_tuple

            if end is None:
                # Copy all data
                data_to_copy = bytes(self.file_buffer)
            else:
                # Copy selected range
                if start < 0 or end > len(self.file_buffer) or start >= end:
                    self.view.set_status("Invalid offset range")
                    return

                data_to_copy = bytes(self.file_buffer[start:end])

            # Format as Pascal source array
            # data: array[0..7] of byte = (
            #     $F6, $40, $6C, $98, $71, $44, $39, $8F
            # );
            pascal_source = f"data: array[0..{len(data_to_copy)-1}] of byte = (\n"

            # Add hex values, 16 bytes per line
            for i in range(0, len(data_to_copy), 16):
                # Get up to 16 bytes for this line
                line_bytes = data_to_copy[i:i+16]
                hex_values = [f"${byte:02X}" for byte in line_bytes]

                # Add line with proper indentation
                pascal_source += "\t" + ", ".join(hex_values)

                # Add comma if not the last line
                if i + 16 < len(data_to_copy):
                    pascal_source += ","

                pascal_source += "\n"

            pascal_source += ");"

            # Copy to clipboard
            self.view.copy_to_clipboard_text(pascal_source)
            self.view.set_status(f"Copied {len(data_to_copy)} bytes as Pascal source array to clipboard")

        except Exception as e:
            self.view.display_error(f"Failed to copy:\n{str(e)}")
            self.view.set_status("Copy failed")

    def cb_copy_editor_display(self, range_tuple) -> None:
        """Callback for copying selection or all data as editor display format.

        Args:
            range_tuple: Tuple of (start_offset, end_offset) or (0, None) for all data.
        """
        if not hasattr(self, 'file_buffer') or len(self.file_buffer) == 0:
            self.view.set_status("No file loaded")
            return

        try:
            start, end = range_tuple

            if end is None:
                # Copy all data
                data_to_copy = bytes(self.file_buffer)
                start = 0
            else:
                # Copy selected range
                if start < 0 or end > len(self.file_buffer) or start >= end:
                    self.view.set_status("Invalid offset range")
                    return

                data_to_copy = bytes(self.file_buffer[start:end])

            # Format as hex editor display
            # Header row
            editor_display = " Offset     0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F         ANSI ASCII\n\n"

            # Calculate starting row offset (aligned to 16-byte boundary)
            first_row_offset = (start // 16) * 16
            # Calculate position within first row
            first_row_start_pos = start % 16
            # Calculate ending position
            last_byte_offset = start + len(data_to_copy) - 1
            last_row_offset = (last_byte_offset // 16) * 16
            last_row_end_pos = (last_byte_offset % 16) + 1

            # Process each 16-byte row
            current_offset = first_row_offset
            data_index = 0

            while current_offset <= last_row_offset:
                # Row offset in hex (8 characters)
                row_text = f"{current_offset:08X}   "

                # Determine which bytes to show in this row
                if current_offset == first_row_offset:
                    row_start_pos = first_row_start_pos
                else:
                    row_start_pos = 0

                if current_offset == last_row_offset:
                    row_end_pos = last_row_end_pos
                else:
                    row_end_pos = 16

                # Build hex part with spaces before data
                hex_part = ""
                ascii_part = ""

                for i in range(16):
                    if i < row_start_pos or i >= row_end_pos:
                        # Empty space (no data in this position)
                        hex_part += "   "
                        ascii_part += " "
                    else:
                        # We have data for this position
                        byte_val = data_to_copy[data_index]
                        hex_part += f"{byte_val:02X} "
                        # ASCII representation (printable or .)
                        if 32 <= byte_val <= 126:
                            ascii_part += chr(byte_val)
                        else:
                            ascii_part += "."
                        data_index += 1

                # Combine row
                row_text += hex_part + "  " + ascii_part + "\n"
                editor_display += row_text

                # Move to next row
                current_offset += 16

            # Copy to clipboard
            self.view.copy_to_clipboard_text(editor_display)
            self.view.set_status(f"Copied {len(data_to_copy)} bytes as editor display to clipboard")

        except Exception as e:
            self.view.display_error(f"Failed to copy:\n{str(e)}")
            self.view.set_status("Copy failed")

    def cb_nand_select(self, selected_config_name) -> None:
        """Callback for NAND flash configuration selection.

        Args:
            selected_config_name: Name of selected config or None if cancelled.
        """
        if selected_config_name is None:
            # User cancelled
            self.view.set_status("NAND selection cancelled")
            return

        # Store the selected config name for later use
        self.selected_nand_config = selected_config_name
        self.view.enable_nand_calculate_ecc(True)
        self.view.set_status(f"Selected NAND configuration: {selected_config_name}")

    def cb_nand_calculate_ecc(self, event) -> None:
        """Callback for NAND Calculate ECC - scans entire file.

        Args:
            event: Event (not used).
        """
        if not hasattr(self, 'selected_nand_config') or self.selected_nand_config is None:
            self.view.display_error("No NAND configuration selected.\nPlease select a configuration first.")
            return

        if not hasattr(self, 'file_buffer') or len(self.file_buffer) == 0:
            self.view.display_error("No file loaded.\nPlease open a file first.")
            return

        # Get the selected NAND configuration
        config = get_config_by_name(self.selected_nand_config)
        if config is None:
            self.view.display_error(f"Configuration '{self.selected_nand_config}' not found.")
            return

        # Check if supported ECC type
        if config.ecc_type not in [ECCType.BCH, ECCType.HAMMING]:
            self.view.display_error(f"ECC type {config.ecc_type.name} is not supported yet.\nOnly BCH and HAMMING are currently supported.")
            return

        try:
            # Calculate page size (total size including data, ECC, BBM, padding)
            page_size = config.data_size + config.ecc_size + config.bbm_size + config.padding_size

            if len(self.file_buffer) < page_size:
                self.view.display_error(f"File is too small.\nExpected at least {page_size} bytes for one page, got {len(self.file_buffer)} bytes.")
                return

            # Calculate total number of pages
            total_pages = len(self.file_buffer) // page_size

            # Statistics counters
            pages_valid = 0
            pages_corrected = 0
            pages_corrupted = 0  # Too many errors to correct
            pages_empty = 0
            total_errors_corrected = 0

            # Process each page
            for page_num in range(total_pages):
                page_offset = page_num * page_size
                page_data = bytes(self.file_buffer[page_offset:page_offset + page_size])

                # Check if page is empty (all 0xFF)
                if all(byte == 0xFF for byte in page_data):
                    pages_empty += 1
                    continue

                # Extract data bytes based on config ranges
                data = extract_data_from_page(page_data, config)

                # Extract existing ECC from page
                existing_ecc = extract_ecc_from_page(page_data, config)

                # Check if existing ECC matches calculated ECC based on ECC type
                if config.ecc_type == ECCType.BCH:
                    ecc_valid = verify_bch_ecc(data, existing_ecc)
                else:  # ECCType.HAMMING
                    ecc_valid = verify_hamming_ecc(data, existing_ecc)

                if ecc_valid:
                    pages_valid += 1
                else:
                    # Try to correct errors based on ECC type
                    if config.ecc_type == ECCType.BCH:
                        corrected_data, num_errors = correct_bch_errors(data, existing_ecc)
                    else:  # ECCType.HAMMING
                        corrected_data, num_errors = correct_hamming_errors(data, existing_ecc)

                    if num_errors == -1:
                        # Too many errors to correct
                        pages_corrupted += 1
                    elif num_errors >= 0:
                        # Errors corrected successfully
                        pages_corrected += 1
                        total_errors_corrected += num_errors

                        # Write corrected data back to buffer
                        corrected_data_index = 0
                        for start, end in config.data_ranges:
                            for offset in range(start, end + 1):
                                if corrected_data_index < len(corrected_data):
                                    buffer_offset = page_offset + offset
                                    if buffer_offset >= len(self.file_buffer):
                                        corrected_data_index += 1
                                        continue

                                    old_value = self.file_buffer[buffer_offset]
                                    new_value = corrected_data[corrected_data_index]

                                    if old_value is None or new_value is None:
                                        corrected_data_index += 1
                                        continue

                                    if old_value != new_value:
                                        # Add to undo stack
                                        self.undo_stack.append(('modify', buffer_offset, old_value))
                                        # Update buffer
                                        self.file_buffer[buffer_offset] = new_value
                                        # Update the view directly for this byte
                                        self.view.update_byte_display(buffer_offset, new_value)
                                    corrected_data_index += 1

                        # Calculate new ECC for corrected data
                        if config.ecc_type == ECCType.BCH:
                            new_ecc = calculate_bch_ecc(corrected_data, config.ecc_size)
                        else:  # ECCType.HAMMING
                            new_ecc = calculate_hamming_ecc(corrected_data, config.ecc_size)

                        # Write new ECC back to buffer
                        new_ecc_index = 0
                        for start, end in config.ecc_ranges:
                            for offset in range(start, end + 1):
                                if new_ecc_index < len(new_ecc):
                                    buffer_offset = page_offset + offset
                                    if buffer_offset >= len(self.file_buffer):
                                        new_ecc_index += 1
                                        continue

                                    old_value = self.file_buffer[buffer_offset]
                                    new_value = new_ecc[new_ecc_index]

                                    if old_value is None or new_value is None:
                                        new_ecc_index += 1
                                        continue

                                    if old_value != new_value:
                                        # Add to undo stack
                                        self.undo_stack.append(('modify', buffer_offset, old_value))
                                        # Update buffer
                                        self.file_buffer[buffer_offset] = new_value
                                        # Update the view directly for this byte
                                        self.view.update_byte_display(buffer_offset, new_value)
                                    new_ecc_index += 1

            # Mark file as modified if any corrections were made
            if pages_corrected > 0:
                self.is_modified = True

            # Build summary report
            result_msg = f"{config.ecc_type.name} ECC Analysis Report\n\n"
            result_msg += f"Configuration: {config.name}\n"
            result_msg += f"Page size: {page_size} bytes\n"
            result_msg += f"Total pages checked: {total_pages}\n\n"
            result_msg += f"Valid pages: {pages_valid}\n"
            result_msg += f"Corrected pages: {pages_corrected} ({total_errors_corrected} bit errors)\n"
            result_msg += f"Corrupted pages: {pages_corrupted} (could not correct)\n"
            result_msg += f"Empty pages: {pages_empty}\n"

            self.view.display_info(result_msg)
            self.view.set_status(f"Scanned {total_pages} pages: {pages_valid} valid, {pages_corrected} corrected, {pages_corrupted} corrupted, {pages_empty} empty")

        except Exception as e:
            self.view.display_error(f"Failed to calculate ECC:\n{str(e)}")
            self.view.set_status("ECC calculation failed")
