import argparse
import asyncio

from modules.outsmart_browser_discovery import OutSmartBrowserDiscovery


def main() -> int:
    parser = argparse.ArgumentParser(description="Attach to existing Chrome for OutSmart discovery")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    args = parser.parse_args()
    asyncio.run(OutSmartBrowserDiscovery().connect_existing_chrome(args.cdp_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
