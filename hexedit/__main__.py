"""A HEX Editor GUI in Python.

Source:
    https://github.com/ClausNC3/python_hexedit

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
import argparse

from .application import Application
from .common import *

def main() -> None:
    parser = argparse.ArgumentParser(description='hexedit: A Python-based HEX Editor')
    parser.add_argument('file', action="store", nargs='?', default = None, help='Path to binary file')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=get_version()))
    args = parser.parse_args()

    app = Application(args.file)
    
    app.run()

if __name__ == "__main__":
    main()
