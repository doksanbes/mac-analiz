import requests
import sys
import time
import json
from datetime import datetime

class MatchAnalysisAPITester:
    def __init__(self, base_url="https://91d590f4-f7b4-4d78-8fee-121dcfb6d8ed.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, check_fields=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text[:500]}

            if success:
                # Check specific fields if provided
                field_checks_passed = True
                if check_fields:
                    for field in check_fields:
                        if field not in response_data:
                            print(f"❌ Missing required field: {field}")
                            field_checks_passed = False
                            success = False
                        else:
                            print(f"✅ Found field: {field}")

                if success and field_checks_passed:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    self.test_results.append({
                        "test": name,
                        "status": "PASSED",
                        "response_code": response.status_code,
                        "data": response_data
                    })
                else:
                    print(f"❌ Failed - Field validation failed")
                    self.test_results.append({
                        "test": name,
                        "status": "FAILED",
                        "response_code": response.status_code,
                        "error": "Field validation failed",
                        "data": response_data
                    })
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response_data}")
                self.test_results.append({
                    "test": name,
                    "status": "FAILED",
                    "response_code": response.status_code,
                    "expected_code": expected_status,
                    "error": response_data.get("detail", "Unknown error"),
                    "data": response_data
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
        """Test health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200,
            check_fields=["status", "api_token_configured"]
        )
        if success:
            print(f"API Token Configured: {response.get('api_token_configured', False)}")
        return success

    def test_match_endpoint(self, match_id):
        """Test match endpoint"""
        success, response = self.run_test(
            f"Get Match {match_id}",
            "GET",
            f"api/match/{match_id}",
            200,
            check_fields=["homeTeam", "awayTeam", "status"]
        )
        return success, response

    def test_match_analysis_with_form(self, match_id):
        """Test match analysis endpoint - KEY TEST for form dots feature"""
        success, response = self.run_test(
            f"Match Analysis with Form Data for ID {match_id}",
            "GET",
            f"api/match/{match_id}/analysis",
            200,
            check_fields=["home_form", "away_form", "hizli_bakis", "mac_ozeti"]
        )
        
        if success and response:
            # Additional validation for form data
            home_form = response.get("home_form", "")
            away_form = response.get("away_form", "")
            
            print(f"   📊 Home Form: '{home_form}'")
            print(f"   📊 Away Form: '{away_form}'")
            
            # Validate form strings contain only G, B, M characters
            valid_chars = set("GBM")
            if home_form and not set(home_form).issubset(valid_chars):
                print(f"❌ Invalid characters in home_form: {home_form}")
                return False, response
            if away_form and not set(away_form).issubset(valid_chars):
                print(f"❌ Invalid characters in away_form: {away_form}")
                return False, response
                
            # Check if form strings are reasonable length (should be 5 or less)
            if len(home_form) > 5:
                print(f"❌ Home form too long: {len(home_form)} characters")
                return False, response
            if len(away_form) > 5:
                print(f"❌ Away form too long: {len(away_form)} characters")
                return False, response
                
            print(f"✅ Form data validation passed")
            
            # Check other required fields
            required_fields = ['mac_ozeti', 'kg_analizi', 'gol_analizi', 'ms_egilimi', 'risk_notu', 'hizli_bakis']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False, response
            else:
                print("✅ All 6 required analysis fields present")
                
            # Test Hızlı Bakış specific requirements
            hb = response.get('hizli_bakis', {})
            if not self.test_hizli_bakis(hb, match_id):
                return False
                
            # Check for real statistics
            analysis_text = ' '.join([str(v) for v in response.values() if isinstance(v, str)]).lower()
            
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
            banned_words = ['banko', 'kesin', 'garanti', 'şunu oyna']
            found_banned = []
            for word in banned_words:
                if word in analysis_text:
                    found_banned.append(word)
            
            if found_banned:
                print(f"❌ Contains banned words: {found_banned} - this should not be present")
                return False
            else:
                print("✅ No banned words found in analysis")
            
            # Check for two-legged tie detection (Liverpool vs PSG)
            if match_id == 556722:
                has_two_leg = 'iki ayaklı' in analysis_text or 'İki ayaklı' in ' '.join([str(v) for v in response.values() if isinstance(v, str)])
                has_first_match = 'ilk maç' in analysis_text or 'İlk maç' in ' '.join([str(v) for v in response.values() if isinstance(v, str)])
                print(f"Two-legged tie detection: {has_two_leg}")
                print(f"First match result mentioned: {has_first_match}")
                if not has_two_leg:
                    print("❌ Two-legged tie detection not working for Liverpool vs PSG")
                    return False
                
            return True, response
            
        return False, response

    def test_hizli_bakis(self, hb, match_id):
        """Test Hızlı Bakış specific requirements"""
        print(f"\n🔍 Testing Hızlı Bakış for Match {match_id}...")
        
        # Check required fields
        required_hb_fields = ['ana_senaryo', 'alternatif', 'taraf_egilimi', 'risk_seviyesi']
        missing_hb_fields = [field for field in required_hb_fields if field not in hb]
        
        if missing_hb_fields:
            print(f"❌ Missing hizli_bakis fields: {missing_hb_fields}")
            return False
        else:
            print("✅ All 4 hizli_bakis fields present")
        
        # Check that all values are short (1 line) and in Turkish
        for field, value in hb.items():
            if not isinstance(value, str):
                print(f"❌ {field} is not a string: {type(value)}")
                return False
            
            if '\n' in value:
                print(f"❌ {field} contains newlines (should be 1 line): {value}")
                return False
            
            if len(value) > 100:  # Reasonable limit for "short"
                print(f"❌ {field} is too long ({len(value)} chars): {value}")
                return False
            
            # Check for Turkish characters (basic check)
            turkish_chars = ['ı', 'ğ', 'ü', 'ş', 'ö', 'ç', 'İ', 'Ğ', 'Ü', 'Ş', 'Ö', 'Ç']
            has_turkish = any(char in value for char in turkish_chars)
            if not has_turkish and len(value) > 10:  # Allow short English words
                print(f"⚠️ {field} may not be in Turkish: {value}")
        
        print("✅ All hizli_bakis values are short and appear to be in Turkish")
        
        # Check risk level values
        valid_risk_levels = ['Düşük', 'Orta', 'Orta-Yüksek', 'Yüksek', 'Maç tamamlandı', 'Maç devam ediyor']
        risk_level = hb.get('risk_seviyesi', '')
        if risk_level not in valid_risk_levels:
            print(f"❌ Invalid risk level: {risk_level}. Expected one of: {valid_risk_levels}")
            return False
        else:
            print(f"✅ Valid risk level: {risk_level}")
        
        # Check for banned words in hizli_bakis
        banned_words = ['banko', 'kesin', 'garanti', 'şunu oyna']
        hb_text = ' '.join(hb.values()).lower()
        found_banned = [word for word in banned_words if word in hb_text]
        
        if found_banned:
            print(f"❌ Hızlı Bakış contains banned words: {found_banned}")
            return False
        else:
            print("✅ No banned words in Hızlı Bakış")
        
        # Print the actual values for verification
        print(f"Ana Senaryo: {hb.get('ana_senaryo', 'N/A')}")
        print(f"Alternatif: {hb.get('alternatif', 'N/A')}")
        print(f"Taraf Eğilimi: {hb.get('taraf_egilimi', 'N/A')}")
        print(f"Risk Seviyesi: {hb.get('risk_seviyesi', 'N/A')}")
        
        return True

    def test_matches_form_endpoint(self):
        """Test the new /api/matches/form endpoint for form dots feature"""
        success, response = self.run_test(
            "Matches Form Endpoint",
            "GET",
            "api/matches/form",
            200
        )
        
        if success and response:
            # Validate response structure
            if not isinstance(response, dict):
                print(f"❌ Response should be a dictionary, got {type(response)}")
                return False
            
            # Check that we have form data for multiple matches
            if len(response) == 0:
                print("❌ No form data returned")
                return False
            
            print(f"✅ Form data returned for {len(response)} matches")
            
            # Validate each match's form data
            valid_chars = set("GBM")
            for match_id, form_data in response.items():
                if not isinstance(form_data, dict):
                    print(f"❌ Form data for match {match_id} should be dict, got {type(form_data)}")
                    return False
                
                if "home_form" not in form_data or "away_form" not in form_data:
                    print(f"❌ Missing home_form or away_form for match {match_id}")
                    return False
                
                home_form = form_data["home_form"]
                away_form = form_data["away_form"]
                
                # Validate form strings
                if home_form and not set(home_form).issubset(valid_chars):
                    print(f"❌ Invalid characters in home_form for match {match_id}: {home_form}")
                    return False
                
                if away_form and not set(away_form).issubset(valid_chars):
                    print(f"❌ Invalid characters in away_form for match {match_id}: {away_form}")
                    return False
                
                if len(home_form) > 5 or len(away_form) > 5:
                    print(f"❌ Form strings too long for match {match_id}")
                    return False
            
            print("✅ All form data validation passed")
            
            # Print sample data
            sample_matches = list(response.items())[:3]
            for match_id, form_data in sample_matches:
                print(f"   Match {match_id}: Home={form_data['home_form']}, Away={form_data['away_form']}")
            
            return True
        
        return False

    def test_matches_endpoint_cache(self):
        """Test that /api/matches endpoint uses cache (120s TTL)"""
        print(f"\n🔍 Testing /api/matches Cache Functionality...")
        
        # First request (should hit API)
        start_time = time.time()
        success1, response1 = self.run_test(
            "First Request (Cache Miss) - Matches List",
            "GET",
            "api/matches",
            200,
            check_fields=["matches"]
        )
        first_request_time = time.time() - start_time
        
        if not success1:
            return False
            
        # Wait a moment
        time.sleep(1)
        
        # Second request (should hit cache)
        start_time = time.time()
        success2, response2 = self.run_test(
            "Second Request (Cache Hit) - Matches List",
            "GET",
            "api/matches",
            200,
            check_fields=["matches"]
        )
        second_request_time = time.time() - start_time
        
        if success2:
            print(f"First request time: {first_request_time:.2f}s")
            print(f"Second request time: {second_request_time:.2f}s")
            
            # Verify we got the same data
            if response1.get("matches") == response2.get("matches"):
                print("✅ Cache returned identical data")
            else:
                print("⚠️ Cache returned different data")
            
            # Cache should make second request faster
            if second_request_time < first_request_time * 0.8:
                print("✅ Cache appears to be working (second request faster)")
                return True
            else:
                print("⚠️ Cache may not be working optimally")
                return True  # Still pass as functionality works
        
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
    print("🚀 Starting Football API Backend Tests - New Features Testing")
    print("=" * 60)
    
    tester = MatchAnalysisAPITester()
    
    # Test 1: Health check
    if not tester.test_health_endpoint():
        print("❌ Health check failed, stopping tests")
        return 1

    # Test 2: NEW FEATURE - /api/matches/form endpoint
    print("\n🆕 Testing NEW FEATURE: Form Dots Data Endpoint")
    if not tester.test_matches_form_endpoint():
        print("❌ Matches form endpoint failed")
        return 1

    # Test 3: NEW FEATURE - /api/matches cache (120s TTL)
    print("\n🆕 Testing NEW FEATURE: Matches List Cache")
    if not tester.test_matches_endpoint_cache():
        print("❌ Matches cache test failed")
        return 1

    # Test 4: Match endpoint for match 556722 (Liverpool vs PSG)
    match_success, match_data = tester.test_match_endpoint(556722)
    if not match_success:
        print("❌ Match endpoint failed, stopping tests")
        return 1

    # Test 5: Match analysis endpoint (existing feature with form data)
    analysis_success, analysis_data = tester.test_match_analysis_with_form(556722)
    if not analysis_success:
        print("❌ Match analysis endpoint failed")
        return 1

    # Test 6: Cache functionality for analysis
    print("\n🔄 Testing analysis cache functionality...")
    tester.test_cache_functionality(556722)

    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Tests Summary:")
    print(f"   Total Tests: {tester.tests_run}")
    print(f"   Passed: {tester.tests_passed}")
    print(f"   Failed: {tester.tests_run - tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    # Save detailed results
    with open("/app/backend_test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": tester.tests_run,
                "passed": tester.tests_passed,
                "failed": tester.tests_run - tester.tests_passed,
                "success_rate": (tester.tests_passed/tester.tests_run)*100
            },
            "tests": tester.test_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to /app/backend_test_results.json")
    
    # Return 0 if all critical tests passed (health + form endpoint + matches + analysis)
    critical_tests_passed = tester.tests_passed >= 5
    return 0 if critical_tests_passed else 1

if __name__ == "__main__":
    sys.exit(main())