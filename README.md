# hexedit

`hexedit` is a Hex editor.

## Installation

### From source

```console
$ git clone https://github.com/ClausNC3/python_hexedit.git
$ cd python_hexedit
$ pip install .
```

### Development installation

For development, install in editable mode:

```console
$ pip install -e .
```

## Usage

```console
$ hexedit -h                 
usage: hexedit [-h] [-kf FORMAT] [file]

hexedit: A Python-based HEX Editor

positional arguments:
  file        Path to binary file

options:
  -h, --help  show this help message and exit
  --version   show program's version number and exit
```

Examples:

```console
$ hexedit
$ hexedit ../../dump.bin
$ python3 __main__.py ../../program.exe
```

## Screenshots

### Main Window


## Requirements

 * Python3.8+ with tkinter

## Contributions

Contributions in the form of pull requests, comments, suggestions and issue reports are welcome! 
