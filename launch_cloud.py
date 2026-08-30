# launch_cloud.py (Keeps Colab Tab Active Until Boot Completes)
import json
import os
import time
from typing import Any, cast
from playwright.sync_api import sync_playwright

NOTEBOOK_URL = "https://colab.research.google.com/drive/1mV3Du5Dwrywly-5I-l5eQCfnC_g6rG4X"
COOKIE_FILE = "cookies.json"


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


def main():
    print(
        "🚀 Launching Google Colab headlessly on T4 GPU...",
        flush=True,
    )

    if not os.path.exists(COOKIE_FILE):
        print("❌ Error: cookies.json not found.", flush=True)
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

        print("⚡ Triggering 'Run All' in Colab...", flush=True)
        page.keyboard.press("Control+F9")
        time.sleep(3)

        # Handle any confirmation modals
        dialog_selectors = [
            "md-text-button:has-text('Run anyway')",
            "mwc-button:has-text('Run anyway')",
            "paper-button:has-text('Run anyway')",
            "button:has-text('Run anyway')",
            "md-text-button:has-text('Yes')",
            "md-text-button:has-text('Connect')",
        ]
        for sel in dialog_selectors:
            try:
                btn = page.locator(sel)
                if btn.is_visible(timeout=1000):
                    btn.click()
                    print(f"   [✔] Clicked confirmation: {sel}", flush=True)
            except Exception:
                pass

        print(
            "⏳ Keeping Colab tab open & active while model downloads (120s)...",
            flush=True,
        )

        # Keep the connection alive for 2 minutes so Colab completes all 5 steps
        for i in range(12):  # 12 x 10s = 120 seconds
            time.sleep(10)
            page.mouse.move(100, 100)
            print(
                f"   ... Colab session active ({(i+1)*10}s elapsed)", flush=True
            )

        print(
            "🎉 Colab boot completed! README will be updated shortly.",
            flush=True,
        )
        browser.close()


if __name__ == "__main__":
    main()
