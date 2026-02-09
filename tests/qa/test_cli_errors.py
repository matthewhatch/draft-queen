"""CLI Error Handling and Edge Case Tests."""

import subprocess
import sys
from typing import Tuple

class CLIErrorValidator:
    """Validate CLI error handling and edge cases."""
    
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
                timeout=5,
                input=""
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def test_error(self, name: str, should_fail: bool, *args) -> bool:
        """Test a CLI command expecting error or success."""
        exit_code, stdout, stderr = self.run_command(*args)
        
        if should_fail:
            passed = exit_code != 0
            expectation = "should fail"
        else:
            passed = exit_code == 0
            expectation = "should pass"
        
        self.results.append({
            "name": name,
            "command": " ".join(args),
            "passed": passed,
            "exit_code": exit_code,
            "expectation": expectation
        })
        
        if passed:
            self.passed += 1
            print(f"✅ {name}")
        else:
            self.failed += 1
            print(f"❌ {name}")
            if stderr:
                print(f"   Stderr: {stderr[:100]}")
        
        return passed
    
    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        pct = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "="*60)
        print(f"CLI ERROR HANDLING: {self.passed}/{total} passed ({pct:.1f}%)")
        print("="*60)
        
        return self.failed == 0


def main():
    """Run CLI error handling tests."""
    print("\n🧪 QA: CLI ERROR HANDLING & EDGE CASES\n")
    
    validator = CLIErrorValidator()
    
    # Test 1: Invalid commands
    print("❌ Testing Invalid Commands:")
    validator.test_error("Invalid command", True, "invalid_command")
    validator.test_error("Invalid subcommand", True, "pipeline", "invalid_sub")
    validator.test_error("Missing required argument", True, "prospects", "get")
    validator.test_error("Unknown option", True, "prospects", "list", "--invalid-option")
    
    # Test 2: Help text validation
    print("\n📖 Testing Help Text Accessibility:")
    validator.test_error("Help with unknown command", True, "unknown", "--help")
    validator.test_error("Prospects list help works", False, "prospects", "list", "--help")
    validator.test_error("Quality rules help works", False, "quality", "rules", "list", "--help")
    validator.test_error("Auth status help works", False, "auth", "status", "--help")
    
    # Test 3: Configuration edge cases
    print("\n⚙️  Testing Config Edge Cases:")
    validator.test_error("Show config (no config file ok)", False, "config", "show")
    validator.test_error("Set config with value", False, "config", "set", "test_key", "test_value")
    
    # Test 4: Option parsing
    print("\n🔧 Testing Option Parsing:")
    validator.test_error("Verbose flag works", False, "-v", "--help")
    validator.test_error("Config file flag works", False, "--config", "/dev/null", "--help")
    validator.test_error("API URL flag works", False, "--api-url", "http://localhost:8000", "--help")
    
    # Test 5: Command-specific options
    print("\n⚡ Testing Command-Specific Options:")
    validator.test_error("Prospects list limit option", False, "prospects", "list", "--limit", "10")
    validator.test_error("Prospects list offset option", False, "prospects", "list", "--offset", "0")
    validator.test_error("Pipeline history limit option", False, "pipeline", "history", "--limit", "5")
    validator.test_error("Quality violations limit option", False, "quality", "violations", "list", "--limit", "25")
    
    # Test 6: Format options
    print("\n📋 Testing Format Options:")
    validator.test_error("JSON output flag", False, "prospects", "list", "--json-output")
    validator.test_error("Export format option", False, "prospects", "export", "--format", "json")
    validator.test_error("Report format option", False, "quality", "report", "--format", "json")
    
    # Test 7: Global flags combinations
    print("\n🌍 Testing Global Flag Combinations:")
    validator.test_error("Verbose + help", False, "-v", "--help")
    validator.test_error("Config + verbose", False, "--config", "/dev/null", "-v", "--help")
    validator.test_error("API URL + config", False, "--api-url", "http://test:8000", "--config", "/dev/null", "--help")
    
    # Print summary
    success = validator.print_summary()
    
    # Print results
    if not success:
        print("\n⚠️  Some error handling tests failed. Details:")
        for result in validator.results:
            if not result["passed"]:
                print(f"\n❌ {result['name']}")
                print(f"   Command: {result['command']}")
                print(f"   Expected: {result['expectation']}")
                print(f"   Exit code: {result['exit_code']}")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
