# launch_cloud.py (Auto-Healing & Crash Recovery)
import json
import os
import time
from typing import Any, cast
import urllib.request
from playwright.sync_api import sync_playwright

NOTEBOOK_URL = "https://colab.research.google.com/drive/1mV3Du5Dwrywly-5I-l5eQCfnC_g6rG4X"
COOKIE_FILE = "cookies.json"
ENDPOINT_CHECK_URL = "https://atlas-ai-workspace.loca.lt"


def format_cookie(c: dict) -> dict[str, Any]:
    cookie: dict[str, Any] = {
        "name": c["name"],
        "value": c["value"],
        "domain": c["domain"],
        "path": c.get("path", "/"),
        "secure": c.get("secure", True),
        "httpOnly": c.get("httpOnly", False),
    }
    if "sameSite" in c:
        s = c["sameSite"]
        if s in ["Strict", "Lax", "None"]:
            cookie["sameSite"] = s
        elif s == "no_restriction":
            cookie["sameSite"] = "None"
        elif s == "lax":
            cookie["sameSite"] = "Lax"
        elif s == "strict":
            cookie["sameSite"] = "Strict"
    return cookie


def check_server_online():
    """Checks if the localtunnel endpoint is actively responding"""
    try:
        req = urllib.request.Request(
            ENDPOINT_CHECK_URL,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Bypass-Tunnel-Reminder": "true",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception:
        return False


def main():
    print("🚀 [Cloud Runner] Starting Auto-Healing Colab Trigger...")

    if not os.path.exists(COOKIE_FILE):
        print("❌ Error: cookies.json missing.")
        return

    with open(COOKIE_FILE, "r") as f:
        raw_cookies = json.load(f)

    cookies = [format_cookie(c) for c in raw_cookies]

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cast(Any, cookies))

        page = context.new_page()
        page.goto(NOTEBOOK_URL, timeout=90000)
        page.wait_for_load_state("networkidle")
        time.sleep(5)

        # Retry loop for resilient execution
        for attempt in range(1, 4):
            print(f"\n⚡ [Attempt {attempt}/3] Triggering 'Run All' (Ctrl+F9)...")
            page.keyboard.press("Control+F9")
            time.sleep(4)

            # 1. Dismiss 'Run anyway' or 'Reconnect' dialogs if present
            try:
                dialog_btns = page.locator(
                    "paper-button:has-text('Run anyway'), paper-button:has-text('Yes'), paper-button:has-text('Reconnect')"
                )
                if dialog_btns.count() > 0:
                    dialog_btns.first.click()
                    print("   [✔] Bypassed prompt / Clicked Reconnect.")
            except Exception:
                pass

            print("⏳ Monitoring startup and checking for crash events...")

            # Wait up to 60 seconds while checking for crashes or endpoint readiness
            crashed = False
            for _ in range(30):
                time.sleep(2)
                content = page.content().lower()

                # Check if Colab crashed
                if (
                    "session crashed" in content
                    or "runtime has terminated" in content
                ):
                    print(
                        f"⚠️ Colab session crash detected on attempt {attempt}! Auto-recovering..."
                    )
                    crashed = True
                    try:
                        reconnect_btn = page.locator(
                            "paper-button:has-text('Reconnect'), colab-connect-button"
                        )
                        if reconnect_btn.is_visible(timeout=3000):
                            reconnect_btn.click()
                    except Exception:
                        page.reload()
                        time.sleep(5)
                    break

                # Check if server came online
                if check_server_online():
                    print(
                        f"\n🎉 SUCCESS: Verified {ENDPOINT_CHECK_URL} is online and operational!"
                    )
                    browser.close()
                    return

            if not crashed and check_server_online():
                break

        print("🏁 Execution phase complete.")
        browser.close()


if __name__ == "__main__":
    main()
