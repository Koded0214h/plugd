"""
WebSocket end-to-end test for plugd-websocket.onrender.com
Tests: login → start conversation → connect WS → send message → receive broadcast
"""
import asyncio
import json
import requests
import websockets

BASE   = "https://plugd-websocket.onrender.com"
WS_BASE = "wss://plugd-websocket.onrender.com"

PASS = 0
FAIL = 0

def ok(label):
    global PASS
    print(f"  PASS: {label}")
    PASS += 1

def fail(label, detail=""):
    global FAIL
    print(f"  FAIL: {label}")
    if detail:
        print(f"        {detail}")
    FAIL += 1

# ── Step 1: REST setup — create users + conversation ──────────────────────

print("\n━━━ SETUP (REST) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

def register(email, role):
    r = requests.post(f"{BASE}/api/users/auth/register/", json={
        "email": email, "first_name": "WS", "last_name": "Test",
        "role": role, "password": "TestPass123!", "password2": "TestPass123!"
    })
    return r.status_code in (200, 201, 400)  # 400 = already exists, fine

def login(email):
    r = requests.post(f"{BASE}/api/users/auth/login/", json={
        "email": email, "password": "TestPass123!"
    })
    data = r.json()
    return data.get("access"), data.get("refresh")

register("ws.user1@test.com", "customer")
register("ws.user2@test.com", "customer")

token1, _ = login("ws.user1@test.com")
token2, _ = login("ws.user2@test.com")

if not token1 or not token2:
    print("FATAL: Could not get tokens. Aborting.")
    exit(1)
print("  Tokens: OK")

# Get user2's ID
profile2 = requests.get(f"{BASE}/api/users/profile/",
    headers={"Authorization": f"Bearer {token2}"}).json()
user2_id = profile2.get("id")

# Start or reuse conversation between user1 and user2
r = requests.post(f"{BASE}/api/messaging/conversations/start/",
    headers={"Authorization": f"Bearer {token1}"},
    json={"user_id": user2_id})
conv_data = r.json()
conversation_id = conv_data.get("id")

if not conversation_id:
    print(f"FATAL: Could not get conversation ID. Response: {conv_data}")
    exit(1)
print(f"  Conversation ID: {conversation_id}")

# ── Step 2: WebSocket tests ────────────────────────────────────────────────

print("\n━━━ WEBSOCKET TESTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

async def run_tests():
    ws_url1 = f"{WS_BASE}/ws/chat/{conversation_id}/?token={token1}"
    ws_url2 = f"{WS_BASE}/ws/chat/{conversation_id}/?token={token2}"
    bad_url  = f"{WS_BASE}/ws/chat/{conversation_id}/?token=totallyinvalidtoken"

    # ── Test 1: Valid token connects successfully ──────────────────────────
    print("\n  [1] Valid token → connection accepted")
    try:
        async with websockets.connect(ws_url1) as ws:
            ok("Connected with valid JWT token")

            # ── Test 2: Send a message ─────────────────────────────────────
            print("\n  [2] Send a message")
            await ws.send(json.dumps({"message": "hello from test!"}))

            # ── Test 3: Receive the broadcast back ─────────────────────────
            print("\n  [3] Receive broadcast")
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=8)
                data = json.loads(raw)
                msg = data.get("message", {})
                if msg.get("text") == "hello from test!":
                    ok(f"Message received: '{msg['text']}'")
                else:
                    fail("Unexpected message content", str(data))

                # ── Test 4: Verify message fields ──────────────────────────
                print("\n  [4] Message shape")
                for field in ("id", "sender", "text", "created_at"):
                    if field in msg:
                        ok(f"Field '{field}' present")
                    else:
                        fail(f"Field '{field}' missing", str(msg))

            except asyncio.TimeoutError:
                fail("No message received within 8s")

    except websockets.exceptions.ConnectionClosedError as e:
        fail("Connection was closed (auth rejected?)", str(e))
    except Exception as e:
        fail("Connection failed", str(e))

    # ── Test 5: Two clients receive each other's messages ─────────────────
    print("\n  [5] Two clients — user2 receives user1's message")
    try:
        async with websockets.connect(ws_url1) as ws1, \
                   websockets.connect(ws_url2) as ws2:
            ok("Both clients connected")
            await ws1.send(json.dumps({"message": "ping from user1"}))
            try:
                # ws2 should receive the broadcast
                raw = await asyncio.wait_for(ws2.recv(), timeout=8)
                data = json.loads(raw)
                text = data.get("message", {}).get("text", "")
                if text == "ping from user1":
                    ok("User2 received user1's message via broadcast")
                else:
                    fail("User2 got unexpected content", str(data))
            except asyncio.TimeoutError:
                fail("User2 did not receive broadcast within 8s")
    except Exception as e:
        fail("Two-client test failed", str(e))

    # ── Test 6: Invalid token is rejected ─────────────────────────────────
    print("\n  [6] Invalid token → connection rejected")
    try:
        async with websockets.connect(bad_url) as ws:
            # If we get here the server accepted — that's a bug
            fail("Invalid token was accepted (should have been rejected)")
    except (websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.InvalidStatus) as e:
        ok(f"Invalid token correctly rejected ({type(e).__name__})")
    except Exception as e:
        ok(f"Invalid token rejected ({type(e).__name__})")

asyncio.run(run_tests())

print(f"\n━━━ RESULTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"  Passed: {PASS}")
print(f"  Failed: {FAIL}")
print()
if FAIL == 0:
    print("  WebSocket is fully working.")
else:
    print("  Some tests failed — see above.")
