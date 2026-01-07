"""Hamming Error Correction Code implementation.

Hamming codes are a family of linear error-correcting codes that can detect
and correct single-bit errors. They are widely used in NAND flash memory.

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

# Column parity lookup table for Hamming ECC
COLUMN_PARITY_TABLE = [
    0x00, 0x55, 0x59, 0x0c, 0x65, 0x30, 0x3c, 0x69,  0x69, 0x3c, 0x30, 0x65, 0x0c, 0x59, 0x55, 0x00,
    0x95, 0xc0, 0xcc, 0x99, 0xf0, 0xa5, 0xa9, 0xfc,  0xfc, 0xa9, 0xa5, 0xf0, 0x99, 0xcc, 0xc0, 0x95,
    0x99, 0xcc, 0xc0, 0x95, 0xfc, 0xa9, 0xa5, 0xf0,  0xf0, 0xa5, 0xa9, 0xfc, 0x95, 0xc0, 0xcc, 0x99,
    0x0c, 0x59, 0x55, 0x00, 0x69, 0x3c, 0x30, 0x65,  0x65, 0x30, 0x3c, 0x69, 0x00, 0x55, 0x59, 0x0c,
    0xa5, 0xf0, 0xfc, 0xa9, 0xc0, 0x95, 0x99, 0xcc,  0xcc, 0x99, 0x95, 0xc0, 0xa9, 0xfc, 0xf0, 0xa5,
    0x30, 0x65, 0x69, 0x3c, 0x55, 0x00, 0x0c, 0x59,  0x59, 0x0c, 0x00, 0x55, 0x3c, 0x69, 0x65, 0x30,
    0x3c, 0x69, 0x65, 0x30, 0x59, 0x0c, 0x00, 0x55,  0x55, 0x00, 0x0c, 0x59, 0x30, 0x65, 0x69, 0x3c,
    0xa9, 0xfc, 0xf0, 0xa5, 0xcc, 0x99, 0x95, 0xc0,  0xc0, 0x95, 0x99, 0xcc, 0xa5, 0xf0, 0xfc, 0xa9,

    0xa9, 0xfc, 0xf0, 0xa5, 0xcc, 0x99, 0x95, 0xc0,  0xc0, 0x95, 0x99, 0xcc, 0xa5, 0xf0, 0xfc, 0xa9,
    0x3c, 0x69, 0x65, 0x30, 0x59, 0x0c, 0x00, 0x55,  0x55, 0x00, 0x0c, 0x59, 0x30, 0x65, 0x69, 0x3c,
    0x30, 0x65, 0x69, 0x3c, 0x55, 0x00, 0x0c, 0x59,  0x59, 0x0c, 0x00, 0x55, 0x3c, 0x69, 0x65, 0x30,
    0xa5, 0xf0, 0xfc, 0xa9, 0xc0, 0x95, 0x99, 0xcc,  0xcc, 0x99, 0x95, 0xc0, 0xa9, 0xfc, 0xf0, 0xa5,
    0x0c, 0x59, 0x55, 0x00, 0x69, 0x3c, 0x30, 0x65,  0x65, 0x30, 0x3c, 0x69, 0x00, 0x55, 0x59, 0x0c,
    0x99, 0xcc, 0xc0, 0x95, 0xfc, 0xa9, 0xa5, 0xf0,  0xf0, 0xa5, 0xa9, 0xfc, 0x95, 0xc0, 0xcc, 0x99,
    0x95, 0xc0, 0xcc, 0x99, 0xf0, 0xa5, 0xa9, 0xfc,  0xfc, 0xa9, 0xa5, 0xf0, 0x99, 0xcc, 0xc0, 0x95,
    0x00, 0x55, 0x59, 0x0c, 0x65, 0x30, 0x3c, 0x69,  0x69, 0x3c, 0x30, 0x65, 0x0c, 0x59, 0x55, 0x00,
]

# Bit count lookup table
COUNT_BITS_TABLE = [
    0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    4, 5, 5, 6, 5, 6, 6, 7, 5, 6, 6, 7, 6, 7, 7, 8
]

def hweight8(byte):
    return COUNT_BITS_TABLE[byte]

def calculate_hamming_ecc(data: bytes, ecc_size: int) -> bytes:
    """Calculate Hamming ECC for data.

    This implementation uses standard Hamming codes for NAND flash,
    typically operating on 256 or 512 byte blocks.

    Args:
        data: Input data bytes
        ecc_size: Expected ECC size in bytes (typically 3 or 6 bytes)

    Returns:
        Hamming ECC bytes
    """

    if len(data) == 0:
        return b'\x00' * ecc_size

    ecc_result = bytearray(ecc_size)

    if ecc_size == 3 and len(data) == 512:
        ecc_result = _calculate_hamming_512(data)
    elif ecc_size == 6 and len(data) == 512:
        ecc_result = _calculate_hamming_256(data) + _calculate_hamming_256(data[256:])

    return bytes(ecc_result)

# Calculate the ECC for a 512-byte block of data
def _calculate_hamming_512(data: bytes) -> bytes:
    """Calculate 3-byte Hamming ECC for 512 bytes of data.

    Uses column and line parity calculation common in NAND flash.

    Args:
        data: 512 bytes of input data

    Returns:
        3 bytes of ECC data
    """
    ecc = bytearray(3)
    col_parity = 0
    line_parity = 0
    line_parity_prime = 0

    for i in range(512):
        b = COLUMN_PARITY_TABLE[data[i]]
        col_parity ^= b

        if (b & 0x01):
            line_parity ^= i
            line_parity_prime ^= ~i

    t = 0
    if (line_parity & 0x08):
        t |= 0x80
    if (line_parity_prime & 0x08):
        t |= 0x40
    if (line_parity & 0x04):
        t |= 0x20
    if (line_parity_prime & 0x04):
        t |= 0x10
    if (line_parity & 0x02):
        t |= 0x08
    if (line_parity_prime & 0x02):
        t |= 0x04
    if (line_parity & 0x01):
        t |= 0x02
    if (line_parity_prime & 0x01):
        t |= 0x01
    ecc[0] = t

    t = 0
    if (line_parity & 0x80):
        t |= 0x80
    if (line_parity_prime & 0x80):
        t |= 0x40
    if (line_parity & 0x40):
        t |= 0x20
    if (line_parity_prime & 0x40):
        t |= 0x10
    if (line_parity & 0x20):
        t |= 0x08
    if (line_parity_prime & 0x20):
        t |= 0x04
    if (line_parity & 0x10):
        t |= 0x02
    if (line_parity_prime & 0x10):
        t |= 0x01
    ecc[1] = t

    col_parity &= 0xfc
    if (line_parity & 0x100):
        col_parity |= 0x02
    if (line_parity_prime & 0x100):
        col_parity |= 0x01

    ecc[2] = col_parity

    return bytes(ecc)

# Calculate the ECC for a 256-byte block of data
def _calculate_hamming_256(data: bytes) -> bytes:
    """Calculate 3-byte Hamming ECC for 256 bytes of data.

    Uses column and line parity calculation common in NAND flash.

    Args:
        data: 256 bytes of input data

    Returns:
        3 bytes of ECC data
    """
    ecc = bytearray(3)
    col_parity = 0
    line_parity = 0
    line_parity_prime = 0

    for i in range(256):
        b = COLUMN_PARITY_TABLE[data[i]]
        col_parity ^= b

        if (b & 0x01):
            line_parity ^= i
            line_parity_prime ^= ~i

    ecc[2] = (~col_parity & 0xff) | 0x03

    t = 0
    if (line_parity & 0x08):
        t |= 0x80
    if (line_parity_prime & 0x08):
        t |= 0x40
    if (line_parity & 0x04):
        t |= 0x20
    if (line_parity_prime & 0x04):
        t |= 0x10
    if (line_parity & 0x02):
        t |= 0x08
    if (line_parity_prime & 0x02):
        t |= 0x04
    if (line_parity & 0x01):
        t |= 0x02
    if (line_parity_prime & 0x01):
        t |= 0x01
    ecc[1] = ~t & 0xff

    t = 0
    if (line_parity & 0x80):
        t |= 0x80
    if (line_parity_prime & 0x80):
        t |= 0x40
    if (line_parity & 0x40):
        t |= 0x20
    if (line_parity_prime & 0x40):
        t |= 0x10
    if (line_parity & 0x20):
        t |= 0x08
    if (line_parity_prime & 0x20):
        t |= 0x04
    if (line_parity & 0x10):
        t |= 0x02
    if (line_parity_prime & 0x10):
        t |= 0x01
    ecc[0] = ~t & 0xff

    return bytes(ecc)

# Correct the ECC on a 512-byte block of data
def _correct_hamming_512(data: bytes, data_ecc: bytes, calculated_ecc: bytes) -> tuple[bytes, bytes, int]:
    """Correct Hamming ECC for 512 bytes of data.

    Uses column and line parity calculation common in NAND flash.

    Args:
        data: Input data bytes (possibly corrupted)
        data_ecc: ECC bytes (possibly corrupted)
        calculated_ecc: ECC bytes (calculated from input data)

    Returns:
        Tuple of (corrected_data, corrected_ecc, num_errors_corrected)
        num_errors_corrected:
            0 = no errors
            1 = single-bit error corrected
            -1 = uncorrectable error (multiple bits)
    """

    corrected = [0] * len(data)
    corrected[:] = data

    d0 = data_ecc[0] ^ calculated_ecc[0]
    d1 = data_ecc[1] ^ calculated_ecc[1]
    d2 = data_ecc[2] ^ calculated_ecc[2]
        
    if (d0 | d1 | d2) == 0:
        # there is no error
        return (data, data_ecc, 0)
    
    # check for single bit error    
    if (((d0 ^ (d0 >> 1)) & 0x55) == 0x55 and
        ((d1 ^ (d1 >> 1)) & 0x55) == 0x55 and
        ((d2 ^ (d2 >> 1)) & 0x55) == 0x55):

        bit = 0
        byte = 0

        if (d1 & 0x80):
            byte |= 0x80
        if (d1 & 0x20):
            byte |= 0x40
        if (d1 & 0x08):
            byte |= 0x20
        if (d1 & 0x02):
            byte |= 0x10
        if (d0 & 0x80):
            byte |= 0x08
        if (d0 & 0x20):
            byte |= 0x04
        if (d0 & 0x08):
            byte |= 0x02
        if (d0 & 0x02):
            byte |= 0x01
        if (d2 & 0x02):
            byte |= 0x100

        if (d2 & 0x80):
            bit |= 0x04
        if (d2 & 0x20):
            bit |= 0x02
        if (d2 & 0x08):
            bit |= 0x01

        corrected[byte] ^= (1 << bit) & 0xff

        # corrected single bit error in data
        return (bytes(corrected), data_ecc, 1)

    # check for recoverable error in ECC
    if ((hweight8(d0) + hweight8(d1) + hweight8(d2)) == 1):
        # corrected single bit error in ECC
        return (data, calculated_ecc, 1)

    # unrecoverable error
    return (data, data_ecc, -1)

# Correct the ECC on a 256-byte block of data
def _correct_hamming_256(data: bytes, data_ecc: bytes, calculated_ecc: bytes) -> tuple[bytes, bytes, int]:
    """Correct Hamming ECC for 256 bytes of data.

    Uses column and line parity calculation common in NAND flash.

    Args:
        data: Input data bytes (possibly corrupted)
        data_ecc: ECC bytes (possibly corrupted)
        calculated_ecc: ECC bytes (calculated from input data)

    Returns:
        Tuple of (corrected_data, corrected_ecc, num_errors_corrected)
        num_errors_corrected:
            0 = no errors
            1 = single-bit error corrected
            -1 = uncorrectable error (multiple bits)
    """

    corrected = [0] * len(data)
    corrected[:] = data

    d1 = data_ecc[0] ^ calculated_ecc[0]
    d0 = data_ecc[1] ^ calculated_ecc[1]
    d2 = data_ecc[2] ^ calculated_ecc[2]
        
    if (d0 | d1 | d2) == 0:
        # there is no error
        return (data, data_ecc, 0)
    
    # check for single bit error    
    if (((d0 ^ (d0 >> 1)) & 0x55) == 0x55 and
        ((d1 ^ (d1 >> 1)) & 0x55) == 0x55 and
        ((d2 ^ (d2 >> 1)) & 0x54) == 0x54):

        bit = 0
        byte = 0

        if (d1 & 0x80):
            byte |= 0x80
        if (d1 & 0x20):
            byte |= 0x40
        if (d1 & 0x08):
            byte |= 0x20
        if (d1 & 0x02):
            byte |= 0x10
        if (d0 & 0x80):
            byte |= 0x08
        if (d0 & 0x20):
            byte |= 0x04
        if (d0 & 0x08):
            byte |= 0x02
        if (d0 & 0x02):
            byte |= 0x01

        if (d2 & 0x80):
            bit |= 0x04
        if (d2 & 0x20):
            bit |= 0x02
        if (d2 & 0x08):
            bit |= 0x01

        corrected[byte] ^= (1 << bit) & 0xff

        # corrected single bit error in data
        return (bytes(corrected), data_ecc, 1)

    # check for recoverable error in ECC
    if ((hweight8(d0) + hweight8(d1) + hweight8(d2)) == 1):
        # corrected single bit error in ECC
        return (data, calculated_ecc, 1)

    # unrecoverable error
    return (data, data_ecc, -1)

def verify_hamming_ecc(data: bytes, ecc: bytes) -> bool:
    """Verify Hamming ECC for data.

    Args:
        data: Input data bytes
        ecc: ECC bytes to verify

    Returns:
        True if ECC is valid, False otherwise
    """

    calculated_ecc = calculate_hamming_ecc(data, len(ecc))
    return calculated_ecc == ecc


def correct_hamming_errors(data: bytes, ecc: bytes) -> tuple[bytes, int]:
    """Correct errors in data using Hamming ECC.

    Hamming codes can correct single-bit errors and detect double-bit errors.

    Args:
        data: Input data bytes (possibly corrupted)
        ecc: ECC bytes

    Returns:
        Tuple of (corrected_data, num_errors_corrected)
        num_errors_corrected:
            0 = no errors
            1 = single-bit error corrected
            -1 = uncorrectable error (multiple bits)
    """

    if len(data) == 0:
        return data, 0

    corrected_data = bytearray(data)
    corrected_ecc = bytearray(ecc)
    total_corrections = 0

    if len(ecc) == 3 and len(data) == 512:
        corrected_data, corrected_ecc, total_corrections = _correct_hamming_512(data, ecc, _calculate_hamming_512(data))
    elif len(ecc) == 6 and len(data) == 512:
        corrected_data, corrected_ecc, total_corrections = _correct_hamming_256(data[0:256], ecc[0:3], _calculate_hamming_256(data))
        temp_data, temp_ecc, temp_corrections = _correct_hamming_256(data[256:], ecc[3:], _calculate_hamming_256(data[256:]))
        corrected_data += temp_data
        corrected_ecc += temp_ecc
        total_corrections += temp_corrections

    return bytes(corrected_data), total_corrections
