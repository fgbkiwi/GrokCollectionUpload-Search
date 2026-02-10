#!/usr/bin/env python3
"""
xAI Collections Upload Diagnostic Tool
Diagnoses Cloudflare header issues and tests upload endpoints.

Usage:
    python diagnose_xai_upload.py <management_key> <collection_id>
"""
import requests
import json
import sys
import argparse
from typing import Dict, Any


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_collections_api(management_key: str, collection_id: str) -> bool:
    """Test Collections API accessibility."""
    print("[Test 1] Testing Collections API Access...")
    
    try:
        response = requests.get(
            f"https://api.x.ai/v1/collections/{collection_id}",
            headers={"Authorization": f"Bearer {management_key}"},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   CF-RAY: {response.headers.get('CF-RAY', 'N/A')}")
        print(f"   CF-IPCountry: {response.headers.get('CF-IPCountry', 'N/A')}")
        
        # Print all Cloudflare headers
        cf_headers = {k: v for k, v in response.headers.items() if k.lower().startswith('cf-')}
        if cf_headers:
            print("   Cloudflare Headers:")
            for key, value in cf_headers.items():
                # Check for non-ASCII
                has_non_ascii = any(ord(c) > 127 for c in value)
                marker = " ⚠️ NON-ASCII" if has_non_ascii else ""
                print(f"      {key}: {value}{marker}")
        
        if response.status_code == 200:
            print("   ✅ API accessible")
            data = response.json()
            print(f"   Collection Name: {data.get('name', 'N/A')}")
            return True
        else:
            print(f"   ❌ API error: {response.status_code}")
            print(f"   Response: {response.text[:300]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False


def test_minimal_upload(management_key: str, collection_id: str) -> Dict[str, Any]:
    """Attempt minimal document upload with different header strategies."""
    print("\n[Test 2] Testing Document Upload...")
    
    test_payload = {
        "collection_id": collection_id,
        "content": "Test document for diagnostic purposes - ASCII only content",
        "metadata": {
            "test": "true",
            "diagnostic": "cloudflare_header_test",
            "timestamp": "2026-02-10"
        }
    }
    
    strategies = [
        ("default", {
            "Authorization": f"Bearer {management_key}",
            "Content-Type": "application/json"
        }),
        ("cf_bypass", {
            "Authorization": f"Bearer {management_key}",
            "Content-Type": "application/json",
            "X-Forwarded-For": "8.8.8.8",
            "Accept-Encoding": "identity",
            "User-Agent": "xai-python-client/1.0"
        }),
        ("minimal", {
            "Authorization": f"Bearer {management_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        })
    ]
    
    results = {}
    
    for strategy_name, headers in strategies:
        print(f"\n   Strategy: {strategy_name}")
        print(f"   Headers: {list(headers.keys())}")
        
        try:
            response = requests.post(
                "https://api.x.ai/v1/collections/documents",
                headers=headers,
                json=test_payload,
                timeout=60
            )
            
            print(f"   Status: {response.status_code}")
            
            # Check response headers
            cf_headers = {k: v for k, v in response.headers.items() if k.lower().startswith('cf-')}
            if cf_headers:
                print("   Response CF Headers:")
                for key, value in cf_headers.items():
                    print(f"      {key}: {value}")
            
            if response.status_code == 200:
                print("   ✅ Upload SUCCESSFUL with this strategy!")
                results[strategy_name] = "success"
                return {"success": True, "strategy": strategy_name}
            else:
                print(f"   ❌ Upload failed: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                
                # Check for specific error patterns
                response_text = response.text.lower()
                if "cf-ipcity" in response_text or "cf-region" in response_text:
                    print("   🐛 CONFIRMED: Cloudflare header issue!")
                    results[strategy_name] = "cloudflare_header_error"
                elif "non-printable" in response_text or "ascii" in response_text:
                    print("   🐛 CONFIRMED: Non-ASCII character issue!")
                    results[strategy_name] = "non_ascii_error"
                else:
                    results[strategy_name] = "other_error"
        
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request error: {e}")
            results[strategy_name] = "request_error"
    
    return {"success": False, "results": results}


def check_geolocation():
    """Check your IP geolocation and CF trace data."""
    print("\n[Test 3] Checking Your Geolocation (Cloudflare Trace)...")
    
    try:
        response = requests.get("https://www.cloudflare.com/cdn-cgi/trace", timeout=10)
        trace_data = {}
        
        for line in response.text.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                trace_data[key] = value
        
        print(f"   Your IP: {trace_data.get('ip', 'N/A')}")
        print(f"   Location (Country): {trace_data.get('loc', 'N/A')}")
        print(f"   Colo (Data Center): {trace_data.get('colo', 'N/A')}")
        print(f"   Timestamp: {trace_data.get('ts', 'N/A')}")
        
        # Try to get more detailed location info
        print("\n   Checking detailed geolocation...")
        try:
            geo_response = requests.get("https://ipapi.co/json/", timeout=10)
            if geo_response.status_code == 200:
                geo_data = geo_response.json()
                city = geo_data.get('city', 'N/A')
                region = geo_data.get('region', 'N/A')
                country = geo_data.get('country_name', 'N/A')
                
                print(f"   City: {city}")
                print(f"   Region: {region}")
                print(f"   Country: {country}")
                
                # Check for non-ASCII characters
                location_str = f"{city} {region}"
                if any(ord(char) > 127 for char in location_str):
                    print("\n   ⚠️ WARNING: Your location contains non-ASCII characters!")
                    print(f"   This is likely causing Cloudflare to inject non-ASCII headers")
                    print(f"   Example non-ASCII chars: {[c for c in location_str if ord(c) > 127]}")
                    return False
                else:
                    print("   ✅ Your location name is ASCII-safe")
                    return True
        except:
            print("   ⚠️ Could not fetch detailed geolocation")
    
    except Exception as e:
        print(f"   ❌ Geolocation check failed: {e}")
    
    return None


def test_alternative_endpoints(management_key: str, collection_id: str):
    """Test alternative upload endpoints."""
    print("\n[Test 4] Testing Alternative Endpoints...")
    
    test_content = "Test content for endpoint testing"
    
    endpoints = [
        ("https://api.x.ai/v1/collections/documents", "Standard API"),
        ("https://management-api.x.ai/v1/collections/documents", "Management API (if exists)"),
    ]
    
    for url, name in endpoints:
        print(f"\n   Testing: {name}")
        print(f"   URL: {url}")
        
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {management_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "collection_id": collection_id,
                    "content": test_content,
                    "metadata": {"test": "endpoint_test"}
                },
                timeout=30
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ This endpoint works!")
            elif response.status_code == 404:
                print("   ❌ Endpoint not found")
            else:
                print(f"   ❌ Error: {response.text[:200]}")
        
        except Exception as e:
            print(f"   ❌ Request failed: {e}")


def print_recommendations(test_results: Dict[str, Any]):
    """Print recommendations based on test results."""
    print_section("RECOMMENDATIONS")
    
    if test_results.get("upload_success"):
        print("✅ Upload is working! No issues detected.")
        print(f"   Working strategy: {test_results.get('working_strategy')}")
        return
    
    print("❌ Upload is failing. Recommended actions:\n")
    
    # Check if it's a CF header issue
    if test_results.get("confirmed_cf_issue"):
        print("1. ⭐ CONFIRMED CLOUDFLARE ISSUE - Try these solutions:")
        print("   a) Use VPN from location with ASCII-only name (US, UK)")
        print("      - Recommended locations: New York, London, Seattle")
        print("   b) Use official xai-sdk if available:")
        print("      pip install xai-sdk")
        print("   c) Contact xAI support and reference this diagnostic output")
        print("   d) Request xAI to sanitize CF headers on their backend\n")
    
    if not test_results.get("api_accessible"):
        print("2. ❌ API ACCESS ISSUE:")
        print("   - Verify your Management Key is correct")
        print("   - Check Collection ID is valid")
        print("   - Ensure network connectivity to api.x.ai\n")
    
    if test_results.get("non_ascii_location"):
        print("3. ⚠️ YOUR LOCATION HAS NON-ASCII CHARACTERS:")
        print("   - Cloudflare is injecting cf-ipcity with your city name")
        print("   - xAI's gRPC backend rejects non-ASCII headers")
        print("   - Immediate workaround: Use VPN\n")
    
    print("4. 📧 CONTACT xAI SUPPORT:")
    print("   Email: support@x.ai")
    print("   Include: This diagnostic output")
    print("   Request: Fix Cloudflare header sanitization for gRPC endpoints")


def main():
    """Main diagnostic function."""
    parser = argparse.ArgumentParser(
        description="Diagnose xAI Collections upload issues (Cloudflare header bug)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
    python diagnose_xai_upload.py xai-mgmt-abc123 col_xyz789
    
This tool will:
1. Test API accessibility
2. Attempt uploads with different header strategies  
3. Check your geolocation for non-ASCII characters
4. Test alternative endpoints
5. Provide actionable recommendations
        """
    )
    
    parser.add_argument("management_key", help="Your xAI Management Key")
    parser.add_argument("collection_id", help="Target Collection ID")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    print_section("xAI Collections Upload Diagnostic Tool")
    print("This tool diagnoses Cloudflare cf-ipcity header issues")
    print(f"Date: 2026-02-10\n")
    print(f"Management Key: {args.management_key[:15]}...")
    print(f"Collection ID: {args.collection_id}")
    
    # Run tests
    test_results = {}
    
    # Test 1: API Access
    test_results["api_accessible"] = test_collections_api(
        args.management_key, 
        args.collection_id
    )
    
    # Test 2: Upload attempts
    upload_result = test_minimal_upload(
        args.management_key,
        args.collection_id
    )
    test_results["upload_success"] = upload_result.get("success", False)
    test_results["working_strategy"] = upload_result.get("strategy")
    test_results["confirmed_cf_issue"] = any(
        "cloudflare" in str(v).lower() or "non_ascii" in str(v).lower()
        for v in upload_result.get("results", {}).values()
    )
    
    # Test 3: Geolocation
    geo_safe = check_geolocation()
    test_results["non_ascii_location"] = (geo_safe == False)
    
    # Test 4: Alternative endpoints
    if not test_results["upload_success"]:
        test_alternative_endpoints(args.management_key, args.collection_id)
    
    # Print recommendations
    print_recommendations(test_results)
    
    print_section("Diagnostic Complete")
    
    if test_results["upload_success"]:
        print("✅ Your setup is working correctly!")
        return 0
    else:
        print("❌ Issues detected. See recommendations above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
