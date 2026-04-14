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
        """Test health endpoint - should return 200 with api_token_configured: true"""
        success, response = self.run_test(
            "Health Endpoint",
            "GET",
            "api/health",
            200,
            expected_content={"status": "ok", "api_token_configured": True}
        )
        return success

    def test_matches_endpoint(self):
        """Test matches endpoint - should return 200 with real match data"""
        success, response = self.run_test(
            "Matches Endpoint (With API Token)",
            "GET",
            "api/matches",
            200
        )
        
        # Check if response contains matches array
        if success and isinstance(response, dict):
            if 'matches' in response and isinstance(response['matches'], list):
                print(f"✅ Found {len(response['matches'])} matches in response")
                if len(response['matches']) > 0:
                    # Check first match structure
                    first_match = response['matches'][0]
                    required_fields = ['id', 'homeTeam', 'awayTeam', 'status', 'utcDate']
                    for field in required_fields:
                        if field in first_match:
                            print(f"✅ Match has required field: {field}")
                        else:
                            print(f"❌ Match missing required field: {field}")
                else:
                    print("⚠️ No matches found in response")
            else:
                print(f"❌ Expected matches array, got: {response}")
        
        return success

    def test_match_detail_endpoint(self):
        """Test match detail endpoint for Portsmouth vs Ipswich Town (ID: 541021)"""
        success, response = self.run_test(
            "Match Detail Endpoint (Portsmouth vs Ipswich Town)",
            "GET",
            "api/match/541021",
            200
        )
        
        # Check if response contains match data
        if success and isinstance(response, dict):
            # Check for required fields
            required_fields = ['id', 'homeTeam', 'awayTeam', 'status', 'utcDate', 'competition']
            for field in required_fields:
                if field in response:
                    print(f"✅ Match detail has required field: {field}")
                else:
                    print(f"❌ Match detail missing required field: {field}")
            
            # Check team names
            if 'homeTeam' in response and 'name' in response['homeTeam']:
                home_team = response['homeTeam']['name']
                if 'Portsmouth' in home_team:
                    print(f"✅ Found Portsmouth as home team: {home_team}")
                else:
                    print(f"⚠️ Home team: {home_team}")
            
            if 'awayTeam' in response and 'name' in response['awayTeam']:
                away_team = response['awayTeam']['name']
                if 'Ipswich' in away_team:
                    print(f"✅ Found Ipswich as away team: {away_team}")
                else:
                    print(f"⚠️ Away team: {away_team}")
        
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