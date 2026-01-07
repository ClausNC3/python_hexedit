"""BCH (Bose–Chaudhuri–Hocquenghem) Error Correction Code implementation.

BCH codes form a class of cyclic error-correcting codes that are constructed
using polynomials over a finite field (Galois field).

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
from bchlib import BCH


def calculate_bch_ecc(data: bytes, ecc_size: int) -> bytes:
    """Calculate BCH ECC for data using bchlib.

    Args:
        data: Input data bytes
        ecc_size: Expected ECC size in bytes

    Returns:
        BCH ECC bytes
    """
    # Determine BCH parameters based on ECC size
    # Common NAND flash configurations:
    # - 8-bit ECC: 13 bytes for 512 bytes data (t=8, m=13)
    # - 24-bit ECC: 42 bytes for 1024 bytes data (t=24)

    # Map ECC size to appropriate t and m values
    # For standard NAND flash with 512 byte pages and 13 byte ECC: t=8, m=13
    '''if ecc_size == 13 and len(data) == 512:
        # Test config: 512 bytes data, 13 bytes ECC
        t = 8
        m = 13'''
    if ecc_size <= 7:
        t = 4
        m = 13
    elif ecc_size <= 13:
        t = 8
        m = 13
    elif ecc_size <= 21:
        t = 12
        m = 14
    elif ecc_size <= 42:
        t = 24
        m = 14
    else:
        t = 32
        m = 15

    # Create BCH instance with t (error correction bits) and m (Galois field parameter)
    bch = BCH(t, m=m)

    # Encode the data to get ECC
    ecc = bch.encode(data)

    # Pad or truncate to match expected size
    if len(ecc) < ecc_size:
        ecc = ecc + b'\x00' * (ecc_size - len(ecc))
    elif len(ecc) > ecc_size:
        ecc = ecc[:ecc_size]

    return ecc


def verify_bch_ecc(data: bytes, ecc: bytes) -> bool:
    """Verify BCH ECC for data.

    Args:
        data: Input data bytes
        ecc: ECC bytes to verify

    Returns:
        True if ECC is valid, False otherwise
    """
    calculated_ecc = calculate_bch_ecc(data, len(ecc))
    return calculated_ecc == ecc


def correct_bch_errors(data: bytes, ecc: bytes) -> tuple[bytes, int]:
    """Correct errors in data using BCH ECC.

    Args:
        data: Input data bytes (possibly corrupted)
        ecc: ECC bytes

    Returns:
        Tuple of (corrected_data, num_errors_corrected)
    """
    ecc_size = len(ecc)

    # Determine t and m values based on ECC size and data size
    '''if ecc_size == 13 and len(data) == 512:
        t = 8
        m = 13'''
    if ecc_size <= 7:
        t = 4
        m = 13
    elif ecc_size <= 13:
        t = 8
        m = 13
    elif ecc_size <= 21:
        t = 12
        m = 14
    elif ecc_size <= 42:
        t = 24
        m = 14
    else:
        t = 32
        m = 15

    bch = BCH(t, m=m)

    # First use decode to check if there are errors
    # Then use correct to fix them if needed

    # Check if there are errors
    num_errors = bch.decode(data, ecc)

    if num_errors < 0:
        # Too many errors to correct
        return data, -1

    # If errors found, correct them
    if num_errors != 0:
        data_part = bytearray(data)
        ecc_part = bytearray(ecc)
        bch.correct(data_part, ecc_part)
        return bytes(data_part), num_errors

    return data, num_errors
