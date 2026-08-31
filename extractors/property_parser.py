"""
Unstructured Text Extractor for Real Estate Notes & Remarks.
Extracts price figures, square footage, locality, and discount percentages from unstructured notes.
"""

import re
from typing import Dict, Any, Optional


class PropertyParser:
    def __init__(self):
        self.currency_pattern = re.compile(r'(?:INR|Rs\.?)\s*([\d,]+(?:\.\d+)?)\s*(?:Lakhs|Cr)?', re.IGNORECASE)
        self.area_pattern = re.compile(r'(\d+)\s*(?:sq\s*ft|sqft|sq\.ft)', re.IGNORECASE)
        self.location_pattern = re.compile(r'in\s+([A-Za-z\s]+?)(?:,|\.|\s+near|\s+for|$)', re.IGNORECASE)
        self.discount_pattern = re.compile(r'(?:discount|offer|save)\s*:\s*([\d\.]+)\s*%', re.IGNORECASE)

    def extract_metadata(self, raw_text: str) -> Dict[str, Any]:
        """Extracts structured values from freeform broker descriptions."""
        price_match = self.currency_pattern.search(raw_text)
        area_match = self.area_pattern.search(raw_text)
        loc_match = self.location_pattern.search(raw_text)
        disc_match = self.discount_pattern.search(raw_text)

        price = price_match.group(0).strip() if price_match else None
        area = int(area_match.group(1)) if area_match else None
        location = loc_match.group(1).strip() if loc_match else None
        discount_pct = float(disc_match.group(1)) if disc_match else 0.0

        return {
            "price_str": price,
            "area_sqft": area,
            "location": location,
            "discount_pct": discount_pct,
            "is_valid": bool(price and area and location)
        }
