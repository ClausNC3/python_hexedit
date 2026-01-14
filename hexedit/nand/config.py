from dataclasses import dataclass
from typing import List, Tuple
from ..ecc.type import ECCType

@dataclass
class NANDFlashConfig:
    name: str
    data_ranges: List[Tuple[int, int]]  # Liste af (start, end) tuples
    data_size: int
    ecc_ranges: List[Tuple[int, int]]
    ecc_size: int
    ecc_type: ECCType
    bbm_ranges: List[Tuple[int, int]]  # Bad Block Management
    bbm_size: int
    padding_ranges: List[Tuple[int, int]]
    padding_size: int
    page_ranges: List[Tuple[int, int]]
    page_size: int
    page_padding_ranges: List[Tuple[int, int]]
    page_padding_size: int

    
NAND_CONFIGS = [
    NANDFlashConfig(
        name="Test_BCH",        # K9F1208U0C (VW E-Call)
        data_ranges=[(0x000, 0x12B), (0x12D, 0x200)],
        data_size=512,
        ecc_ranges=[(0x201, 0x20D)],
        ecc_size=13,
        ecc_type=ECCType.BCH,
        bbm_ranges=[(0x12C, 0x12C)],
        bbm_size=1,
        padding_ranges=[(0x20E, 0x20F)],
        padding_size=2,
        
        page_ranges=[(0x000, 0x20F)],
        page_size=512 + 16,
        page_padding_ranges=[],
        page_padding_size=0
    ),
    NANDFlashConfig(
        name="Test_Hamming512",
        data_ranges=[(0x000, 0x1FF)],
        data_size=512,
        ecc_ranges=[(0x20D, 0x20F)],
        ecc_size=3,
        ecc_type=ECCType.HAMMING,
        bbm_ranges=[],
        bbm_size=0,
        padding_ranges=[(0x200, 0x20C)],
        padding_size=13,
        
        page_ranges=[(0x000, 0x20F)],
        page_size=512 + 16,
        page_padding_ranges=[],
        page_padding_size=0
    ),
    NANDFlashConfig(
        name="Test_Hamming256",     # NAND128W3A2BN6 (Audi Telemodul)
        data_ranges=[(0x000, 0x0FF), (0x100, 0x1FF)],
        data_size=512,
        ecc_ranges=[(0x20A, 0x20C), (0x20D, 0x20F)],
        ecc_size=6,
        ecc_type=ECCType.HAMMING,
        bbm_ranges=[],
        bbm_size=0,
        padding_ranges=[(0x200, 0x209)],
        padding_size=10,
        
        page_ranges=[(0x000, 0x20F)],
        page_size=512+16,
        page_padding_ranges=[],
        page_padding_size=0
    ),
]

# Helper functions for working with configs
def get_config_by_name(name: str) -> NANDFlashConfig | None:
    for config in NAND_CONFIGS:
        if config.name == name:
            return config
    return None

def extract_data_from_page(page_data: bytes, config: NANDFlashConfig) -> bytes:
    """Extract data bytes from a page based on config ranges"""
    result = bytearray()
    for start, end in config.data_ranges:
        result.extend(page_data[start:end + 1])
    return bytes(result)

def extract_ecc_from_page(page_data: bytes, config: NANDFlashConfig) -> bytes:
    """Extract ECC bytes from a page"""
    result = bytearray()
    for start, end in config.ecc_ranges:
        result.extend(page_data[start:end + 1])
    return bytes(result)

def extract_bbm_from_page(page_data: bytes, config: NANDFlashConfig) -> bytes:
    """Extract Bad Block Management bytes from a page"""
    result = bytearray()
    for start, end in config.bbm_ranges:
        result.extend(page_data[start:end + 1])
    return bytes(result)

def extract_padding_from_page(page_data: bytes, config: NANDFlashConfig) -> bytes:
    """Extract padding bytes from a page"""
    result = bytearray()
    for start, end in config.padding_ranges:
        result.extend(page_data[start:end + 1])
    return bytes(result)

def extract_ranges_from_page(page_data: bytes, ranges: List[Tuple[int, int]]) -> bytes:
    """Extract bytes from a page based on a list of (start, end) ranges"""
    result = bytearray()
    for start, end in ranges:
        result.extend(page_data[start:end + 1])
    return bytes(result)