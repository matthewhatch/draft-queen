# Draft Queen CLI - Command Reference

Comprehensive command-line interface for managing the Draft Queen NFL data pipeline and analytics platform.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Authentication](#authentication)
- [Commands](#commands)
  - [Pipeline Management](#pipeline-management)
  - [Prospect Queries](#prospect-queries)
  - [Historical Data](#historical-data)
  - [Quality Management](#quality-management)
  - [System Administration](#system-administration)
- [Common Workflows](#common-workflows)
- [Output Formats](#output-formats)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites
- Python 3.9+
- Poetry (for development)
- PostgreSQL (for backend)

### From Source

```bash
cd draft-queen
poetry install
```

### CLI Entry Point

After installation, the `dq` command becomes available:

```bash
dq --help
dq --version
```

---

## Quick Start

### 1. Initialize Configuration

```bash
dq config init
```

Interactive wizard will prompt for:
- API endpoint URL (default: `http://localhost:8000`)
- Profile name
- Output format preference (table/json)
- Verbose logging

### 2. Authenticate

```bash
dq auth login
```

Securely stores authentication token in system keyring.

### 3. Check System Health

```bash
dq health check
```

Verifies backend connectivity and component status.

### 4. List Prospects

```bash
dq prospects list
```

---

## Configuration

### Configuration File

Default location: `~/.dq/config.yaml`

Example:
```yaml
api_url: http://localhost:8000
profile: default
output_format: table
verbose: false
```

### Configuration Commands

```bash
# Display current configuration
dq config show

# Validate configuration file
dq config validate

# Update a setting
dq config set api_url http://production-api:8000
dq config set verbose true

# Reinitialize configuration
dq config init
```

### Custom Configuration File

```bash
dq --config /path/to/custom/config.yaml [COMMAND]
```

### Override API Endpoint

```bash
dq --api-url http://custom-api:8000 [COMMAND]
```

### Verbose Output

```bash
dq -v [COMMAND]
dq --verbose [COMMAND]
```

---

## Authentication

### Login

```bash
dq auth login
```

Prompts for username and password. Token is securely stored using system keyring.

### Check Status

```bash
dq auth status
```

Shows current user, email, and role if authenticated.

### Logout

```bash
dq auth logout
```

Removes stored authentication token.

---

## Commands

### Pipeline Management

#### Status

Show current pipeline execution status:

```bash
dq pipeline status
```

Output includes:
- Current execution status
- Running stages
- Last completed execution
- Upcoming schedules

#### Run

Trigger immediate pipeline execution:

```bash
# Run all stages
dq pipeline run

# Run specific stages
dq pipeline run --stages yahoo
dq pipeline run --stages yahoo --stages espn
```

Available stages:
- `yahoo` - Yahoo Sports scraper
- `espn` - ESPN injury data
- `reconciliation` - Data reconciliation
- `quality` - Quality rules evaluation
- `snapshot` - Historical snapshot

#### Logs

View execution logs:

```bash
# View logs for specific execution
dq pipeline logs abc123def456

# View last 100 lines
dq pipeline logs abc123def456 | tail -100
```

#### History

Show pipeline execution history:

```bash
# Show last 10 executions (default)
dq pipeline history

# Show last 50 executions
dq pipeline history --limit 50
```

Displays:
- Execution ID
- Status (success/failed/partial)
- Start time
- Duration

#### Retry

Retry a failed execution:

```bash
dq pipeline retry abc123def456
```

Prompts for confirmation before retrying.

#### Configuration

View pipeline configuration:

```bash
dq pipeline config show
```

Update configuration:

```bash
dq pipeline config set retry_attempts 5
dq pipeline config set timeout 300
```

---

### Prospect Queries

#### List Prospects

```bash
# List all prospects (paginated)
dq prospects list

# List with custom limit
dq prospects list --limit 100

# Filter by position
dq prospects list --position QB

# Filter by college
dq prospects list --college Alabama

# Filter by height range
dq prospects list --height-min 6.0 --height-max 6.4

# Filter by weight range
dq prospects list --weight-min 200 --weight-max 250

# Combine filters
dq prospects list --position QB --college Alabama --height-min 6.0

# Output as JSON
dq prospects list --json-output
```

Options:
- `--limit N` - Number of results (default: 50)
- `--offset N` - Pagination offset (default: 0)
- `--position TEXT` - Filter by position (QB, RB, WR, TE, OL, etc.)
- `--college TEXT` - Filter by college name
- `--height-min FLOAT` - Minimum height in inches
- `--height-max FLOAT` - Maximum height in inches
- `--weight-min INT` - Minimum weight in pounds
- `--weight-max INT` - Maximum weight in pounds
- `--json-output` - Output as JSON instead of table

#### Search Prospects

Fuzzy name search:

```bash
# Search by name
dq prospects search "Patrick Mahomes"

# Partial name search
dq prospects search "mahomes"

# Output as JSON
dq prospects search "mahomes" --json-output
```

Returns prospects with match confidence scores.

#### Get Prospect Details

```bash
dq prospects get abc123
```

Displays:
- Basic info (ID, position, college, year)
- Physical attributes (height, weight, hand size, arm length)
- Performance metrics (40-time, vertical, broad jump, 3-cone)
- Injury history
- Rankings

#### Export Prospects

Export data in multiple formats:

```bash
# Export as JSON
dq prospects export --format json --output prospects.json

# Export as CSV
dq prospects export --format csv --output prospects.csv --position QB

# Export as Parquet
dq prospects export --format parquet --output prospects.parquet

# Export with filters
dq prospects export --format csv --output qbs.csv --position QB --college Alabama

# Export with limit
dq prospects export --format json --output top-100.json --limit 100
```

Options:
- `--format [json|csv|parquet]` - Output format (default: json)
- `-o, --output PATH` - Output file path
- `--position TEXT` - Filter by position
- `--college TEXT` - Filter by college
- `--height-min FLOAT` - Minimum height
- `--height-max FLOAT` - Maximum height
- `--weight-min INT` - Minimum weight
- `--weight-max INT` - Maximum weight
- `--limit INT` - Maximum records to export

---

### Historical Data

#### Get Prospect History

View all historical changes for a prospect:

```bash
# Show last 20 changes (default)
dq history get abc123

# Show more changes
dq history get abc123 --limit 50

# Output as JSON
dq history get abc123 --json-output
```

Shows:
- Date of change
- Field that changed
- Old and new values
- Data source

#### Snapshot

Query prospect data as it existed on a specific date:

```bash
# Get data snapshot for a date
dq history snapshot 2026-02-01

# Filter by position
dq history snapshot 2026-02-01 --position QB

# Filter by college
dq history snapshot 2026-02-01 --college Alabama

# Limit results
dq history snapshot 2026-02-01 --limit 100

# Output as JSON
dq history snapshot 2026-02-01 --json-output
```

Options:
- `--position TEXT` - Filter by position
- `--college TEXT` - Filter by college
- `--limit INT` - Number of records (default: 50)
- `--json-output` - Output as JSON

---

### Quality Management

#### List Rules

View all active quality rules:

```bash
dq quality rules list

# Output as JSON
dq quality rules list --json-output
```

#### Show Rule Details

```bash
dq quality rules show rule-001
```

Shows rule configuration, thresholds, and type.

#### Create Rules from File

Import quality rules from YAML:

```bash
dq quality rules create --file rules.yaml
```

YAML format:
```yaml
rules:
  - name: "QB Height"
    type: "business_logic"
    active: true
    description: "Quarterbacks must be at least 6'0\""
    config:
      field: "height"
      operator: ">="
      value: 72
  
  - name: "BMI Check"
    type: "consistency"
    description: "Validate BMI calculations"
    config:
      fields: ["height", "weight"]
      relationship: "bmi"
```

#### List Violations

View data quality violations:

```bash
# Show all violations
dq quality violations list

# Filter by prospect
dq quality violations list --prospect-id abc123

# Filter by severity
dq quality violations list --severity error

# Show more violations
dq quality violations list --limit 100

# Output as JSON
dq quality violations list --json-output
```

Options:
- `--prospect-id TEXT` - Filter by specific prospect
- `--severity [error|warning|info]` - Filter by severity level
- `--limit INT` - Number of violations (default: 50)
- `--json-output` - Output as JSON

#### Run Quality Check

Evaluate all quality rules against prospect data:

```bash
# Run quality check
dq quality check

# Force check (bypass cooldown)
dq quality check --force
```

Prompts for confirmation before running.

#### Generate Report

Generate quality report:

```bash
# Generate JSON report
dq quality report --format json

# Generate HTML report
dq quality report --format html --output report.html

# Generate PDF report
dq quality report --format pdf --output report.pdf
```

#### View Metrics

See overall quality metrics dashboard:

```bash
dq quality metrics

# Output as JSON
dq quality metrics --json-output
```

Shows:
- Overall quality score (0-100%)
- Violation counts by severity
- Top rules triggered
- Last check timestamp

---

### System Administration

#### Health Check

Verify system health:

```bash
dq health check
```

Checks:
- Backend API connectivity
- Database connectivity
- Pipeline status
- Cache/Redis status
- External API endpoints

#### Database Migrations

Run database migrations:

```bash
dq db migrate
```

Shows:
- Number of migrations applied
- Current schema version

Prompts for confirmation before running.

#### Database Backup

Create database backup:

```bash
dq db backup

# Specify output file
dq db backup --output backup_2026-02-09.sql
```

Shows:
- Backup ID
- Backup size
- Backup location

Prompts for confirmation before creating.

#### Version Information

Show CLI and backend versions:

```bash
dq version
```

---

## Common Workflows

### Daily Operations

```bash
# Morning: Check system health
dq health check

# Run data pipeline
dq pipeline run

# Check for violations
dq quality violations list --severity error

# View pipeline status
dq pipeline history --limit 5
```

### Data Analysis

```bash
# Search for specific prospect
dq prospects search "Patrick Mahomes"

# Get detailed information
dq prospects get abc123

# View historical changes
dq history get abc123

# Export for analysis
dq prospects export --format csv --output analysis.csv --position QB
```

### Quality Management

```bash
# Import new rules
dq quality rules create --file new_rules.yaml

# Run quality check
dq quality check --force

# View violations
dq quality violations list

# Generate report
dq quality report --format html --output weekly_report.html

# Review metrics
dq quality metrics
```

### System Maintenance

```bash
# Check health
dq health check

# Run migrations
dq db migrate

# Create backup
dq db backup

# View configuration
dq config show
```

### First-Time Setup

```bash
# 1. Initialize configuration
dq config init

# 2. Validate setup
dq config validate

# 3. Authenticate
dq auth login

# 4. Check health
dq health check

# 5. Run pipeline
dq pipeline run
```

---

## Output Formats

### Table Output (Default)

```bash
dq prospects list
```

Produces formatted table with colors and alignment.

### JSON Output

```bash
dq prospects list --json-output
```

Outputs raw JSON for scripting and automation.

### Piping

Combine with standard Unix tools:

```bash
# Filter results
dq prospects list --json-output | jq '.prospects[] | select(.position=="QB")'

# Count violations
dq quality violations list --json-output | jq 'length'

# Export and count
dq prospects list --json-output | jq '.prospects | length'
```

---

## Troubleshooting

### Connection Issues

```bash
# Check health
dq health check

# Validate configuration
dq config validate

# Test API endpoint
dq --api-url http://api:8000 config validate
```

### Authentication Issues

```bash
# Check auth status
dq auth status

# Re-authenticate
dq auth logout
dq auth login

# Check keyring access
# Verify system keyring is accessible (may require password manager)
```

### Configuration Issues

```bash
# Show current config
dq config show

# Reset configuration
dq config init

# Validate config file
dq config validate
```

### Pipeline Issues

```bash
# Check pipeline status
dq pipeline status

# View recent executions
dq pipeline history --limit 20

# Check logs
dq pipeline logs abc123

# Retry failed execution
dq pipeline retry abc123
```

### Data Quality Issues

```bash
# List all violations
dq quality violations list

# View specific prospect violations
dq quality violations list --prospect-id abc123

# View rules
dq quality rules list

# Run quality check
dq quality check --force
```

### Common Error Messages

| Error | Solution |
|-------|----------|
| `Unable to connect to API` | Check API endpoint is running: `dq config validate` |
| `Not authenticated` | Login: `dq auth login` |
| `Configuration not found` | Initialize: `dq config init` |
| `Invalid date format` | Use YYYY-MM-DD format for dates |
| `Permission denied` | Check file permissions for config files |

---

## Environment Variables

Configuration can also be set via environment variables:

```bash
export DQ_API_URL=http://production-api:8000
export DQ_PROFILE=production
export DQ_OUTPUT_FORMAT=json
export DQ_VERBOSE=true

dq prospects list
```

---

## Advanced Usage

### Scripting

```bash
#!/bin/bash

# Export all QBs
dq prospects export --format json --position QB --output qbs.json

# Check for violations
violations=$(dq quality violations list --json-output | jq 'length')
if [ $violations -gt 0 ]; then
    echo "Warning: $violations violations found"
    dq quality report --format html --output report.html
fi
```

### Cron Jobs

```bash
# Daily pipeline run and backup
0 3 * * * dq pipeline run && dq db backup

# Weekly quality report
0 9 * * 1 dq quality check && dq quality report --format html --output /reports/weekly.html
```

### Integration with Other Tools

```bash
# Export to PostgreSQL
dq prospects export --format csv --output /tmp/prospects.csv
psql -d draft_queen -c "\\COPY prospects FROM '/tmp/prospects.csv' WITH (FORMAT CSV)"

# Send report via email
dq quality report --format html --output report.html
mail -s "Weekly Quality Report" team@example.com < report.html
```

---

## Performance Tips

- Use `--limit` to reduce data transfer for large exports
- Use `--json-output` for scripting (faster parsing than tables)
- Cache configurations locally with `dq config show > config.backup.yaml`
- Use specific filters to reduce result sets before export

---

## Support

For issues, questions, or contributions:
- Check logs: `dq pipeline logs [EXEC_ID]`
- Validate setup: `dq config validate`
- Review health: `dq health check`
- Contact: team@example.com

---

## Version

Current CLI Version: 0.1.0  
Requires Backend: 0.1.0+

Check version: `dq version`
