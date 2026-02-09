"""API client for communicating with draft-queen backend."""

import json
from typing import Any, Dict, Optional
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout
import keyring
from pathlib import Path
import yaml

class APIClient:
    """Client for communicating with draft-queen backend API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: Optional[str] = None):
        """Initialize API client.
        
        Args:
            base_url: Base URL for API endpoint
            auth_token: Optional authentication token
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or self._get_stored_token()
        self.session = requests.Session()
        self._update_headers()
    
    def _update_headers(self) -> None:
        """Update request headers with auth token if available."""
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "draft-queen-cli/0.1.0",
        })
        if self.auth_token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.auth_token}"
            })
    
    def _get_stored_token(self) -> Optional[str]:
        """Retrieve stored auth token from system keyring."""
        try:
            return keyring.get_password("draft-queen", "api_token")
        except Exception:
            return None
    
    def store_token(self, token: str) -> None:
        """Store auth token in system keyring."""
        try:
            keyring.set_password("draft-queen", "api_token", token)
            self.auth_token = token
            self._update_headers()
        except Exception as e:
            raise RuntimeError(f"Failed to store authentication token: {e}")
    
    def clear_token(self) -> None:
        """Clear stored auth token."""
        try:
            keyring.delete_password("draft-queen", "api_token")
            self.auth_token = None
            self._update_headers()
        except Exception:
            # Token didn't exist, that's fine
            pass
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Make HTTP request to API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/api/pipeline/status")
            **kwargs: Additional arguments to pass to requests
        
        Returns:
            Response JSON as dictionary
        
        Raises:
            ConnectionError: If unable to connect to API
            RuntimeError: If API returns an error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Handle empty responses
            if response.status_code == 204:
                return {}
            
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"message": response.text}
        
        except ConnectionError as e:
            raise ConnectionError(
                f"Unable to connect to API at {self.base_url}. "
                f"Is the backend running? Error: {e}"
            )
        except Timeout:
            raise Timeout(f"API request timed out. Server at {self.base_url} is not responding.")
        except RequestException as e:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("detail", str(error_data))
            except Exception:
                error_msg = str(e)
            raise RuntimeError(f"API error: {error_msg}")
    
    def get(self, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Make GET request."""
        return self._request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        """Make POST request."""
        if data:
            kwargs["json"] = data
        return self._request("POST", endpoint, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        """Make PUT request."""
        if data:
            kwargs["json"] = data
        return self._request("PUT", endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Make DELETE request."""
        return self._request("DELETE", endpoint, **kwargs)
    
    # Pipeline endpoints
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline execution status."""
        return self.get("/api/pipeline/status")
    
    def trigger_pipeline(self, stages: Optional[list[str]] = None) -> Dict[str, Any]:
        """Trigger pipeline execution."""
        data = {}
        if stages:
            data["stages"] = stages
        return self.post("/api/pipeline/run", data if data else None)
    
    def get_pipeline_logs(self, execution_id: str) -> Dict[str, Any]:
        """Get logs for specific execution."""
        return self.get(f"/api/pipeline/logs/{execution_id}")
    
    def get_pipeline_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get pipeline execution history."""
        return self.get("/api/pipeline/history", params={"limit": limit})
    
    def retry_pipeline_execution(self, execution_id: str) -> Dict[str, Any]:
        """Retry failed pipeline execution."""
        return self.post(f"/api/pipeline/retry/{execution_id}")
    
    def get_pipeline_config(self) -> Dict[str, Any]:
        """Get current pipeline configuration."""
        return self.get("/api/pipeline/config")
    
    def update_pipeline_config(self, key: str, value: Any) -> Dict[str, Any]:
        """Update pipeline configuration."""
        return self.put("/api/pipeline/config", {"key": key, "value": value})
    
    # Prospects endpoints
    def list_prospects(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """List prospects."""
        return self.get("/api/prospects", params={"limit": limit, "offset": offset})
    
    def search_prospects(self, name: str) -> Dict[str, Any]:
        """Search prospects by name."""
        return self.get("/api/prospects/search", params={"q": name})
    
    def get_prospect(self, prospect_id: str) -> Dict[str, Any]:
        """Get prospect details."""
        return self.get(f"/api/prospects/{prospect_id}")
    
    def export_prospects(self, format: str = "json", **filters: Any) -> Dict[str, Any]:
        """Export prospects in specified format."""
        data = {"format": format}
        if filters:
            data["filters"] = filters
        return self.post("/api/exports/prospects", data)
    
    # History endpoints
    def get_prospect_history(self, prospect_id: str) -> Dict[str, Any]:
        """Get historical changes for prospect."""
        return self.get(f"/api/history/{prospect_id}")
    
    def get_snapshot(self, snapshot_date: str) -> Dict[str, Any]:
        """Get data snapshot for specific date."""
        return self.get("/api/history/snapshot", params={"date": snapshot_date})
    
    # Quality endpoints
    def list_quality_rules(self) -> Dict[str, Any]:
        """List all quality rules."""
        return self.get("/api/quality/rules")
    
    def get_quality_rule(self, rule_id: str) -> Dict[str, Any]:
        """Get specific quality rule."""
        return self.get(f"/api/quality/rules/{rule_id}")
    
    def create_quality_rules(self, rules_file: str) -> Dict[str, Any]:
        """Create quality rules from file."""
        with open(rules_file, "r") as f:
            rules = yaml.safe_load(f)
        return self.post("/api/quality/rules/import", {"rules": rules})
    
    def get_quality_violations(self, prospect_id: Optional[str] = None) -> Dict[str, Any]:
        """Get quality violations."""
        params = {}
        if prospect_id:
            params["prospect_id"] = prospect_id
        return self.get("/api/quality/violations", params=params)
    
    def run_quality_check(self, force: bool = False) -> Dict[str, Any]:
        """Run quality check."""
        return self.post("/api/quality/check", {"force": force})
    
    def generate_quality_report(self, format: str = "json") -> Dict[str, Any]:
        """Generate quality report."""
        return self.post("/api/quality/report", {"format": format})
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get overall quality metrics."""
        return self.get("/api/quality/metrics")
    
    # Auth endpoints
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate with username and password."""
        result = self.post("/api/auth/login", {
            "username": username,
            "password": password
        })
        if "access_token" in result:
            self.store_token(result["access_token"])
        return result
    
    def logout(self) -> Dict[str, Any]:
        """Logout and clear token."""
        self.clear_token()
        return {"message": "Logged out successfully"}
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status."""
        return self.get("/api/auth/status")
    
    # Admin endpoints
    def health_check(self) -> Dict[str, Any]:
        """Perform system health check."""
        return self.get("/api/health")
    
    def run_db_migration(self) -> Dict[str, Any]:
        """Run database migrations."""
        return self.post("/api/admin/db/migrate")
    
    def create_db_backup(self) -> Dict[str, Any]:
        """Create database backup."""
        return self.post("/api/admin/db/backup")
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get version information."""
        return self.get("/api/version")
