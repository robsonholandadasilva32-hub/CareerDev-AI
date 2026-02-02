import sys
import json
import urllib.request
import urllib.error

DEFAULT_URL = "https://www.careerdev-ai.online"

def check_url(url, description):
    print(f"Checking {description} ({url})...")
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            data = response.read().decode('utf-8')

            print(f"✅ Status: {status}")
            try:
                json_data = json.loads(data)
                print(f"   Response: {json.dumps(json_data, indent=2)}")
                return True, json_data
            except json.JSONDecodeError:
                print(f"   Response (Text): {data[:200]}...") # Truncate if long html
                return True, data

    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} - {e.reason}")
        return False, None
    except urllib.error.URLError as e:
        print(f"❌ Connection Error: {e.reason}")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False, None

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    base_url = base_url.rstrip('/')

    print(f"Starting Health Check for: {base_url}\n")

    # 1. Check /health
    health_url = f"{base_url}/health"
    health_ok, health_data = check_url(health_url, "Health Endpoint")

    if not health_ok:
        print("\nCRITICAL: /health endpoint failed.")
        sys.exit(1)

    print("-" * 30)

    # 2. Check /api/v1/monitoring/diagnostics
    diag_url = f"{base_url}/api/v1/monitoring/diagnostics"
    diag_ok, diag_data = check_url(diag_url, "Diagnostics Endpoint")

    if not diag_ok:
        print("\nWARNING: /diagnostics endpoint failed (might be auth protected or error).")
    else:
        # Validate Diagnostics
        if isinstance(diag_data, dict):
            db_status = diag_data.get("database")
            internet_status = diag_data.get("internet")
            overall_status = diag_data.get("status")

            if db_status == "connected" and internet_status == "connected":
                print("\n✅ SYSTEM FULLY OPERATIONAL")
            else:
                print(f"\n⚠️  SYSTEM DEGRADED (Status: {overall_status})")
                if db_status != "connected":
                    print(f"   - Database: {db_status}")
                if internet_status != "connected":
                    print(f"   - Internet: {internet_status}")

    print("\nVerification Complete.")

if __name__ == "__main__":
    main()
