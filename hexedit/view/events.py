"""The 'View' Module of the application: The GUI Events.

This file contains the different GUI events that can be triggered by the user/application.

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
import enum

class Events(enum.Enum):
        
    # User refreshes the view
    REFRESH            = enum.auto()
    
    # Application needs to set the status bar
    SET_STATUS         = enum.auto()
    
    # Application needs to display error
    SHOW_ERROR         = enum.auto()

    # User wants to jump to offset
    GOTO               = enum.auto()

    # User wants to create a new file
    NEW                = enum.auto()

    # User wants to open file
    OPEN               = enum.auto()

    # Get current working directory
    GET_CWD            = enum.auto()
    
    # Abort loading the current file
    CANCEL_LOAD        = enum.auto()

    # Search in binary
    SEARCH             = enum.auto()

    # Find next result for search
    FIND_NEXT          = enum.auto()

    # Find previous result for search
    FIND_PREV          = enum.auto()

    # Copy the selection to the clipboard
    COPY_SELECTION     = enum.auto()

    # Hex value was modified
    HEX_MODIFIED       = enum.auto()

    # ASCII value was modified
    ASCII_MODIFIED     = enum.auto()

    # User wants to save the file
    SAVE               = enum.auto()

    # User wants to save the file with a new name
    SAVE_AS            = enum.auto()

    # User wants to undo last change
    UNDO               = enum.auto()

    # User wants to delete byte at cursor
    DELETE_BYTE        = enum.auto()

    # User wants to clear selected block
    CLEAR_BLOCK        = enum.auto()

    # User wants to select all bytes
    SELECT_ALL         = enum.auto()

    # User wants to copy selection/all as raw data
    COPY_NORMAL        = enum.auto()

    # User wants to copy selection/all as hex values string
    COPY_HEX_VALUES    = enum.auto()

    # User wants to copy selection/all as editor display format
    COPY_EDITOR_DISPLAY = enum.auto()

    # User wants to copy selection/all as GREP hex format
    COPY_GREP_HEX      = enum.auto()

    # User wants to copy selection/all as C source array
    COPY_C_SOURCE      = enum.auto()

    # User wants to copy selection/all as Pascal source array
    COPY_PASCAL_SOURCE = enum.auto()

    # User wants to select NAND flash configuration
    NAND_SELECT        = enum.auto()

    # User wants to calculate ECC for NAND flash
    NAND_CALCULATE_ECC = enum.auto()
