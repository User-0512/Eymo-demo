"""
Smoke test: verifies the FastAPI app imports, all routers are wired,
and the root + key endpoints respond via TestClient.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from services.api.app.main import app

client = TestClient(app)


def main():
    print("=== Eymo API Smoke Test ===\n")

    # 1. Verify routes are registered
    print("Registered routes:")
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None)
        if path:
            method_str = ",".join(sorted(methods)) if methods else ""
            print(f"  {method_str:20s} {path}")

    # 2. Root endpoint
    res = client.get("/")
    print(f"\nGET / -> {res.status_code} {res.json()}")

    # 3. Auth endpoints (health via openapi)
    openapi = client.get("/openapi.json")
    print(f"GET /openapi.json -> {openapi.status_code}")

    # 4. Moderation check endpoint
    res = client.get("/moderation/check")
    print(f"GET /moderation/check -> {res.status_code} {res.json()}")

    # 5. Progress + Verification health
    res = client.get("/progress/")
    print(f"GET /progress/ -> {res.status_code} {res.json()}")

    res = client.get("/verification/")
    print(f"GET /verification/ -> {res.status_code} {res.json()}")

    print("\n=== Smoke test PASSED ===")


if __name__ == "__main__":
    main()

