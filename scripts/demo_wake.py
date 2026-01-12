#!/usr/bin/env python3
"""
Wake-word PoC demonstration script.

Shows how to interact with wake-word detection system:
- Switching between PTT, hotword, and auto modes
- Enabling/disabling wake detection at runtime
- Reporting false positives and false negatives
- Querying wake-word status

Usage:
    python scripts/demo_wake.py
"""

import asyncio
import base64
import json
import sys

import websockets


async def demo_wake_modes():
    """Demonstrate wake-word mode switching."""
    uri = "ws://localhost:8000/ws"
    
    print("=== Wake-Word PoC Demo ===\n")
    
    async with websockets.connect(uri) as ws:
        # Get initial status
        print("1. Getting initial wake-word status...")
        await ws.send(json.dumps({"type": "wake.get_status"}))
        response = json.loads(await ws.recv())
        print(f"   Status: {json.dumps(response, indent=2)}\n")
        
        # Switch to hotword mode
        print("2. Switching to hotword mode...")
        await ws.send(json.dumps({"type": "wake.set_mode", "mode": "hotword"}))
        response = json.loads(await ws.recv())
        print(f"   Response: {response}\n")
        
        # Send some audio chunks (will be processed by wake detector)
        print("3. Sending audio chunks in hotword mode...")
        print("   (stub detector triggers after 32000 bytes)\n")
        
        chunk = b"\x00\x00" * 160  # 320 bytes per chunk
        for i in range(105):  # Send 105 chunks to exceed threshold
            await ws.send(json.dumps({
                "type": "audio.chunk",
                "session_id": "demo",
                "payload_base64": base64.b64encode(chunk).decode("ascii"),
            }))
            
            # Check for wake detection
            try:
                response = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.01))
                if response.get("type") == "wake.detected":
                    print(f"   ✓ Wake detected: {response}\n")
                    break
            except asyncio.TimeoutError:
                continue
        
        # Switch to PTT mode
        print("4. Switching to PTT mode...")
        await ws.send(json.dumps({"type": "wake.set_mode", "mode": "ptt"}))
        response = json.loads(await ws.recv())
        print(f"   Response: {response}\n")
        
        # Send audio in PTT mode (immediate accumulation)
        print("5. Sending audio chunk in PTT mode...")
        await ws.send(json.dumps({
            "type": "audio.chunk",
            "session_id": "demo",
            "payload_base64": base64.b64encode(chunk).decode("ascii"),
        }))
        response = json.loads(await ws.recv())
        print(f"   Response (should be stt.partial): {response}\n")
        
        # Disable wake detection at runtime
        print("6. Disabling wake detection...")
        await ws.send(json.dumps({"type": "wake.disable"}))
        response = json.loads(await ws.recv())
        print(f"   Response: {response}\n")
        
        # Re-enable wake detection
        print("7. Re-enabling wake detection...")
        await ws.send(json.dumps({"type": "wake.enable"}))
        response = json.loads(await ws.recv())
        print(f"   Response: {response}\n")
        
        # Report false positive
        print("8. Reporting false positive...")
        await ws.send(json.dumps({"type": "wake.report_false_positive"}))
        response = json.loads(await ws.recv())
        print(f"   Response: {response}\n")
        
        # Report false negative
        print("9. Reporting false negative...")
        await ws.send(json.dumps({"type": "wake.report_false_negative"}))
        response = json.loads(await ws.recv())
        print(f"   Response: {response}\n")
        
        # Get final status
        print("10. Getting final wake-word status...")
        await ws.send(json.dumps({"type": "wake.get_status"}))
        response = json.loads(await ws.recv())
        print(f"    Status: {json.dumps(response, indent=2)}\n")
        
        print("=== Demo Complete ===")
        print("\nCheck metrics at http://localhost:8000/metrics")
        print("Look for: wake_detections_total, wake_false_positives_total, wake_false_negatives_total")


async def main():
    try:
        await demo_wake_modes()
    except websockets.exceptions.WebSocketException as e:
        print(f"\n❌ WebSocket error: {e}")
        print("\nMake sure the backend is running:")
        print("  cd apps/backend")
        print("  WAKE_ENABLED=true WAKE_BACKEND=stub uvicorn m_assistant_backend.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
