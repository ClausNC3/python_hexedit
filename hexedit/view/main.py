"""The 'View' Module of the application.

This file contains the main "View" logic.

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
import importlib.resources

from tkinter import messagebox, simpledialog, filedialog
from typing import Dict, Callable

from .menus import *
from .bars import *
from .hex_area import *
from .events import *
from .widgets import *
from .windows import *

from ..common import *

class View(tk.Tk):
    """ The application 'View' Model."""
    
    def __init__(self, title, callbacks: Dict[Events, Callable[..., None]], *args, **kwargs):
        """Instantiate the class.
        
        Args:
            title: 
                Title of the application.
            
            callbacks:
                Dictionary of callbacks to call when an event from Events occurs
                
        """
        super().__init__(*args, **kwargs)

        self.root = self
        self.app_title = title
        self.callbacks = callbacks
        self.is_file_open = False

        self.title(title)
        self.resizable(width = True, height = True)
        self.geometry('790x720')

        try:
            with importlib.resources.path(f"{__package__}.assets", "pytai.ico") as icon_path:
                self.iconbitmap(default = icon_path)
        except tk.TclError:
            try:
                with importlib.resources.path(f"{__package__}.assets", "pytai.gif") as icon_path:
                    icon = tk.PhotoImage(file = icon_path)
                    self.root.call('wm', 'iconphoto', self.root._w, icon)
            except Exception:
                pass

        self.menubar = MenuBar(self.root, {
            MenuBar.Events.REFRESH:                 self.refresh,
            MenuBar.Events.GOTO:                    self.show_goto,
            MenuBar.Events.NEW:                     self.show_new,
            MenuBar.Events.OPEN:                    self.show_open,
            MenuBar.Events.SAVE:                    self.save_file,
            MenuBar.Events.SAVE_AS:                 self.save_file_as,
            MenuBar.Events.UNDO:                    self.undo,
            MenuBar.Events.CLEAR_BLOCK:             self.clear_block,
            MenuBar.Events.SEARCH:                  self.show_search,
            MenuBar.Events.FIND_NEXT:               self.find_next,
            MenuBar.Events.FIND_PREV:               self.find_prev,
            MenuBar.Events.ABOUT:                   self.show_about,
        })
        self.root.config(menu = self.menubar)

        #self.top_frame = tk.Frame()
        #self.address_bar = AddressBar(self.top_frame)
        #self.top_frame.pack(side=tk.TOP, fill = tk.BOTH)

        self.bottom_frame = tk.Frame()
        self.status_bar = StatusBar(self.bottom_frame)
        self.bottom_frame.pack(side=tk.BOTTOM, fill = tk.BOTH)

        self.pw = tk.Frame()        
        self.hex_view = HexAreaView(self, self.pw, self.callbacks)
        self.pw.pack(fill = tk.BOTH, expand = True) 

        self.root.bind('<F5>', self.refresh)
        self.root.bind('<Control-g>', self.show_goto)
        self.root.bind('<Control-f>', self.show_search)
        self.root.bind('<F3>', self.find_next)
        self.root.bind('<Shift-F3>', self.find_prev)
        self.root.bind('<Control-n>', self.show_new)
        self.root.bind('<Control-o>', self.show_open)
        self.root.bind('<Control-s>', self.save_file)
        self.root.bind('<Control-Shift-S>', self.save_file_as)
        self.root.bind('<Control-z>', self.undo)

        # Delegate a few interface functions directly to internal implementation
        self.populate_hex_view = self.hex_view.populate_hex_view
        self.make_visible = self.hex_view.make_visible

        # Initialize Clear Block menu state to disabled
        self.menubar.update_clear_block_state(False)

        self.reset()

    def reset(self) -> None:
        """Reset the view to its initial state."""
        self.hex_view.reset()

    def refresh(self, event = None) -> None:
        """Handle a user refresh request."""
        if not self.is_file_open:
            return

        self.callbacks[Events.REFRESH]()

    def show_goto(self, event = None) -> None:
        """Show the 'goto' diaglog to jump to an arbitrary offset."""
        if not self.is_file_open:
            return
            
        answer = simpledialog.askstring("Go to...", "Enter offset (prefix with '0x' for hex)",
                                         parent = self.root)
        if answer is None:
            return

        try:
            try:
                offset = int(answer, 0)
            except ValueError:
                raise ValueError("Illegal characters")
            self.callbacks[Events.GOTO](offset)
        except ValueError as e:
            self.display_error(f"Unable to jump to offset {answer}:\n({str(e)})")

    def check_save_modified(self) -> bool:
        """Check if file is modified and ask user to save.

        Returns:
            True if it's safe to continue (saved, not modified, or user chose No)
            False if user chose Cancel
        """
        # Get modified status from application via callback
        if hasattr(self.callbacks[Events.SAVE], '__self__'):
            app = self.callbacks[Events.SAVE].__self__
            if hasattr(app, 'is_modified') and app.is_modified:
                # Get current file name
                filename = "New File" if app.current_file_path is None else str(app.current_file_path)

                response = messagebox.askyesnocancel(
                    "Save Changes?",
                    f"{filename} was modified.\nSave now?"
                )

                if response is None:  # Cancel
                    return False
                elif response:  # Yes
                    self.callbacks[Events.SAVE]()
                    return True
                else:  # No
                    return True
        return True

    def show_new(self, event = None) -> None:
        """Show the 'New file' window."""
        if not self.check_save_modified():
            return
        NewFileWindow(self.root, self.callbacks[Events.NEW])

    def show_open(self, event = None) -> None:
        """Show the 'Open file' window."""
        if not self.check_save_modified():
            return
        cwd = self.callbacks[Events.GET_CWD]()
        filename = filedialog.askopenfilename(filetypes=[('All files','*.*')], initialdir=cwd)
        if filename:
            self.callbacks[Events.OPEN](filename)

    def save_file(self, event = None) -> None:
        """Save the current file with modifications."""
        if not self.is_file_open:
            return

        self.callbacks[Events.SAVE]()

    def save_file_as(self, event = None) -> None:
        """Save the current file with a new name."""
        if not self.is_file_open:
            return

        cwd = self.callbacks[Events.GET_CWD]()
        filename = filedialog.asksaveasfilename(
            defaultextension=".*",
            filetypes=[('All files','*.*')],
            initialdir=cwd
        )

        if filename:
            self.callbacks[Events.SAVE_AS](filename)

    def show_search(self, event = None) -> None:
        """Show the 'Search' window"""
        if not self.is_file_open:
            return

        SearchWindow(self.root, self.callbacks[Events.SEARCH])

    def find_next(self, event = None) -> None:
        """Find the next occurrance of the search term."""
        if not self.is_file_open:
            return

        self.callbacks[Events.FIND_NEXT]()

    def find_prev(self, event = None) -> None:
        """Find the previous occurrance of the search term."""
        if not self.is_file_open:
            return

        self.callbacks[Events.FIND_PREV]()

    def undo(self, event = None) -> None:
        """Undo the last change."""
        if not self.is_file_open:
            return

        self.callbacks[Events.UNDO]()

    def clear_block(self, event = None) -> None:
        """Clear the selected block."""
        if not self.is_file_open:
            return

        # Get selection range
        selection_range = self.hex_view._get_selection_range()
        if selection_range:
            from tkinter import messagebox
            if messagebox.askyesno("Delete Block", "Removing the current block will decrease the file size. Continue?"):
                self.callbacks[Events.DELETE_BYTE](selection_range)

    def show_about(self, event = None) -> None:
        """Show the 'About' window."""
        AboutWindow(self.root)

    def update_clear_block_menu(self, has_selection: bool) -> None:
        """Update Clear Block menu state based on selection.

        Args:
            has_selection: True if there is a selection, False otherwise.
        """
        self.menubar.update_clear_block_state(has_selection)

    def set_status(self, status: str) -> None:
        """Set the given status in the status bar.
        
        Args:
            status:
                Status to set.
        """
        self.status_bar.set_status(status)

    @staticmethod
    def display_error(msg: str) -> None:
        """Display the given error.
        
        Args:
            msg:
                Error message to display.
        """
        messagebox.showerror("Error", msg)

    @staticmethod
    def display_warning(msg: str) -> None:
        """Display the given warning.
        
        Args:
            msg:
                Warning message to display.
        """
        messagebox.showwarning("Warning", msg)

    def mark_range(self, start_offset: int, end_offset: int, mark: bool, highlight_type: HighlightType = HighlightType.DEFAULT) -> None:
        """Highlight a range between the given offsets.
        
        Args:
            start_offset:
                Offset to highlight from (absolute index of byte in file)
            end_offset:
                Offset to highlight to (absolute index of byte in file)
            mark:
                True to highlight a range, False to remove the highlight
            highlight_type:
                Type of highlight to use. Use HighlightType.DEFAULT for selection, 
                or HighlightType.CUSTOMx for user triggered custom highlights
        """
        if mark and start_offset is not None and end_offset is not None:
            length = end_offset - start_offset
            
            status = []
            if length > 0:
                # end offset is exclusive, but we want to show inclusive range
                status.append(f"Range: {hex(start_offset)}-{hex(end_offset - 1)}")

            status.append(f"Length: {length} ({hex(length)}) bytes")

            self.set_status(" | ".join(status))
            self.hex_view.mark_range(start_offset, end_offset, mark, highlight_type)
        else:
            self.set_status("")
            self.hex_view.unmark_range(start_offset, end_offset, highlight_type)

    def show_loading(self) -> None:
        """Show the loading window."""
        
        # tkinter has better performance when the widgets aren't visible
        self.pw.pack_forget() 

        self.loading = LoadingWindow(self.root, self.callbacks[Events.CANCEL_LOAD])
        

    def hide_loading(self) -> None:
        """Hide the loading window."""

        try:
            self.pw.pack(fill = tk.BOTH, expand = True) # Show the widgets again
            self.loading.stop()
            self.loading = None
        except AttributeError:
            assert(self.loading is None)
            pass

    def start_worker(self, callback: Callable[[], bool]) -> None:
        """Start a worker provided by the caller.
        
        The worker will be called again as long as the previous call returned True.

        Args:
            callback:
                The callback to the worker. Expected to return a boolean indicating
                whether it should be called again.
        
        """
        reschedule = callback()
        if reschedule:
            self.root.after_idle(lambda: self.start_worker(callback))

    def schedule_function(self, time_ms: int, callback: Callable[[], None]) -> None:
        """Schedule a function to run after time_ms milliseconds.

        Function will run in the View context.
        
        Args:
            time_ms:
                Time in milliseconds after which the callback will be called.

            callback:
                Callback to call.
                
        """
        self.root.after(time_ms, callback)

    def set_current_file_path(self, file_path: str) -> None:
        """Displays the path of the file currently open.
        
        Args:
            file_path:
                Path to the file currently open.
                An empty string removes the file path.
        
        """
        title = self.app_title
        if file_path != "":
            title += f" - [{file_path}]"
            self.is_file_open = True
            self.menubar.toggle_loaded_file_commands(enable = True)
        else:
            self.is_file_open = False
            self.menubar.toggle_loaded_file_commands(enable = False)
        self.winfo_toplevel().title(title)

