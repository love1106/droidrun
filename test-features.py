#!/usr/bin/env python3
"""
Test basic phone control features and report what works/fails.
"""

import asyncio
import os
import sys

# Load API key from .env file
from dotenv import load_dotenv
load_dotenv()

async def main():
    from droidrun.tools.android import AdbTools

    tools = AdbTools()
    await tools.connect()
    print("✅ Connected to device\n")

    # Get screen size
    size_output = await tools.device.shell("wm size")
    if "Physical size:" in size_output:
        size_str = size_output.split("Physical size:")[-1].strip()
        width, height = map(int, size_str.split("x"))
        print(f"📐 Screen: {width}x{height}\n")
    else:
        width, height = 1080, 2400

    results = []

    # Test 1: Get screen state
    print("🧪 Test 1: Get screen state...")
    try:
        ui_xml, current_app, elements, memory = await tools.get_state()
        print(f"   ✅ Current app: {current_app}")
        print(f"   ✅ Found {len(elements)} UI elements")
        if elements:
            print(f"   ✅ First element: {elements[0]}")
        results.append(("get_state", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("get_state", False, str(e)))

    await asyncio.sleep(1)

    # Test 2: Take screenshot
    print("\n🧪 Test 2: Take screenshot...")
    try:
        fmt, screenshot_bytes = await tools.take_screenshot()
        print(f"   ✅ Screenshot: {len(screenshot_bytes)} bytes, format: {fmt}")
        results.append(("take_screenshot", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("take_screenshot", False, str(e)))

    await asyncio.sleep(1)

    # Test 3: Tap element
    print("\n🧪 Test 3: Tap element (index 0)...")
    try:
        result = await tools.tap(0)
        print(f"   ✅ Tap result: {result[:100] if result else 'OK'}")
        results.append(("tap", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("tap", False, str(e)))

    await asyncio.sleep(1)

    # Test 4: Back button
    print("\n🧪 Test 4: Press back...")
    try:
        result = await tools.back()
        print(f"   ✅ Back result: {result[:100] if result else 'OK'}")
        results.append(("back", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("back", False, str(e)))

    await asyncio.sleep(1)

    # Test 5: Home button
    print("\n🧪 Test 5: Press home (keycode 3)...")
    try:
        result = await tools.press_key(3)
        print(f"   ✅ Home result: {result}")
        results.append(("home", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("home", False, str(e)))

    await asyncio.sleep(1)

    # Test 6: Swipe up
    print("\n🧪 Test 6: Swipe up...")
    try:
        cx, cy = width // 2, height // 2
        distance = height // 3
        result = await tools.swipe(cx, cy + distance, cx, cy - distance, 300)
        print(f"   ✅ Swipe up result: {result}")
        results.append(("swipe_up", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("swipe_up", False, str(e)))

    await asyncio.sleep(1)

    # Test 7: Swipe down
    print("\n🧪 Test 7: Swipe down...")
    try:
        cx, cy = width // 2, height // 2
        distance = height // 3
        result = await tools.swipe(cx, cy - distance, cx, cy + distance, 300)
        print(f"   ✅ Swipe down result: {result}")
        results.append(("swipe_down", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("swipe_down", False, str(e)))

    await asyncio.sleep(1)

    # Test 8: Start app (Settings)
    print("\n🧪 Test 8: Start Settings app...")
    try:
        result = await tools.start_app("com.android.settings")
        print(f"   ✅ Start app result: {result[:100] if result else 'OK'}")
        results.append(("start_app", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("start_app", False, str(e)))

    await asyncio.sleep(2)

    # Test 9: Input text (need a text field first)
    print("\n🧪 Test 9: Input text (skipped - needs text field)...")
    results.append(("input_text", None, "Skipped - needs text field"))

    # Test 10: Long press (swipe to same position)
    print("\n🧪 Test 10: Long press simulation...")
    try:
        cx, cy = width // 2, height // 2
        result = await tools.swipe(cx, cy, cx, cy, 1500)
        print(f"   ✅ Long press result: {result}")
        results.append(("long_press", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("long_press", False, str(e)))

    # Test 11: List packages
    print("\n🧪 Test 11: List installed packages...")
    try:
        packages = await tools.list_packages(include_system_apps=False)
        print(f"   ✅ Found {len(packages)} user apps")
        # Check for TikTok
        tiktok_pkgs = [p for p in packages if 'tiktok' in p.lower() or 'musically' in p.lower()]
        if tiktok_pkgs:
            print(f"   📱 TikTok packages: {tiktok_pkgs}")
        results.append(("list_packages", True, None))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("list_packages", False, str(e)))

    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    passed = sum(1 for _, ok, _ in results if ok is True)
    failed = sum(1 for _, ok, _ in results if ok is False)
    skipped = sum(1 for _, ok, _ in results if ok is None)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")

    if failed > 0:
        print("\n❌ Failed tests:")
        for name, ok, err in results:
            if ok is False:
                print(f"   - {name}: {err}")

if __name__ == "__main__":
    asyncio.run(main())
