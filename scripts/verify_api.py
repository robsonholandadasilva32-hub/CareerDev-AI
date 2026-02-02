import urllib.request
import urllib.error
import time
import sys

TARGET_BASE = "https://www.careerdev-ai.online"
ENDPOINTS = [
    "/",
    "/health",
    "/api/v1/monitoring/diagnostics"
]

def check_endpoint(base_url, endpoint):
    url = f"{base_url.rstrip('/')}{endpoint}"
    print(f"Checking {url} ...", end=" ", flush=True)

    start_time = time.time()
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CareerDev-Verifier/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            latency = (time.time() - start_time) * 1000
            status_code = response.getcode()
            print(f"[{status_code}] - {latency:.2f}ms")
            return True, status_code, latency
    except urllib.error.HTTPError as e:
        latency = (time.time() - start_time) * 1000
        print(f"[{e.code}] - {latency:.2f}ms (HTTP Error)")
        return False, e.code, latency
    except urllib.error.URLError as e:
        latency = (time.time() - start_time) * 1000
        print(f"[ERR] - {latency:.2f}ms ({e.reason})")
        return False, 0, latency
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        print(f"[ERR] - {latency:.2f}ms ({str(e)})")
        return False, 0, latency

def main():
    print(f"Starting verification for {TARGET_BASE}\n")
    results = []

    for endpoint in ENDPOINTS:
        success, code, latency = check_endpoint(TARGET_BASE, endpoint)
        results.append((endpoint, success, code, latency))

    print("\nSummary:")
    print("-" * 60)
    print(f"{'Endpoint':<35} | {'Status':<10} | {'Latency':<10}")
    print("-" * 60)

    failures = 0
    for endpoint, success, code, latency in results:
        status_str = str(code) if code else "ERR"
        print(f"{endpoint:<35} | {status_str:<10} | {latency:.2f}ms")
        if not success and code != 401 and code != 403: # Consider 401/403 as "reachable" but auth required?
            # Request asked for 200 OK for / and /health.
            # /api/v1/monitoring/diagnostics might require auth?
            # Let's check the code for that.
            pass

    print("-" * 60)

if __name__ == "__main__":
    main()
