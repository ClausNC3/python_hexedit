"""Common definitions for the package.

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
import importlib.resources
from typing import List
from collections import namedtuple
import enum

APP_NAME = "hexedit"
PACKAGE_NAME = "hexedit"

class HexEditException(Exception):
    pass

class HexEditWarning(Exception):
    pass

class HexEditViewException(Exception):
    pass

class HexEditReparseException(Exception):
    pass

def get_version() -> str:
    try:
        from importlib import metadata
        version = metadata.version(PACKAGE_NAME)
        if not version:
            raise ValueError("Can't find version from importlib metadata")
        return version
    except (ImportError, ValueError):
        pass

    try:
        from .version import __version__ # type: ignore
        return __version__
    except ImportError:
        pass

    try:
        import setuptools_scm
        version = setuptools_scm.get_version(root="..", relative_to=__file__)
        return version
    except (ImportError, LookupError):
        pass

    return ""

class ByteRepresentation(enum.Enum):
    """Different representations of a byte array"""

    # Hex array: "30 31 32 ..."
    HEX = enum.auto()

    # Hex stream: "303132 ..."
    HEX_STREAM = enum.auto()

    # Raw Bytes: "012..."
    RAW_BYTES = enum.auto()

class HighlightType(enum.Enum):
    """Represents different highlight types"""

    # The default highlighter used when clicking an element:
    DEFAULT = enum.auto() 

    # Custom highlighters that can be used to highlight custom areas:
    CUSTOM1 = enum.auto()
    CUSTOM2 = enum.auto()
    CUSTOM3 = enum.auto()

    @classmethod
    def is_custom(cls, highlight_type: "HighlightType"):
        """Returns whether the given highlighter is a custom highlighter"""
        return highlight_type != cls.DEFAULT
    
# Details about a highlighted selection:
#  is_active (boolean): Whether the selection is currently highlighted
#  is_exact_match (boolean): If the selection is highlighted, this variable
#                            reflects whether the highlight is due to being
#                            an exact match (the user explicitly requested
#                            to highlight this range) or whether it's highlighted
#                            since the user requested to highlight a parent range.
HighlightDetails = namedtuple("HighlightDetails", "is_active is_exact_match")