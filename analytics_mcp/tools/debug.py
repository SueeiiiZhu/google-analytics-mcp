"""Debug utilities for verifying network configuration."""

import os
import httpx
import google.auth
import google.auth.transport.requests


async def check_proxy_ip() -> dict:
    """Check the outbound IP address as seen by external services.

    Useful for verifying that proxy configuration is working correctly.
    Returns the public IP address used for outbound requests, along with
    the current proxy environment variable settings.
    """
    proxy_env = {
        "HTTPS_PROXY": os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"),
        "HTTP_PROXY": os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"),
        "GRPC_PROXY": os.environ.get("GRPC_PROXY") or os.environ.get("grpc_proxy"),
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.ipify.org?format=json", timeout=10)
            response.raise_for_status()
            ip_info = response.json()
    except Exception as e:
        return {
            "error": str(e),
            "proxy_env": proxy_env,
        }

    return {
        "outbound_ip": ip_info.get("ip"),
        "proxy_env": proxy_env,
    }


async def check_ga_connectivity() -> dict:
    """Verify connectivity to Google Analytics API.

    Obtains an access token via Application Default Credentials, then makes
    a lightweight REST call to the GA Admin API. Uses the same HTTPS_PROXY
    as check_proxy_ip, so a successful response confirms both proxy routing
    and credential validity.
    """
    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        token = creds.token

        url = "https://analyticsadmin.googleapis.com/v1beta/accountSummaries?pageSize=1"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
        if response.status_code == 200:
            data = response.json()
            summaries = data.get("accountSummaries", [])
            return {
                "connected": True,
                "accounts_found": len(summaries),
                "sample": [s.get("account") for s in summaries],
            }
        else:
            return {
                "connected": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }
