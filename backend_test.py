import requests
import sys
from datetime import datetime

class TurkishFootballAPITester:
    def __init__(self, base_url="https://91d590f4-f7b4-4d78-8fee-121dcfb6d8ed.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, expected_content=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, timeout=10)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
                print(f"   Response: {response_data}")
            except:
                response_data = response.text
                print(f"   Response Text: {response_data}")

            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Expected status {expected_status}, got {response.status_code}")
                
                # Check content if specified
                if expected_content:
                    if isinstance(response_data, dict):
                        for key, value in expected_content.items():
                            if key in response_data and response_data[key] == value:
                                print(f"✅ Content check passed: {key} = {value}")
                            else:
                                print(f"❌ Content check failed: {key} expected {value}, got {response_data.get(key)}")
                    elif isinstance(response_data, str) and expected_content in response_data:
                        print(f"✅ Content check passed: Found expected text")
                
                self.test_results.append({
                    "test": name,
                    "status": "PASSED",
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response_data
                })
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                self.test_results.append({
                    "test": name,
                    "status": "FAILED",
                    "expected_status": expected_status,
                    "actual_status": response.status_code,
                    "response": response_data
                })

            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "test": name,
                "status": "ERROR",
                "error": str(e)
            })
            return False, {}

    def test_health_endpoint(self):
        """Test health endpoint - should return 200 with api_token_configured: false"""
        success, response = self.run_test(
            "Health Endpoint",
            "GET",
            "api/health",
            200,
            expected_content={"status": "ok", "api_token_configured": False}
        )
        return success

    def test_matches_endpoint(self):
        """Test matches endpoint - should return 503 with Turkish error"""
        success, response = self.run_test(
            "Matches Endpoint (No API Token)",
            "GET",
            "api/matches",
            503
        )
        
        # Check if response contains Turkish error message
        if success and isinstance(response, dict) and 'detail' in response:
            if 'FOOTBALL_DATA_API_TOKEN' in response['detail'] and 'ayarlanmamış' in response['detail']:
                print("✅ Turkish error message found in response")
            else:
                print(f"❌ Expected Turkish error message, got: {response['detail']}")
        
        return success

    def test_match_detail_endpoint(self):
        """Test match detail endpoint - should return 503 with Turkish error"""
        success, response = self.run_test(
            "Match Detail Endpoint (No API Token)",
            "GET",
            "api/match/12345",
            503
        )
        
        # Check if response contains Turkish error message
        if success and isinstance(response, dict) and 'detail' in response:
            if 'FOOTBALL_DATA_API_TOKEN' in response['detail'] and 'ayarlanmamış' in response['detail']:
                print("✅ Turkish error message found in response")
            else:
                print(f"❌ Expected Turkish error message, got: {response['detail']}")
        
        return success

def main():
    print("🚀 Starting Turkish Football API Tests")
    print("=" * 50)
    
    # Setup
    tester = TurkishFootballAPITester()

    # Run tests
    print("\n📋 Testing Backend API Endpoints...")
    
    # Test health endpoint
    tester.test_health_endpoint()
    
    # Test matches endpoint (should fail with 503)
    tester.test_matches_endpoint()
    
    # Test match detail endpoint (should fail with 503)
    tester.test_match_detail_endpoint()

    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        print("\nFailed Tests:")
        for result in tester.test_results:
            if result["status"] != "PASSED":
                print(f"  - {result['test']}: {result['status']}")
        return 1

if __name__ == "__main__":
    sys.exit(main())