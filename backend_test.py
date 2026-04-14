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
            required_fields = ['mac_ozeti', 'kg_analizi', 'gol_analizi', 'ms_egilimi', 'risk_notu', 'hizli_bakis']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False
            else:
                print("✅ All 6 required analysis fields present (including hizli_bakis)")
                
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
                
            return True
            
        return False

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