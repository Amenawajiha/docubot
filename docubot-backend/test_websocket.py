import asyncio
import websockets
import json

# Replace with your actual values!
WORKSPACE_SLUG = "test123-48f350e7"
CHATBOT_ID = "683a3a36-df67-49ad-b4f1-c0e8a33c44f9"
SESSION_TOKEN = "EjNOdmrbIWNx6dy1o8PuMJBdRV2u6tVmNIfMuLma6U5eXYTNKBaILe8TJ0cUZAfR"

WS_URL = f"ws://localhost:8001/api/v1/chatbot/{WORKSPACE_SLUG}/{CHATBOT_ID}/chat?token={SESSION_TOKEN}"

async def chat():
    print(f"Connecting to {WS_URL}...")
    async with websockets.connect(WS_URL, additional_headers={"Origin": "http://localhost:3000"}) as websocket:
        print("✅ Connected!")
        
        # Send a message
        message = {"type": "message", "content": "For internal employees"}
        await websocket.send(json.dumps(message))
        print(f"User: {message['content']}")
        
        # Wait for the backend -> chatbot-rag -> backend response
        response = await websocket.recv()
        data = json.loads(response)
        
        print("\n🤖 Assistant Response:")
        print(f"Raw data: {json.dumps(data, indent=2)}")
        print(f"Message: {data.get('content')}")
        print(f"Confidence: {data.get('confidence')}")
        print(f"Time taken: {data.get('execution_time_ms')}ms")

asyncio.run(chat())
