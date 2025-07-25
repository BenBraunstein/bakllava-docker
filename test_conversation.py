#!/usr/bin/env python3

import requests
import json
import time

# Configuration
API_BASE_URL = "http://localhost:8000"

def test_conversation_flow():
    """Test a complete conversation flow."""
    print("Testing conversation functionality...")
    
    try:
        # 1. Create a new conversation
        print("\n1. Creating new conversation...")
        response = requests.post(f"{API_BASE_URL}/api/conversation/new")
        if response.status_code != 200:
            print(f"Failed to create conversation: {response.text}")
            return False
        
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Created conversation: {session_id}")
        
        # 2. Send first message
        print("\n2. Sending first message...")
        payload = {
            "prompt": "Hello! My name is Alice. What's your name?",
            "session_id": session_id,
            "temperature": 0.7,
            "max_tokens": 100
        }
        response = requests.post(f"{API_BASE_URL}/api/text", json=payload)
        if response.status_code != 200:
            print(f"First message failed: {response.text}")
            return False
        
        result = response.json()
        print(f"Response: {result['response'][:200]}...")
        
        # 3. Send follow-up message referencing conversation
        print("\n3. Sending follow-up message...")
        payload = {
            "prompt": "Do you remember my name? What did I tell you earlier?",
            "session_id": session_id,
            "temperature": 0.7,
            "max_tokens": 100
        }
        response = requests.post(f"{API_BASE_URL}/api/text", json=payload)
        if response.status_code != 200:
            print(f"Follow-up message failed: {response.text}")
            return False
        
        result = response.json()
        print(f"Response: {result['response'][:200]}...")
        
        # 4. Get conversation history
        print("\n4. Getting conversation history...")
        response = requests.get(f"{API_BASE_URL}/api/conversation/{session_id}")
        if response.status_code != 200:
            print(f"Failed to get conversation: {response.text}")
            return False
        
        conversation = response.json()
        print(f"Conversation has {conversation['total_messages']} messages")
        for i, msg in enumerate(conversation['messages']):
            role = msg['role'].title()
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"  {i+1}. {role}: {content}")
        
        # 5. Test conversation without session (should create new one)
        print("\n5. Testing new conversation (no session_id)...")
        payload = {
            "prompt": "This should be a fresh conversation. What's my name?",
            "temperature": 0.7,
            "max_tokens": 100
        }
        response = requests.post(f"{API_BASE_URL}/api/text", json=payload)
        if response.status_code != 200:
            print(f"New conversation failed: {response.text}")
            return False
        
        result = response.json()
        new_session_id = result['session_id']
        print(f"New session created: {new_session_id}")
        print(f"Response: {result['response'][:200]}...")
        
        # 6. Clean up - delete conversations
        print("\n6. Cleaning up conversations...")
        for sid in [session_id, new_session_id]:
            response = requests.delete(f"{API_BASE_URL}/api/conversation/{sid}")
            if response.status_code == 200:
                print(f"Deleted conversation: {sid}")
            else:
                print(f"Failed to delete {sid}: {response.text}")
        
        return True
        
    except Exception as e:
        print(f"Conversation test error: {e}")
        return False

def test_conversation_with_images():
    """Test conversation with images."""
    print("\n" + "="*50)
    print("Testing conversation with images...")
    
    try:
        # Create conversation
        response = requests.post(f"{API_BASE_URL}/api/conversation/new")
        session_data = response.json()
        session_id = session_data["session_id"]
        
        # First, text message
        print("1. Sending text message...")
        payload = {
            "prompt": "I'm about to show you an image. Please remember what I show you.",
            "session_id": session_id
        }
        response = requests.post(f"{API_BASE_URL}/api/text", json=payload)
        print(f"Response: {response.json()['response'][:100]}...")
        
        # Download test image
        print("2. Downloading test image...")
        img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/800px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
        img_response = requests.get(img_url)
        with open("test_conv_image.jpg", "wb") as f:
            f.write(img_response.content)
        
        # Send image
        print("3. Sending image...")
        with open("test_conv_image.jpg", "rb") as f:
            files = {"image": f}
            data = {
                "prompt": "What do you see in this image?",
                "session_id": session_id
            }
            response = requests.post(f"{API_BASE_URL}/api/image", files=files, data=data)
        
        print(f"Image response: {response.json()['response'][:100]}...")
        
        # Ask about the image
        print("4. Asking about the image...")
        payload = {
            "prompt": "What was in the image I just showed you? Can you describe it again?",
            "session_id": session_id
        }
        response = requests.post(f"{API_BASE_URL}/api/text", json=payload)
        print(f"Follow-up response: {response.json()['response'][:100]}...")
        
        # Cleanup
        import os
        os.remove("test_conv_image.jpg")
        requests.delete(f"{API_BASE_URL}/api/conversation/{session_id}")
        
        return True
        
    except Exception as e:
        print(f"Image conversation test error: {e}")
        return False

def main():
    """Run conversation tests."""
    print("Bakllava Conversation API Tests")
    print("=" * 50)
    
    # Wait for service
    print("Waiting for service to be ready...")
    max_wait = 60
    for i in range(max_wait):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("Service is ready!")
                break
        except:
            pass
        if i == max_wait - 1:
            print("Service not ready, continuing anyway...")
        time.sleep(2)
    
    # Run tests
    tests = [
        ("Conversation Flow", test_conversation_flow),
        ("Conversation with Images", test_conversation_with_images),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
        print(f"{test_name}: {'PASSED' if result else 'FAILED'}")
    
    # Summary
    print(f"\n{'='*50}")
    print("CONVERSATION TEST SUMMARY")
    print(f"{'='*50}")
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name:25}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nOverall: {passed}/{total} conversation tests passed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 