#!/usr/bin/env python3
"""
Interactive chat to control your Android phone with natural language.
Usage: python chat-phone.py [--vision]
"""

import asyncio
import os
import sys
import re

# Load API key from .env file
from dotenv import load_dotenv
load_dotenv()

if not os.environ.get("GOOGLE_API_KEY"):
    print("❌ GOOGLE_API_KEY not set.")
    print("   Option 1: Create .env file with: GOOGLE_API_KEY=your-api-key")
    print("   Option 2: Run: export GOOGLE_API_KEY=your-api-key")
    sys.exit(1)

# Screen dimensions (default, will be updated)
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2400

# Common app name to package mapping
APP_PACKAGES = {
    # Social
    'tiktok': 'com.ss.android.ugc.trill',
    'tik tok': 'com.ss.android.ugc.trill',
    'facebook': 'com.facebook.katana',
    'fb': 'com.facebook.katana',
    'instagram': 'com.instagram.android',
    'insta': 'com.instagram.android',
    'zalo': 'com.zing.zalo',
    'messenger': 'com.facebook.orca',
    'whatsapp': 'com.whatsapp',
    'telegram': 'org.telegram.messenger',
    'twitter': 'com.twitter.android',
    'x': 'com.twitter.android',
    'threads': 'com.instagram.barcelona',
    'snapchat': 'com.snapchat.android',

    # Google
    'youtube': 'com.google.android.youtube',
    'yt': 'com.google.android.youtube',
    'youtube music': 'com.google.android.apps.youtube.music',
    'gmail': 'com.google.android.gm',
    'chrome': 'com.android.chrome',
    'maps': 'com.google.android.apps.maps',
    'google maps': 'com.google.android.apps.maps',
    'photos': 'com.google.android.apps.photos',
    'google photos': 'com.google.android.apps.photos',
    'drive': 'com.google.android.apps.docs',
    'google drive': 'com.google.android.apps.docs',
    'calendar': 'com.google.android.calendar',
    'keep': 'com.google.android.keep',

    # System
    'settings': 'com.android.settings',
    'cài đặt': 'com.android.settings',
    'camera': 'com.android.camera',
    'máy ảnh': 'com.android.camera',
    'phone': 'com.android.dialer',
    'điện thoại': 'com.android.dialer',
    'messages': 'com.android.messaging',
    'tin nhắn': 'com.android.messaging',
    'contacts': 'com.android.contacts',
    'danh bạ': 'com.android.contacts',
    'calculator': 'com.android.calculator2',
    'máy tính': 'com.android.calculator2',
    'clock': 'com.android.deskclock',
    'đồng hồ': 'com.android.deskclock',
    'files': 'com.android.documentsui',

    # Shopping/Finance
    'shopee': 'com.shopee.vn',
    'lazada': 'com.lazada.android',
    'grab': 'com.grabtaxi.passenger',
    'gojek': 'com.gojek.app',
    'momo': 'com.mservice.momotransfer',
    'vnpay': 'com.vnpay.merchant',
    'vcb': 'com.VCB',
    'vietcombank': 'com.VCB',
    'techcombank': 'vn.com.techcombank.bb.app',
    'binance': 'com.binance.dev',

    # Entertainment
    'spotify': 'com.spotify.music',
    'netflix': 'com.netflix.mediaclient',
    'disney': 'com.disney.disneyplus',

    # Productivity
    'notion': 'notion.id',
    'slack': 'com.Slack',
    'zoom': 'us.zoom.videomeetings',
    'teams': 'com.microsoft.teams',
}

# Installed packages cache
INSTALLED_PACKAGES = set()

async def load_installed_packages(tools):
    """Load list of installed package names."""
    global INSTALLED_PACKAGES
    try:
        packages = await tools.list_packages(include_system_apps=False)
        INSTALLED_PACKAGES = set(packages)
        return INSTALLED_PACKAGES
    except:
        return set()

def find_app_package(app_name: str) -> str | None:
    """Find package name by app name."""
    app_name_lower = app_name.lower().strip()

    # Direct match in our mapping
    if app_name_lower in APP_PACKAGES:
        pkg = APP_PACKAGES[app_name_lower]
        # Check if installed
        if not INSTALLED_PACKAGES or pkg in INSTALLED_PACKAGES:
            return pkg

    # Partial match in mapping
    for name, pkg in APP_PACKAGES.items():
        if app_name_lower in name or name in app_name_lower:
            if not INSTALLED_PACKAGES or pkg in INSTALLED_PACKAGES:
                return pkg

    # Search in installed packages by keyword
    for pkg in INSTALLED_PACKAGES:
        if app_name_lower in pkg.lower():
            return pkg

    return None

async def main():
    global SCREEN_WIDTH, SCREEN_HEIGHT
    # Vision OFF by default, use --vision to enable
    vision_mode = "--vision" in sys.argv
    print("📱 Phone Chat - Control your Android with natural language")
    print(f"👁️  Vision: {'ON' if vision_mode else 'OFF'} (use 'vision on/off' to toggle)")
    print("Type 'quit' to exit\n")

    from google import genai
    from google.genai import types
    from droidrun.tools.android import AdbTools

    # Initialize
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    tools = AdbTools()
    await tools.connect()
    print("✅ Connected to device")

    # Get screen size
    try:
        size_output = await tools.device.shell("wm size")
        if "Physical size:" in size_output:
            size_str = size_output.split("Physical size:")[-1].strip()
            SCREEN_WIDTH, SCREEN_HEIGHT = map(int, size_str.split("x"))
            print(f"📐 Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    except:
        pass

    # Load installed packages
    print("📦 Loading installed apps...")
    await load_installed_packages(tools)
    print(f"📦 Found {len(INSTALLED_PACKAGES)} apps\n")

    while True:
        try:
            goal = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Bye!")
            break

        if not goal:
            continue
        if goal.lower() == "quit":
            print("👋 Bye!")
            break
        if goal.lower() == "vision on":
            vision_mode = True
            print("👁️  Vision: ON")
            continue
        if goal.lower() == "vision off":
            vision_mode = False
            print("👁️  Vision: OFF")
            continue

        # Get screen state
        ui_xml, current_app, elements, memory = await tools.get_state()

        # Build prompt - use actual element index from data (starts from 1, not 0)
        elements_str = "\n".join([f"[{e.get('index', i+1)}] {e.get('text', '')} ({e.get('className', e.get('class', ''))})" for i, e in enumerate(elements[:30])])

        # Check if user wants to open an app
        open_app_match = re.search(r'(open|mở|launch|start|chạy)\s+(.+?)(?:\s+app)?$', goal.lower())

        # App-specific hints
        app_hints = ""
        if "tiktok" in current_app.lower() or "trill" in current_app.lower():
            app_hints = """
APP CONTEXT (TikTok):
- Next video / xem video tiếp → swipe up
- Previous video / video trước → swipe down
- Like / thả tim → tap heart icon (usually right side)
- Open comments / mở bình luận → open_comments
- Close comments / đóng bình luận → close_comments
- Close modal / đóng → back
- Share / chia sẻ → tap share icon
- Follow / theo dõi → tap follow button
- Search / tìm kiếm → search <keyword> (e.g., search minhshopvnbinhthanh)
- Select video tab → select_tab Video
- Tap video #N in grid → tap_video <N> (1=first, 2=second)
"""
        elif "facebook" in current_app.lower() or "katana" in current_app.lower():
            app_hints = """
APP CONTEXT (Facebook):
- Scroll feed → swipe up/down
- Like post → tap like button
- Comment → tap comment icon
- Share → tap share icon
"""
        elif "youtube" in current_app.lower():
            app_hints = """
APP CONTEXT (YouTube):
- Next video → swipe up (shorts) or tap next
- Like → tap thumbs up
- Subscribe → tap subscribe button
- Comments → tap comments section
"""
        elif "zalo" in current_app.lower():
            app_hints = """
APP CONTEXT (Zalo):
- Open chat → tap conversation
- Send message → input_text then tap send
- Back to list → back
"""

        prompt_text = f"""You are an Android phone automation assistant.

USER REQUEST: {goal}

CURRENT STATE:
- App: {current_app or 'Home screen'}
- Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}
- UI Elements:
{elements_str}
{app_hints}
AVAILABLE COMMANDS (reply with EXACTLY ONE):
- open_app <name> → Open an app (e.g., open_app tiktok, open_app facebook, open_app settings)
- tap <index> → Tap UI element by index number
- tap_video <n> → Tap nth video thumbnail (1=first, 2=second...)
- input_text <text> → Type text
- swipe up/down/left/right → Swipe gesture
- scroll up/down → Scroll page
- back → Press back button
- home → Go to home screen
- long_press <index> → Long press element
- search <keyword> → Search for keyword in current app (TikTok, YouTube, etc.)
- select_tab <name> → Select tab by name (e.g., Video, Người dùng, Cửa hàng)
- open_comments → Open comments dialog on current video
- close_comments → Close comments dialog

RULES:
1. To open ANY app, ALWAYS use: open_app <app_name>
2. Reply with ONE command only, no explanation
3. If user asks a question, answer briefly then suggest an action
"""

        # Build content
        if vision_mode:
            fmt, screenshot_bytes = await tools.take_screenshot()
            contents = [
                types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png"),
                types.Part.from_text(text=prompt_text)
            ]
        else:
            contents = prompt_text

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents
            )

            if response.text is None:
                print("🤖 (No response - try again or rephrase)")
                print()
                continue

            reply = response.text.strip().split('\n')[0]  # Take first line only
        except Exception as e:
            print(f"❌ API Error: {e}")
            print()
            continue

        # Check if it's an action or just a response
        action_keywords = ["open_app", "start_app", "tap", "tap_video", "back", "home", "input_text", "swipe", "scroll", "long_press", "search", "select_tab", "open_comments", "close_comments"]
        is_action = any(reply.lower().startswith(kw) for kw in action_keywords)

        if is_action:
            print(f"🤖 Action: {reply}")
            reply_lower = reply.lower()

            # Execute action
            if reply_lower.startswith("open_app") or reply_lower.startswith("start_app"):
                # Extract app name from reply
                app_name = reply.split(" ", 1)[1] if " " in reply else ""

                # Step 1: Find package by app name
                package = find_app_package(app_name)

                if package:
                    # Step 2: Check if already in this app
                    if package in current_app:
                        print(f"   ✅ Already in {app_name} ({package})")
                    else:
                        try:
                            result = await tools.start_app(package)
                            print(f"   ✅ Opened {app_name} ({package})")
                        except Exception as e:
                            print(f"   ❌ Failed to open {app_name}: {e}")
                else:
                    # Fallback: try as package name directly
                    try:
                        result = await tools.start_app(app_name)
                        print(f"   ✅ Opened {app_name}")
                    except Exception as e:
                        print(f"   ❌ App '{app_name}' not found")

            elif reply_lower.startswith("tap"):
                try:
                    index = int(reply.split()[1])
                    result = await tools.tap(index)
                    print(f"   ✅ Tapped element {index}")
                except (IndexError, ValueError):
                    print(f"   ❌ Invalid tap command")

            elif reply_lower == "back":
                result = await tools.back()
                print(f"   ✅ Pressed back")

            elif reply_lower == "home":
                result = await tools.press_key(3)  # KEYCODE_HOME = 3
                print(f"   ✅ Pressed home")

            elif reply_lower.startswith("input_text"):
                text = reply.split(" ", 1)[1] if " " in reply else ""
                result = await tools.input_text(text)
                print(f"   ✅ Typed: {text}")

            elif reply_lower.startswith("swipe") or reply_lower.startswith("scroll"):
                # Calculate swipe coordinates based on direction
                cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
                distance = SCREEN_HEIGHT // 3

                if "up" in reply_lower:
                    await tools.swipe(cx, cy + distance, cx, cy - distance, 300)
                    print(f"   ✅ Swiped up")
                elif "down" in reply_lower:
                    await tools.swipe(cx, cy - distance, cx, cy + distance, 300)
                    print(f"   ✅ Swiped down")
                elif "left" in reply_lower:
                    await tools.swipe(cx + distance, cy, cx - distance, cy, 300)
                    print(f"   ✅ Swiped left")
                elif "right" in reply_lower:
                    await tools.swipe(cx - distance, cy, cx + distance, cy, 300)
                    print(f"   ✅ Swiped right")
                else:
                    print(f"   ❌ Unknown swipe direction")

            elif reply_lower.startswith("long_press"):
                try:
                    index = int(reply.split()[1])
                    # Get element coordinates
                    if index < len(elements):
                        elem = elements[index]
                        x = elem.get('x', SCREEN_WIDTH // 2)
                        y = elem.get('y', SCREEN_HEIGHT // 2)
                        # Long press = swipe to same position with long duration
                        await tools.swipe(x, y, x, y, 1500)
                        print(f"   ✅ Long pressed element {index}")
                    else:
                        print(f"   ❌ Element {index} not found")
                except (IndexError, ValueError):
                    print(f"   ❌ Invalid long_press command")

            elif reply_lower.startswith("search"):
                keyword = reply.split(" ", 1)[1] if " " in reply else ""
                if not keyword:
                    print(f"   ❌ No search keyword provided")
                else:
                    print(f"   🔍 Searching for: {keyword}")
                    try:
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
                        else:
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

                                    # Step 4: Get suggestions and tap matching one or press search
                                    ui_xml, current_app, elements, memory = await tools.get_state()
                                    suggestion_found = False
                                    for se in elements:
                                        se_text = se.get('text', '').lower()
                                        se_idx = se.get('index', 0)
                                        if keyword.lower() in se_text and 'textlayout' in se.get('className', '').lower():
                                            await tools.tap(se_idx)
                                            suggestion_found = True
                                            print(f"   ✅ Selected: {se.get('text', '')}")
                                            break

                                    if not suggestion_found:
                                        # Tap search button
                                        for se in elements:
                                            if 'tìm kiếm' in se.get('text', '').lower() and 'button' in se.get('className', '').lower():
                                                await tools.tap(se.get('index', 0))
                                                print(f"   ✅ Tapped search button")
                                                break
                                    break
                    except Exception as e:
                        print(f"   ❌ Search failed: {e}")

            elif reply_lower.startswith("tap_video"):
                try:
                    video_num = int(reply.split()[1])
                    # Find video thumbnails (FrameLayout with resourceId containing 'sq')
                    video_count = 0
                    tapped = False
                    for e in elements:
                        resource_id = e.get('resourceId', '')
                        cls = e.get('className', '')
                        if 'sq' in resource_id and 'FrameLayout' in cls:
                            video_count += 1
                            if video_count == video_num:
                                idx = e.get('index', 0)
                                await tools.tap(idx)
                                print(f"   ✅ Tapped video #{video_num} (index {idx})")
                                tapped = True
                                break
                    if not tapped:
                        print(f"   ❌ Video #{video_num} not found (only {video_count} videos visible)")
                except (IndexError, ValueError):
                    print(f"   ❌ Invalid tap_video command. Use: tap_video <number>")

            elif reply_lower.startswith("select_tab"):
                tab_name = reply.split(" ", 1)[1] if " " in reply else ""
                if not tab_name:
                    print(f"   ❌ No tab name provided")
                else:
                    tab_found = False
                    for e in elements:
                        text = e.get('text', '')
                        cls = e.get('className', '')
                        if text.lower() == tab_name.lower() and ('FrameLayout' in cls or 'TextView' in cls):
                            idx = e.get('index', 0)
                            await tools.tap(idx)
                            print(f"   ✅ Selected tab: {text}")
                            tab_found = True
                            break
                    if not tab_found:
                        print(f"   ❌ Tab '{tab_name}' not found")

            elif reply_lower == "open_comments":
                # Find and tap comment button
                comment_found = False
                for e in elements:
                    desc = e.get('contentDescription', '') or e.get('text', '')
                    if 'bình luận' in desc.lower() and 'đọc' in desc.lower():
                        idx = e.get('index', 0)
                        await tools.tap(idx)
                        print(f"   ✅ Opened comments")
                        comment_found = True
                        break
                if not comment_found:
                    # Fallback: look for comment icon by position (usually right side of screen)
                    for e in elements:
                        desc = e.get('contentDescription', '') or e.get('text', '')
                        if 'comment' in desc.lower() or 'bình luận' in desc.lower():
                            idx = e.get('index', 0)
                            await tools.tap(idx)
                            print(f"   ✅ Opened comments")
                            comment_found = True
                            break
                if not comment_found:
                    print(f"   ❌ Comment button not found")

            elif reply_lower == "close_comments":
                # Find and tap close button
                close_found = False
                for e in elements:
                    desc = e.get('contentDescription', '') or e.get('text', '')
                    if 'đóng' in desc.lower() or 'close' in desc.lower():
                        idx = e.get('index', 0)
                        await tools.tap(idx)
                        print(f"   ✅ Closed comments")
                        close_found = True
                        break
                if not close_found:
                    # Try pressing back as fallback
                    await tools.back()
                    print(f"   ✅ Closed comments (back)")

        else:
            print(f"🤖 {reply}")

        print()

if __name__ == "__main__":
    asyncio.run(main())
