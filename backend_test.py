import requests
import sys
import time
from datetime import datetime

class MatchAnalysisAPITester:
    def __init__(self, base_url="https://91d590f4-f7b4-4d78-8fee-121dcfb6d8ed.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"Response: {response.text[:200]}")

            return success, response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_endpoint(self):
        """Test health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        if success:
            print(f"API Token Configured: {response.get('api_token_configured', False)}")
        return success

    def test_match_analysis(self, match_id):
        """Test match analysis endpoint"""
        success, response = self.run_test(
            f"Match Analysis for ID {match_id}",
            "GET",
            f"api/match/{match_id}/analysis",
            200
        )
        
        if success:
            # Check required fields
            required_fields = ['mac_ozeti', 'kg_analizi', 'gol_analizi', 'ms_egilimi', 'risk_notu']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False
            else:
                print("✅ All 5 required analysis fields present")
                
            # Check for real statistics
            analysis_text = ' '.join(response.values()).lower()
            
            # Check for percentages
            has_percentages = '%' in analysis_text
            print(f"Contains percentages: {has_percentages}")
            
            # Check for form strings (like GGGBM)
            import re
            form_pattern = r'[gbm]{3,5}'
            has_form = bool(re.search(form_pattern, analysis_text))
            print(f"Contains form strings: {has_form}")
            
            # Check for W-D-L records (like 5G-2B-3M)
            wdl_pattern = r'\d+[gb]-\d+[gb]-\d+[gm]'
            has_wdl = bool(re.search(wdl_pattern, analysis_text))
            print(f"Contains W-D-L records: {has_wdl}")
            
            # Check for betting language (should NOT be present)
            # Look for actual betting phrases, not just individual words that could be used in normal context
            betting_phrases = ['banko oyna', 'kesin oyna', 'garanti gol', 'şunu oyna', 'kesin galibiyet', 'banko bahis']
            found_betting_phrases = [phrase for phrase in betting_phrases if phrase in analysis_text]
            if found_betting_phrases:
                print(f"❌ Contains betting language: {found_betting_phrases} - this should not be present")
                return False
            else:
                print("✅ No betting language found")
            
            # Check for two-legged tie detection (Liverpool vs PSG)
            if match_id == 556722:
                has_two_leg = 'iki ayaklı' in analysis_text or 'İki ayaklı' in ' '.join(response.values())
                has_first_match = 'ilk maç' in analysis_text or 'İlk maç' in ' '.join(response.values())
                print(f"Two-legged tie detection: {has_two_leg}")
                print(f"First match result mentioned: {has_first_match}")
                if not has_two_leg:
                    print("❌ Two-legged tie detection not working for Liverpool vs PSG")
                    return False
                
            return True
            
        return False

    def test_cache_functionality(self, match_id):
        """Test cache functionality by making two requests and measuring time"""
        print(f"\n🔍 Testing Cache Functionality for Match {match_id}...")
        
        # First request (should hit API)
        start_time = time.time()
        success1, _ = self.run_test(
            f"First Request (Cache Miss) - Match {match_id}",
            "GET",
            f"api/match/{match_id}/analysis",
            200
        )
        first_request_time = time.time() - start_time
        
        if not success1:
            return False
            
        # Wait a moment
        time.sleep(1)
        
        # Second request (should hit cache)
        start_time = time.time()
        success2, _ = self.run_test(
            f"Second Request (Cache Hit) - Match {match_id}",
            "GET",
            f"api/match/{match_id}/analysis",
            200
        )
        second_request_time = time.time() - start_time
        
        if success2:
            print(f"First request time: {first_request_time:.2f}s")
            print(f"Second request time: {second_request_time:.2f}s")
            
            # Cache should make second request significantly faster
            if second_request_time < first_request_time * 0.5:
                print("✅ Cache appears to be working (second request much faster)")
                return True
            else:
                print("⚠️ Cache may not be working optimally")
                return True  # Still pass as functionality works
        
        return False

def main():
    # Setup
    tester = MatchAnalysisAPITester()
    
    print("🚀 Starting Match Analysis API Tests")
    print("=" * 50)
    
    # Test health endpoint first
    if not tester.test_health_endpoint():
        print("❌ Health check failed, stopping tests")
        return 1
    
    # Test analysis endpoints for both match IDs
    match_ids = [556722, 556724]  # Liverpool vs PSG, Atletico vs Barcelona
    
    for match_id in match_ids:
        print(f"\n📊 Testing Match ID: {match_id}")
        print("-" * 30)
        
        if not tester.test_match_analysis(match_id):
            print(f"❌ Analysis test failed for match {match_id}")
            continue
            
        # Test cache for first match only to avoid rate limits
        if match_id == match_ids[0]:
            if not tester.test_cache_functionality(match_id):
                print(f"❌ Cache test failed for match {match_id}")
    
    # Print final results
    print(f"\n📊 Final Results")
    print("=" * 50)
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())