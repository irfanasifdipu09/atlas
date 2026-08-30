# launch_cloud.py (Scrapes Cloudflare URL & Auto-Updates README)
import json
import os
import re
import subprocess
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


def update_readme(live_url: str):
    """Updates the repository README with the active Cloudflare link"""
    readme_content = f"""# 🤖 Atlas Autonomous AI Workspace

### 🔗 Live AI Interface:
👉 **[{live_url}]({live_url})**

---
* **Engine**: DeepSeek R1 (Reasoning) & Qwen 2.5 Coder (Tools)
* **Compute**: NVIDIA Tesla T4 GPU (16 GB VRAM)
* **Status**: 🟢 **ONLINE** *(Updated automatically on startup)*
"""
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    subprocess.run(["git", "config", "user.name", "github-actions[bot]"])
    subprocess.run([
        "git",
        "config",
        "user.email",
        "github-actions[bot]@users.noreply.github.com",
    ])
    subprocess.run(["git", "add", "README.md"])
    subprocess.run([
        "git",
        "commit",
        "-m",
        f"Update Live AI Endpoint: {live_url}",
    ])
    subprocess.run(["git", "push"])
    print(f"🎉 Successfully updated README.md with {live_url}")


def main():
    print("🚀 Launching Google Colab headlessly on T4 GPU...")

    if not os.path.exists(COOKIE_FILE):
        print("❌ Error: cookies.json not found.")
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

        print("⚡ Triggering 'Run All' cells (Control+F9)...")
        page.keyboard.press("Control+F9")
        time.sleep(3)

        # Handle 'Run anyway' dialog if it appears
        try:
            run_btn = page.locator(
                "paper-button:has-text('Run anyway'), paper-button:has-text('Yes')"
            )
            if run_btn.is_visible(timeout=5000):
                run_btn.click()
                print("   [✔] Bypassed 'Run anyway' prompt.")
        except Exception:
            pass

        print(
            "⏳ Waiting for GPU boot and model loading (checking for up to 3.5 minutes)..."
        )

        tunnel_url = None
        # Check every 6 seconds for up to 3.5 minutes (35 loops)
        for i in range(35):
            time.sleep(6)
            content = page.content()
            match = re.search(
                r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content
            )
            if match:
                tunnel_url = match.group(0)
                print(f"\n✨ [FOUND LIVE TUNNEL]: {tunnel_url}")
                break
            if i % 5 == 0:
                print(f"   ... still building runtime ({i*6}s elapsed)")

        browser.close()

        if tunnel_url:
            update_readme(tunnel_url)
        else:
            print(
                "❌ Timed out waiting for Cloudflare URL to appear in Colab output."
            )


if __name__ == "__main__":
    main()
