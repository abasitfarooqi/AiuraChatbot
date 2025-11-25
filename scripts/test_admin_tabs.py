#!/usr/bin/env python3
"""
Test all admin.html tabs and functionality.
Generates a comprehensive report of what works and what doesn't.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
import json
from typing import Dict, List, Any
from loguru import logger

# Configuration
API_BASE = "http://localhost:8000/api/v1"
TEST_ADMIN_EMAIL = "admin@example.com"  # Update with your admin credentials
TEST_ADMIN_PASSWORD = "admin123"  # Update with your admin password

class TabTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.results = {}
        self.current_vendor_id = None
        
    def login(self) -> bool:
        """Login as admin and get auth token."""
        try:
            response = self.session.post(
                f"{API_BASE}/auth/vendor-admin/login",
                json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD}
            )
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                logger.info("✅ Login successful")
                return True
            else:
                logger.error(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Test an API endpoint."""
        try:
            url = f"{API_BASE}{endpoint}"
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=data, params=params)
            elif method == "PUT":
                response = self.session.put(url, json=data, params=params)
            elif method == "DELETE":
                response = self.session.delete(url, params=params)
            else:
                return {"status": "error", "message": f"Unknown method: {method}"}
            
            return {
                "status": "success" if response.status_code < 400 else "error",
                "status_code": response.status_code,
                "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "error": None if response.status_code < 400 else response.text
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "error": str(e)}
    
    def test_dashboard(self) -> Dict:
        """Test Dashboard tab."""
        logger.info("Testing Dashboard tab...")
        results = {}
        
        # Test database stats
        results["database_stats"] = self.test_endpoint("GET", "/database/stats")
        
        # Test RAG stats
        results["rag_stats"] = self.test_endpoint("GET", "/rag/stats")
        
        # Test current model
        results["current_model"] = self.test_endpoint("GET", "/models/current")
        
        return results
    
    def test_vendors(self) -> Dict:
        """Test Vendors tab."""
        logger.info("Testing Vendors tab...")
        results = {}
        
        # Test list vendors
        results["list_vendors"] = self.test_endpoint("GET", "/vendor/list")
        
        # Test create vendor (will fail if vendor exists, that's OK)
        test_vendor_id = "test_vendor_" + str(int(__import__("time").time()))
        results["create_vendor"] = self.test_endpoint("POST", "/vendor/create", data={
            "vendor_id": test_vendor_id,
            "vendor_name": "Test Vendor",
            "company_name": "Test Company",
            "business_type": "motorcycle_dealership"
        })
        
        # Test get vendor
        if self.current_vendor_id:
            results["get_vendor"] = self.test_endpoint("GET", f"/vendor/{self.current_vendor_id}")
        
        return results
    
    def test_models(self) -> Dict:
        """Test Models tab."""
        logger.info("Testing Models tab...")
        results = {}
        
        # Test list models from database
        results["list_models_db"] = self.test_endpoint("GET", "/database/table/models", params={"page": 1, "page_size": 100})
        
        # Test available models
        results["available_models"] = self.test_endpoint("GET", "/models/available", params={"provider": "ollama"})
        
        # Test current model
        results["current_model"] = self.test_endpoint("GET", "/models/current")
        
        # Test model config
        results["model_config"] = self.test_endpoint("GET", "/models/config")
        
        return results
    
    def test_rag(self) -> Dict:
        """Test RAG tab."""
        logger.info("Testing RAG tab...")
        results = {}
        
        # Test RAG stats
        results["rag_stats"] = self.test_endpoint("GET", "/rag/stats")
        
        # Test knowledge base
        if self.current_vendor_id:
            results["knowledge_base"] = self.test_endpoint("GET", f"/vendor/{self.current_vendor_id}/knowledge-base")
        
        return results
    
    def test_memory(self) -> Dict:
        """Test Memory tab."""
        logger.info("Testing Memory tab...")
        results = {}
        
        # Test memory stats
        results["memory_stats"] = self.test_endpoint("GET", "/memory/stats")
        
        # Test list memories
        results["list_memories"] = self.test_endpoint("GET", "/memory/list", params={"limit": 10, "offset": 0})
        
        return results
    
    def test_llm_config(self) -> Dict:
        """Test LLM Config tab."""
        logger.info("Testing LLM Config tab...")
        results = {}
        
        # Test get config
        results["get_config"] = self.test_endpoint("GET", "/models/config")
        
        # Test get presets
        results["get_presets"] = self.test_endpoint("GET", "/models/presets")
        
        return results
    
    def test_unified_config(self) -> Dict:
        """Test Unified Config tab."""
        logger.info("Testing Unified Config tab...")
        results = {}
        
        if not self.current_vendor_id:
            return {"error": "No vendor selected"}
        
        # Test get config
        results["get_config"] = self.test_endpoint("GET", f"/vendor/{self.current_vendor_id}/config")
        
        # Test get config versions
        results["config_versions"] = self.test_endpoint("GET", f"/vendor/{self.current_vendor_id}/versions/config")
        
        return results
    
    def test_knowledge_base(self) -> Dict:
        """Test Knowledge Base tab."""
        logger.info("Testing Knowledge Base tab...")
        results = {}
        
        if not self.current_vendor_id:
            return {"error": "No vendor selected"}
        
        # Test get knowledge base
        results["get_kb"] = self.test_endpoint("GET", f"/vendor/{self.current_vendor_id}/knowledge-base")
        
        # Test KB versions
        results["kb_versions"] = self.test_endpoint("GET", f"/vendor/{self.current_vendor_id}/versions/knowledge-base")
        
        return results
    
    def test_database(self) -> Dict:
        """Test Database tab."""
        logger.info("Testing Database tab...")
        results = {}
        
        # Test database stats
        results["db_stats"] = self.test_endpoint("GET", "/database/stats")
        
        # Test table list
        results["table_list"] = self.test_endpoint("GET", "/database/tables")
        
        # Test specific table (vendors)
        results["table_vendors"] = self.test_endpoint("GET", "/database/table/vendors", params={"page": 1, "page_size": 10})
        
        return results
    
    def test_caching(self) -> Dict:
        """Test Caching tab."""
        logger.info("Testing Caching tab...")
        results = {}
        
        # Test cache stats
        results["cache_stats"] = self.test_endpoint("GET", "/cache/stats")
        
        # Test main cache
        results["main_cache"] = self.test_endpoint("GET", "/cache/main", params={"limit": 10, "offset": 0})
        
        # Test temporary cache
        results["temp_cache"] = self.test_endpoint("GET", "/cache/temporary", params={"limit": 10, "offset": 0})
        
        return results
    
    def run_all_tests(self) -> Dict:
        """Run all tab tests."""
        logger.info("=" * 60)
        logger.info("Starting Admin Panel Tab Tests")
        logger.info("=" * 60)
        
        if not self.login():
            return {"error": "Login failed"}
        
        # Get current vendor
        vendors_resp = self.test_endpoint("GET", "/vendor/list")
        if vendors_resp.get("status") == "success" and vendors_resp.get("response"):
            vendors = vendors_resp["response"]
            if isinstance(vendors, dict) and "vendors" in vendors:
                vendor_list = vendors["vendors"]
                if vendor_list and len(vendor_list) > 0:
                    self.current_vendor_id = vendor_list[0].get("vendor_id") or vendor_list[0].get("slug")
        
        all_results = {
            "dashboard": self.test_dashboard(),
            "vendors": self.test_vendors(),
            "models": self.test_models(),
            "rag": self.test_rag(),
            "memory": self.test_memory(),
            "llm_config": self.test_llm_config(),
            "unified_config": self.test_unified_config(),
            "knowledge_base": self.test_knowledge_base(),
            "database": self.test_database(),
            "caching": self.test_caching()
        }
        
        return all_results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a human-readable test report."""
        report = []
        report.append("=" * 80)
        report.append("ADMIN PANEL TAB TEST REPORT")
        report.append("=" * 80)
        report.append("")
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for tab_name, tab_results in results.items():
            if isinstance(tab_results, dict) and "error" in tab_results:
                report.append(f"❌ {tab_name.upper()} TAB: {tab_results['error']}")
                report.append("")
                continue
            
            report.append(f"{tab_name.upper()} TAB")
            report.append("-" * 80)
            
            for test_name, test_result in tab_results.items():
                total_tests += 1
                status = test_result.get("status", "unknown")
                status_code = test_result.get("status_code", 0)
                
                if status == "success" and status_code < 400:
                    passed_tests += 1
                    report.append(f"  ✅ {test_name}: PASSED (HTTP {status_code})")
                else:
                    failed_tests += 1
                    error_msg = test_result.get("error", test_result.get("message", "Unknown error"))
                    report.append(f"  ❌ {test_name}: FAILED (HTTP {status_code})")
                    report.append(f"      Error: {error_msg[:200]}")
            
            report.append("")
        
        report.append("=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {passed_tests} ({passed_tests*100//total_tests if total_tests > 0 else 0}%)")
        report.append(f"Failed: {failed_tests} ({failed_tests*100//total_tests if total_tests > 0 else 0}%)")
        report.append("")
        
        return "\n".join(report)

def main():
    """Run tests and generate report."""
    tester = TabTester()
    results = tester.run_all_tests()
    report = tester.generate_report(results)
    
    print(report)
    
    # Save to file
    with open("admin_tab_test_report.txt", "w") as f:
        f.write(report)
    
    logger.info("Report saved to admin_tab_test_report.txt")

if __name__ == "__main__":
    main()

