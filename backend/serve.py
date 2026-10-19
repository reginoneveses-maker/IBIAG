"""Container entrypoint: forwarded headers are opt-in for exact proxy IPs."""
import ipaddress
import os


def server_options(environ):
    raw = environ.get("TRUSTED_PROXY_IPS", "").strip()
    peers = []
    if raw:
        for item in raw.split(","):
            # Uvicorn 0.25 matches literal addresses, not CIDRs. Reject broad
            # trust, hostnames and empty entries instead of silently trusting.
            item = item.strip()
            try:
                ipaddress.ip_address(item)
            except ValueError:
                raise ValueError("TRUSTED_PROXY_IPS must contain exact IP addresses") from None
            peers.append(item)
    return dict(host="0.0.0.0", port=int(environ.get("PORT", "8000")),
                proxy_headers=bool(peers), forwarded_allow_ips=peers, server_header=False, access_log=False)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", **server_options(os.environ))
