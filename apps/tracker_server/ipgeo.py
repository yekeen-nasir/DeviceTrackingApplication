"""IP geolocation service."""

import os
import httpx
from typing import Dict, Any, Optional
from functools import lru_cache

from libs.core.logging import setup_logging

logger = setup_logging("tracker-server.ipgeo")

# IP geolocation provider configuration
IPGEO_PROVIDER = os.getenv("TRACKER_IPGEO_PROVIDER", "ipapi")  # ipapi, ipinfo, maxmind
IPGEO_API_KEY = os.getenv("TRACKER_IPGEO_API_KEY", "")

@lru_cache(maxsize=1000)
async def get_ip_location(ip: str) -> Dict[str, Any]:
    """
    Get location information for an IP address.
    
    Args:
        ip: IP address to lookup
        
    Returns:
        Dictionary with location data
    """
    if not ip or ip in ["127.0.0.1", "::1", "localhost"]:
        return {
            "city": "Local",
            "region": "Local",
            "country": "Local",
            "lat": None,
            "lon": None,
            "asn": None
        }
    
    try:
        if IPGEO_PROVIDER == "ipapi":
            return await _ipapi_lookup(ip)
        elif IPGEO_PROVIDER == "ipinfo":
            return await _ipinfo_lookup(ip)
        else:
            # Default to ipapi free tier
            return await _ipapi_lookup(ip)
    except Exception as e:
        logger.error(f"IP geolocation failed for {ip}: {e}")
        return {
            "city": None,
            "region": None,
            "country": None,
            "lat": None,
            "lon": None,
            "asn": None
        }

async def _ipapi_lookup(ip: str) -> Dict[str, Any]:
    """Lookup using ip-api.com (free tier)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,city,regionName,country,lat,lon,as"},
            timeout=5.0
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return {
                    "city": data.get("city"),
                    "region": data.get("regionName"),
                    "country": data.get("country"),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "asn": data.get("as", "").split(" ")[0] if data.get("as") else None
                }
    
    return {}

async def _ipinfo_lookup(ip: str) -> Dict[str, Any]:
    """Lookup using ipinfo.io."""
    headers = {}
    if IPGEO_API_KEY:
        headers["Authorization"] = f"Bearer {IPGEO_API_KEY}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://ipinfo.io/{ip}/json",
            headers=headers,
            timeout=5.0
        )
        
        if response.status_code == 200:
            data = response.json()
            loc = data.get("loc", "").split(",") if data.get("loc") else [None, None]
            return {
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
                "lat": float(loc[0]) if loc[0] else None,
                "lon": float(loc[1]) if loc[1] else None,
                "asn": data.get("org", "").split(" ")[0] if data.get("org") else None
            }
    
    return {}
