"""
FareIndex India — Domestic Itinerary & Airport Validation Module
Enforces strict Indian domestic routing rules for airfare observations.
"""
from __future__ import annotations
import re
from typing import Iterable

# Comprehensive registry of Indian Civil Aviation Airport IATA codes (DGCA / AAI)
INDIAN_AIRPORTS = {
    # Major Metros & Primaries
    "DEL", "BOM", "BLR", "HYD", "MAA", "CCU",
    # Goa
    "GOI", "GOX",
    # Tier 1 & 2 Primaries & Regionals
    "COK", "CCJ", "AMD", "PNQ", "JAI", "LKO", "GAU", "IXC", "TRV", "PAT", "BBI",
    "SXR", "IXB", "IDR", "NAG", "VNS", "VTZ", "ATQ", "IXR", "CJB", "IXE",
    "DED", "RPR", "BDQ", "TIR", "STV", "TRZ", "IXZ", "IMF", "IXA", "IXL",
    "UDR", "IXJ", "HBX", "MYQ", "DMU", "IXS", "GAY", "IXU", "JLR", "RJA",
    "CNN", "BHO", "GWL", "IXD", "HDO", "AYJ", "JGA", "PBD", "BHJ", "RAJ",
    "KLH", "SHL", "DIB", "TEZ", "AJL", "ZER", "RUP", "PYG", "KNU", "BEK",
    "AGR", "PGH", "DHM", "KUU", "SLV", "BKB", "JSA", "JDH", "KQH", "NDC",
    "SAG", "SSE", "ISK", "JRG", "IXV", "DEP", "CDP", "KJB", "IXG", "IXN",
    "IXM", "TCR", "VGA", "GBI", "HSS", "IXP", "MOH", "NMB", "TNI", "SHK",
    "BUP", "BIL", "JRH", "DBR", "HJR", "IXI", "IXY", "IXH", "IXQ", "IXK",
    "IXW", "IXT",
}

# Known Foreign / International Hubs (for explicit logging & testing)
FOREIGN_TRANSIT_AIRPORTS = {
    "BAH", "CMB", "DXB", "DOH", "AUH", "SIN", "BKK", "KUL", "MCT", "SHJ",
    "KWI", "JED", "RUH", "LHR", "FRA", "CDG", "AMS", "HKG", "NRT", "ICN",
    "KTM", "DAC", "MLE", "BOM-INTL", "KHI", "LHE", "ISB", "MUC", "ZRH",
}

def is_indian_airport(airport_code: str) -> bool:
    """Returns True if the airport code is a registered Indian domestic airport."""
    if not airport_code or not isinstance(airport_code, str):
        return False
    return airport_code.strip().upper() in INDIAN_AIRPORTS

def extract_airports_from_text(
    text: str,
    known_origin: str = "",
    known_destination: str = ""
) -> list[str]:
    """
    Extracts 3-letter IATA airport codes from flight card / layover text.
    Filters out origin and destination.
    """
    if not text:
        return []
    
    # Matches uppercase 3-letter words or standard stop patterns e.g. "BOM", "BAH", "in Mumbai (BOM)"
    candidates = re.findall(r"\b([A-Z]{3})\b", text)
    
    origin_clean = known_origin.strip().upper()
    dest_clean = known_destination.strip().upper()
    
    intermediate: list[str] = []
    for code in candidates:
        code_upper = code.upper()
        # Skip currency, common words, and origin/destination
        if code_upper in ("INR", "USD", "EUR", "GBP", "AED", "BHD", "LKR", "MIN", "HRS", "SEC", "AM", "PM", "NON", "STP"):
            continue
        if code_upper == origin_clean or code_upper == dest_clean:
            continue
        if code_upper not in intermediate:
            intermediate.append(code_upper)
            
    return intermediate

def validate_itinerary(
    origin: str,
    destination: str,
    stops_str: str,
    intermediate_airports: list[str] | None = None
) -> tuple[str, str, list[str]]:
    """
    Validates whether an itinerary is strictly Indian domestic:
    
    Returns (eligibility, reason, full_itinerary):
    - eligibility: "VALID", "INVALID", or "UNKNOWN"
    - reason: "DOMESTIC_ITINERARY", "INTERNATIONAL_TRANSIT", "ROUTING_NOT_VERIFIED", "INVALID_ORIGIN_DESTINATION"
    - full_itinerary: list of airport codes [origin, ..., destination]
    """
    origin_code = str(origin).strip().upper()
    dest_code = str(destination).strip().upper()
    
    # 1. Verify Origin and Destination are Indian domestic airports
    if not is_indian_airport(origin_code) or not is_indian_airport(dest_code):
        return (
            "INVALID",
            "INVALID_ORIGIN_DESTINATION",
            [origin_code, dest_code]
        )
        
    stops_lower = str(stops_str or "").strip().lower()
    is_nonstop = any(kw in stops_lower for kw in ("nonstop", "non-stop", "0 stop", "0 stops", "direct"))
    
    # 2. Non-stop flight between two Indian airports
    if is_nonstop:
        return (
            "VALID",
            "DOMESTIC_ITINERARY",
            [origin_code, dest_code]
        )
        
    # 3. Connecting flight (1+ stops)
    inter_list = [str(a).strip().upper() for a in (intermediate_airports or []) if a]
    
    if not inter_list:
        # If stops indicate connection but no intermediate airports could be established -> fail closed
        return (
            "UNKNOWN",
            "ROUTING_NOT_VERIFIED",
            [origin_code, dest_code]
        )
        
    full_itinerary = [origin_code] + inter_list + [dest_code]
    
    # 4. Verify every intermediate airport is domestic
    for airport in inter_list:
        if not is_indian_airport(airport):
            return (
                "INVALID",
                "INTERNATIONAL_TRANSIT",
                full_itinerary
            )
            
    return (
        "VALID",
        "DOMESTIC_ITINERARY",
        full_itinerary
    )
