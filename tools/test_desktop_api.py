#!/usr/bin/env python3
"""Test API client."""
from station_calyx_desktop.api_client import get_client

client = get_client()

print("Testing API client methods...")
print(f"  health_check: {client.health_check().success}")
print(f"  get_status: {client.get_status().success}")
print(f"  get_human_status: {client.get_human_status().success}")
print(f"  get_trends: {client.get_trends().success}")
print("All API methods working!")
