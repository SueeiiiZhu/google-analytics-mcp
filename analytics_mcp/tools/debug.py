"""Debug utilities for verifying network configuration."""

import os
import httpx
from analytics_mcp.tools.utils import create_admin_api_client


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

    Makes a lightweight GA Admin API call (list accounts) to confirm that
    requests can reach Google's servers. Since the client uses REST transport,
    the same HTTPS_PROXY used by check_proxy_ip applies here too — so if
    check_proxy_ip shows the correct proxy IP, this call goes through the
    same path.
    """
    try:
        client = create_admin_api_client()
        pager = await client.list_account_summaries()
        accounts = []
        async for summary in pager:
            accounts.append(summary.account)
            break
        return {
            "connected": True,
            "accounts_found": len(accounts),
            "sample": accounts,
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }
