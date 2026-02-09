"""QA Validation Suite for CLI Commands."""

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

class CLIValidator:
    """Validate CLI functionality and help text."""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.base_cmd = [sys.executable, "-m", "cli.main"]
    
    def run_command(self, *args) -> Tuple[int, str, str]:
        """Run CLI command and return exit code, stdout, stderr."""
        try:
            cmd = self.base_cmd + list(args)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def test(self, name: str, *args) -> bool:
        """Test a CLI command and record result."""
        exit_code, stdout, stderr = self.run_command(*args)
        passed = exit_code == 0
        
        self.results.append({
            "name": name,
            "command": " ".join(args),
            "passed": passed,
            "exit_code": exit_code,
            "output_length": len(stdout)
        })
        
        if passed:
            self.passed += 1
            print(f"✅ {name}")
        else:
            self.failed += 1
            print(f"❌ {name}")
            if stderr:
                print(f"   Error: {stderr[:100]}")
        
        return passed
    
    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        pct = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "="*60)
        print(f"CLI VALIDATION RESULTS: {self.passed}/{total} passed ({pct:.1f}%)")
        print("="*60)
        
        return self.failed == 0


def main():
    """Run CLI validation tests."""
    print("\n🧪 QA: CLI VALIDATION TEST SUITE\n")
    
    validator = CLIValidator()
    
    # Test 1: Main help
    print("📋 Testing Main Commands:")
    validator.test("Main help", "--help")
    validator.test("Main version", "version")
    validator.test("Main with verbose", "-v", "--help")
    
    # Test 2: Pipeline commands
    print("\n🔄 Testing Pipeline Commands:")
    validator.test("Pipeline help", "pipeline", "--help")
    validator.test("Pipeline status help", "pipeline", "status", "--help")
    validator.test("Pipeline run help", "pipeline", "run", "--help")
    validator.test("Pipeline logs help", "pipeline", "logs", "--help")
    validator.test("Pipeline history help", "pipeline", "history", "--help")
    validator.test("Pipeline retry help", "pipeline", "retry", "--help")
    validator.test("Pipeline config help", "pipeline", "config", "--help")
    validator.test("Pipeline config show help", "pipeline", "config", "show", "--help")
    validator.test("Pipeline config set help", "pipeline", "config", "set", "--help")
    
    # Test 3: Prospects commands
    print("\n👥 Testing Prospect Commands:")
    validator.test("Prospects help", "prospects", "--help")
    validator.test("Prospects list help", "prospects", "list", "--help")
    validator.test("Prospects search help", "prospects", "search", "--help")
    validator.test("Prospects get help", "prospects", "get", "--help")
    validator.test("Prospects export help", "prospects", "export", "--help")
    
    # Test 4: History commands
    print("\n📚 Testing History Commands:")
    validator.test("History help", "history", "--help")
    validator.test("History get help", "history", "get", "--help")
    validator.test("History snapshot help", "history", "snapshot", "--help")
    
    # Test 5: Quality commands
    print("\n✨ Testing Quality Commands:")
    validator.test("Quality help", "quality", "--help")
    validator.test("Quality rules help", "quality", "rules", "--help")
    validator.test("Quality rules list help", "quality", "rules", "list", "--help")
    validator.test("Quality rules show help", "quality", "rules", "show", "--help")
    validator.test("Quality rules create help", "quality", "rules", "create", "--help")
    validator.test("Quality violations help", "quality", "violations", "--help")
    validator.test("Quality violations list help", "quality", "violations", "list", "--help")
    validator.test("Quality check help", "quality", "check", "--help")
    validator.test("Quality report help", "quality", "report", "--help")
    validator.test("Quality metrics help", "quality", "metrics", "--help")
    
    # Test 6: Config commands
    print("\n⚙️  Testing Config Commands:")
    validator.test("Config help", "config", "--help")
    validator.test("Config init help", "config", "init", "--help")
    validator.test("Config validate help", "config", "validate", "--help")
    validator.test("Config show help", "config", "show", "--help")
    validator.test("Config set help", "config", "set", "--help")
    
    # Test 7: Auth commands
    print("\n🔐 Testing Auth Commands:")
    validator.test("Auth help", "auth", "--help")
    validator.test("Auth login help", "auth", "login", "--help")
    validator.test("Auth logout help", "auth", "logout", "--help")
    validator.test("Auth status help", "auth", "status", "--help")
    
    # Test 8: Health commands
    print("\n🏥 Testing Health Commands:")
    validator.test("Health help", "health", "--help")
    validator.test("Health check help", "health", "check", "--help")
    
    # Test 9: DB commands
    print("\n🗄️  Testing Database Commands:")
    validator.test("DB help", "db", "--help")
    validator.test("DB migrate help", "db", "migrate", "--help")
    validator.test("DB backup help", "db", "backup", "--help")
    
    # Test 10: Global options
    print("\n🌍 Testing Global Options:")
    validator.test("API URL override", "--api-url", "http://test:8000", "--help")
    validator.test("Config file option", "--config", "/tmp/test.yaml", "--help")
    
    # Print summary
    success = validator.print_summary()
    
    # Print detailed results
    print("\n📊 Detailed Results:")
    print("-"*60)
    for result in validator.results:
        status = "✅" if result["passed"] else "❌"
        cmd = result["command"]
        print(f"{status} {result['name']}")
        print(f"   Command: {cmd}")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
