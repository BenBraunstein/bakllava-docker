#!/usr/bin/env python3

import requests
import json
import time
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"

def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Health check status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_text_prompt():
    """Test text-only prompt."""
    print("\nTesting text prompt...")
    try:
        payload = {
            "prompt": "Explain what artificial intelligence is in simple terms.",
            "temperature": 0.7,
            "max_tokens": 100
        }
        response = requests.post(f"{API_BASE_URL}/api/text", json=payload)
        print(f"Text prompt status: {response.status_code}")
        result = response.json()
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Response: {result['response'][:200]}...")
            print(f"Processing time: {result['processing_time']:.2f}s")
        else:
            print(f"Error: {result['error']}")
        return result['success']
    except Exception as e:
        print(f"Text prompt test failed: {e}")
        return False

def test_image_prompt():
    """Test image prompt with a sample image."""
    print("\nTesting image prompt...")
    try:
        # Download a test image
        img_response = requests.get(TEST_IMAGE_URL)
        if img_response.status_code != 200:
            print("Failed to download test image")
            return False
        
        # Save temporarily
        with open("test_image.jpg", "wb") as f:
            f.write(img_response.content)
        
        # Test the API
        with open("test_image.jpg", "rb") as f:
            files = {"image": f}
            data = {
                "prompt": "What do you see in this image? Describe it in detail.",
                "temperature": 0.7,
                "max_tokens": 200
            }
            response = requests.post(f"{API_BASE_URL}/api/image", files=files, data=data)
        
        print(f"Image prompt status: {response.status_code}")
        result = response.json()
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Response: {result['response'][:200]}...")
            print(f"Processing time: {result['processing_time']:.2f}s")
        else:
            print(f"Error: {result['error']}")
        
        # Cleanup
        Path("test_image.jpg").unlink(missing_ok=True)
        return result['success']
    except Exception as e:
        print(f"Image prompt test failed: {e}")
        # Cleanup
        Path("test_image.jpg").unlink(missing_ok=True)
        return False

def wait_for_service(max_wait=300):
    """Wait for the service to be ready."""
    print(f"Waiting for service to be ready (max {max_wait}s)...")
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if test_health_check():
            print("Service is ready!")
            return True
        print("Service not ready yet, waiting...")
        time.sleep(10)
    print("Service failed to become ready within timeout")
    return False

def main():
    """Run all tests."""
    print("Starting Bakllava API Tests")
    print("=" * 50)
    
    # Wait for service to be ready
    if not wait_for_service():
        print("FAILED: Service not ready")
        return False
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Text Prompt", test_text_prompt),
        ("Image Prompt", test_image_prompt),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
        print(f"{test_name}: {'PASSED' if result else 'FAILED'}")
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name:20}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 