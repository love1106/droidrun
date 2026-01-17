#!/usr/bin/env python3
"""
Test a single command through chat-phone logic.
Usage: python test-command.py "open tiktok"
"""

import asyncio
import os
import sys
import re

# Load API key from .env file
from dotenv import load_dotenv
load_dotenv()

if not os.environ.get("GOOGLE_API_KEY"):
    print("❌ GOOGLE_API_KEY not set. Create .env file or export GOOGLE_API_KEY=...")
    sys.exit(1)

SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2400

APP_PACKAGES = {
    'tiktok': 'com.ss.android.ugc.trill',
    'facebook': 'com.facebook.katana',
    'zalo': 'com.zing.zalo',
    'settings': 'com.android.settings',
    'youtube': 'com.google.android.youtube',
}

def find_app_package(app_name: str) -> str | None:
    app_name_lower = app_name.lower().strip()
    if app_name_lower in APP_PACKAGES:
        return APP_PACKAGES[app_name_lower]
    for name, pkg in APP_PACKAGES.items():
        if app_name_lower in name or name in app_name_lower:
            return pkg
    return None

async def do_search(tools, keyword: str, elements: list):
    """Perform search in current app."""
    print(f"   🔍 Searching for: {keyword}")

    # Step 1: Find and tap search button/icon
    search_tapped = False
    for e in elements:
        text = e.get('text', '').lower()
        cls = e.get('className', '').lower()
        idx = e.get('index', 0)
        if ('tìm kiếm' in text or 'search' in text) and ('image' in cls or 'button' in cls):
            await tools.tap(idx)
            search_tapped = True
            print(f"   ✅ Opened search")
            await asyncio.sleep(1)
            break

    if not search_tapped:
        print(f"   ❌ Search button not found")
        return

    # Step 2: Get new state and find search input
    ui_xml, current_app, elements, memory = await tools.get_state()

    # Step 3: Find EditText and type keyword
    for e in elements:
        cls = e.get('className', '').lower()
        idx = e.get('index', 0)
        if 'edittext' in cls:
            await tools.input_text(keyword, index=idx, clear=True)
            print(f"   ✅ Typed: {keyword}")
            await asyncio.sleep(1)

            # Step 4: Get suggestions and tap matching one
            ui_xml, current_app, elements, memory = await tools.get_state()
            for se in elements:
                se_text = se.get('text', '').lower()
                se_idx = se.get('index', 0)
                if keyword.lower() in se_text and 'textlayout' in se.get('className', '').lower():
                    await tools.tap(se_idx)
                    print(f"   ✅ Selected: {se.get('text', '')}")
                    return

            # Fallback: tap search button
            for se in elements:
                if 'tìm kiếm' in se.get('text', '').lower() and 'button' in se.get('className', '').lower():
                    await tools.tap(se.get('index', 0))
                    print(f"   ✅ Tapped search button")
                    return
            break

async def main():
    if len(sys.argv) < 2:
        print('Usage: python test-command.py "your command"')
        sys.exit(1)

    goal = sys.argv[1]
    print(f"🎯 Command: {goal}")

    from google import genai
    from droidrun.tools.android import AdbTools

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    tools = AdbTools()
    await tools.connect()
    print("✅ Connected")

    # Get state
    ui_xml, current_app, elements, memory = await tools.get_state()
    print(f"📱 Current app: {current_app}")
    print(f"🔢 Elements: {len(elements)}")

    # Build prompt
    elements_str = "\n".join([f"[{e.get('index', i+1)}] {e.get('text', '')} ({e.get('className', '')})" for i, e in enumerate(elements[:20])])

    # App context hints
    app_hints = ""
    if "trill" in current_app.lower() or "tiktok" in current_app.lower():
        app_hints = """
TikTok commands:
- Next video → swipe up
- Previous video → swipe down
- Like → tap heart icon
- Comment → tap comment icon
- Search for something → search <keyword>
"""

    prompt_text = f"""You are an Android phone automation assistant.

USER REQUEST: {goal}

Current app: {current_app or 'Home'}
UI elements:
{elements_str}
{app_hints}
AVAILABLE COMMANDS (reply with EXACTLY ONE):
- open_app <app_name> → Open an app
- tap <index> → Tap element by index
- back → Go back
- home → Go to home screen
- swipe up/down/left/right → Swipe gesture
- input_text <text> → Type text
- search <keyword> → Search in current app (e.g., search minhshopvnbinhthanh)

IMPORTANT: For search requests, use: search <keyword>
"""

    print(f"\n📤 Sending to Gemini...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_text
    )

    if response.text is None:
        print("❌ Empty response from Gemini")
        return

    reply = response.text.strip().split('\n')[0]
    print(f"📥 Gemini reply: {reply}")

    # Execute action
    reply_lower = reply.lower()

    if reply_lower.startswith("open_app"):
        app_name = reply.split(" ", 1)[1] if " " in reply else ""
        package = find_app_package(app_name)
        if package:
            print(f"📲 Opening {app_name} ({package})...")
            result = await tools.start_app(package)
            print(f"✅ Done: {result}")
        else:
            print(f"❌ App not found: {app_name}")

    elif reply_lower.startswith("tap"):
        index = int(reply.split()[1])
        print(f"👆 Tapping element {index}...")
        result = await tools.tap(index)
        print(f"✅ Done")

    elif reply_lower == "back":
        await tools.back()
        print("✅ Pressed back")

    elif reply_lower == "home":
        await tools.press_key(3)
        print("✅ Pressed home")

    elif "swipe" in reply_lower:
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        dist = SCREEN_HEIGHT // 3
        if "up" in reply_lower:
            await tools.swipe(cx, cy + dist, cx, cy - dist, 300)
            print("✅ Swiped up")
        elif "down" in reply_lower:
            await tools.swipe(cx, cy - dist, cx, cy + dist, 300)
            print("✅ Swiped down")

    elif reply_lower.startswith("search"):
        keyword = reply.split(" ", 1)[1] if " " in reply else ""
        if keyword:
            await do_search(tools, keyword, elements)
        else:
            print("❌ No keyword provided")

    else:
        print(f"🤖 Response: {reply}")

if __name__ == "__main__":
    asyncio.run(main())
