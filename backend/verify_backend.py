import asyncio
import httpx
import json
import uuid

BACKEND_URL = "http://127.0.0.1:8000/api"

async def test_flow():
    email = f"test_user_{uuid.uuid4().hex[:6]}@example.com"
    password = "testpassword123"
    
    print("--- 1. Testing Signup ---")
    async with httpx.AsyncClient() as client:
        signup_res = await client.post(
            f"{BACKEND_URL}/auth/signup",
            json={"email": email, "password": password}
        )
        print(f"Signup Status: {signup_res.status_code}")
        if signup_res.status_code != 200:
            print(f"Signup Error: {signup_res.text}")
            return
        signup_data = signup_res.json()
        print(f"Signup Response: {signup_data}")
        
        print("\n--- 2. Testing Login ---")
        login_res = await client.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": email, "password": password}
        )
        print(f"Login Status: {login_res.status_code}")
        if login_res.status_code != 200:
            print(f"Login Error: {login_res.text}")
            return
        login_data = login_res.json()
        token = login_data["access_token"]
        print(f"Access Token: {token[:15]}...")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        print("\n--- 3. Testing Get Me ---")
        me_res = await client.get(f"{BACKEND_URL}/auth/me", headers=headers)
        print(f"Get Me Status: {me_res.status_code}")
        print(f"Get Me Response: {me_res.json()}")
        
        print("\n--- 4. Testing Create Conversation ---")
        conv_res = await client.post(
            f"{BACKEND_URL}/conversations",
            json={"title": "Test Chat Integration"},
            headers=headers
        )
        print(f"Create Conversation Status: {conv_res.status_code}")
        conv_data = conv_res.json()
        print(f"Conversation Data: {conv_data}")
        conv_id = conv_data["id"]
        
        print("\n--- 5. Testing List Conversations ---")
        list_res = await client.get(f"{BACKEND_URL}/conversations", headers=headers)
        print(f"List Conversations Status: {list_res.status_code}")
        print(f"Total Conversations: {len(list_res.json())}")
        
        print("\n--- 6. Testing SSE Streaming Chat (Fast Model) ---")
        chat_payload = {
            "conversation_id": conv_id,
            "message": "Hi Dushman AI, write a 3 line poem about the space voyager.",
            "model_type": "fast"
        }
        
        # Test HTTP streaming
        print("Streaming chunks:")
        async with client.stream(
            "POST",
            f"{BACKEND_URL}/chat",
            json=chat_payload,
            headers=headers,
            timeout=60.0
        ) as response:
            print(f"Streaming Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"Error reading stream: {await response.aread()}")
                return
                
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                if line.startswith("event:"):
                    print(f"\n[{line.strip()}] ", end="")
                elif line.startswith("data:"):
                    try:
                        data = json.loads(line[5:])
                        print(data.get("content", ""), end="", flush=True)
                    except json.JSONDecodeError:
                        print(f"Raw data line: {line}")
            print("\nStream finished successfully!")
            
        print("\n--- 7. Verification: Load Conversation Detail ---")
        detail_res = await client.get(f"{BACKEND_URL}/conversations/{conv_id}", headers=headers)
        print(f"Detail Status: {detail_res.status_code}")
        detail_data = detail_res.json()
        print(f"Messages count: {len(detail_data.get('messages', []))}")
        for msg in detail_data.get("messages", []):
            print(f" - {msg['role'].upper()}: {msg['content'][:50]}... (model: {msg.get('model_used')}, provider: {msg.get('provider_used')})")

if __name__ == "__main__":
    asyncio.run(test_flow())
