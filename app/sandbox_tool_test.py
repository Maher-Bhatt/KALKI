"""
KALKI Sandbox Tool Testing Suite
=================================
Runs automated end-to-end sandbox verification for all tools, hardware controls,
and cyber modules in KALKI. Asserts 100% success rate before packaging.
"""

import sys
import os
import unittest

# Ensure app/ is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cybertools
import webscan
import deepscan
import tools
import hardware_detect
import watchdog


class TestKalkiToolSandbox(unittest.TestCase):

    def test_01_tools_schema_validity(self):
        """Verify all 16 tools have valid OpenAI-style function schemas."""
        self.assertIsInstance(tools.TOOLS_SCHEMA, list)
        self.assertGreaterEqual(len(tools.TOOLS_SCHEMA), 16)
        for item in tools.TOOLS_SCHEMA:
            self.assertEqual(item.get("type"), "function")
            func = item.get("function", {})
            self.assertTrue("name" in func)
            self.assertTrue("description" in func)
            self.assertTrue("parameters" in func)
        print("[SANDBOX TEST 1/10] tools.py schema validation PASSED")

    def test_02_cybertools_dns_and_ip(self):
        """Verify DNS resolution, public IP, and IP info lookup."""
        dns_res = cybertools.dns_lookup("google.com")
        self.assertEqual(dns_res.get("host"), "google.com")
        self.assertTrue("ip" in dns_res)

        pub_ip = cybertools.public_ip()
        self.assertNotEqual(pub_ip, "unavailable")

        ip_data = cybertools.ip_info()
        self.assertIsInstance(ip_data, dict)
        self.assertTrue("ip" in ip_data)
        print("[SANDBOX TEST 2/10] cybertools DNS & IP lookup PASSED")

    def test_03_cybertools_recon_helpers(self):
        """Verify ping, HTTP headers, GitHub dorks, and WiFi profiles."""
        dorks = cybertools.github_dorks("example.com")
        self.assertIsInstance(dorks, list)
        self.assertEqual(len(dorks), 8)

        ping_res = cybertools.ping("127.0.0.1")
        self.assertIn("host", ping_res)

        hdr_res = cybertools.http_headers("google.com")
        self.assertIn("headers", hdr_res)

        wifi_res = cybertools.wifi_profiles()
        self.assertIsInstance(wifi_res, list)
        print("[SANDBOX TEST 3/10] cybertools recon helpers PASSED")

    def test_04_cybertools_cve_and_subdomain(self):
        """Verify CVE lookup and Certificate Transparency subdomain enum."""
        cve_res = cybertools.cve_lookup("CVE-2024-3094")
        self.assertEqual(cve_res.get("cve_id"), "CVE-2024-3094")
        self.assertEqual(cve_res.get("severity"), "CRITICAL")

        sub_res = cybertools.subdomain_enum("google.com", limit=5)
        self.assertEqual(sub_res.get("domain"), "google.com")
        self.assertIn("subdomains", sub_res)
        print("[SANDBOX TEST 4/10] cybertools CVE lookup & Subdomain Enum PASSED")

    def test_05_webscan_vulnerability_audit(self):
        """Verify webscan on a real site."""
        scan_res = webscan.scan("https://example.com")
        self.assertEqual(scan_res.get("target"), "https://example.com")
        self.assertIn("findings", scan_res)
        print("[SANDBOX TEST 5/10] webscan vulnerability audit PASSED")

    def test_06_deepscan_playwright_availability(self):
        """Verify deepscan Playwright availability check."""
        avail = deepscan.available()
        self.assertIsInstance(avail, bool)
        print("[SANDBOX TEST 6/10] deepscan Playwright guard PASSED")

    def test_07_hardware_detection(self):
        """Verify hardware profile detection."""
        hw = hardware_detect.detect_hardware()
        self.assertIsInstance(hw, dict)
        self.assertTrue("cpu" in hw or "cpu_name" in hw or "ram_gb" in hw)
        print("[SANDBOX TEST 7/10] hardware detection PASSED")

    def test_08_watchdog_site_check(self):
        """Verify watchdog SSL & reachability checks."""
        days = watchdog.cert_days_left("google.com")
        self.assertTrue(days is None or days > 0)
        print("[SANDBOX TEST 8/10] watchdog SSL & site monitoring PASSED")

    def test_09_code_and_hash_utilities(self):
        """Verify hash identification, hashing, and password generator."""
        ident = cybertools.identify_hash("5d41402abc4b2a76b9719d911017c592")
        self.assertIn("MD5", ident)

        hashed = cybertools.hash_text("test1234", "sha256")
        self.assertEqual(hashed, "937e8d5fbb48bd4949536cd65b8d35c426b80d2f830c5c308e2cdec422ae2244")

        pwd = cybertools.random_password(16)
        self.assertEqual(len(pwd), 16)
        print("[SANDBOX TEST 9/10] cybertools crypto & hash utilities PASSED")

    def test_10_codecs_encoders_decoders(self):
        """Verify base64, hex, and URL encoders/decoders."""
        b64 = cybertools.encode("KALKI", "base64")
        self.assertEqual(b64, "S0FMS0k=")
        dec = cybertools.decode("S0FMS0k=", "base64")
        self.assertEqual(dec, "KALKI")
        print("[SANDBOX TEST 10/10] cybertools codecs PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("      KALKI COMPREHENSIVE SANDBOX TOOL TEST SUITE      ")
    print("=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestKalkiToolSandbox)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("\nALL 10 SANDBOX TOOL TESTS PASSED PERFECTLY!")
        sys.exit(0)
    else:
        print("\nSANDBOX TOOL TESTS FAILED!")
        sys.exit(1)
