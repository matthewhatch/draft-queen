"""Data quality rules and violations management commands (US-029)."""

import click
import json
import yaml
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.status import Status
from rich.panel import Panel
from pathlib import Path

console = Console()


@click.group()
def quality():
    """Manage data quality rules and view violations."""
    pass


# Rules subcommand group
@quality.group()
def rules():
    """Manage quality rules."""
    pass


@rules.command("list")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.pass_context
def rules_list(ctx, json_output):
    """List all active quality rules.
    
    Examples:
        $ dq quality rules list
        $ dq quality rules list --json-output
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status("[bold cyan]Fetching quality rules...", console=console) as status:
            response = client.list_quality_rules()
        
        if not response.get("rules"):
            console.print("[yellow]No quality rules configured[/yellow]")
            return
        
        rules_list = response["rules"]
        
        if json_output:
            console.print_json(data=rules_list)
        else:
            # Display as table
            table = Table(title=f"Quality Rules ({len(rules_list)} total)", 
                         show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Description", style="white")
            table.add_column("Status", style="blue")
            
            for rule in rules_list:
                status_color = "green" if rule.get("active", True) else "red"
                status_text = "[green]active[/green]" if rule.get("active", True) else "[red]inactive[/red]"
                
                table.add_row(
                    str(rule.get("id", "N/A"))[:12],
                    rule.get("name", "N/A"),
                    rule.get("type", "N/A"),
                    rule.get("description", "N/A")[:40],
                    status_text
                )
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error fetching rules: {e}[/red]")
        ctx.exit(1)


@rules.command("show")
@click.argument("rule_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.pass_context
def rules_show(ctx, rule_id, json_output):
    """Show detailed information about a specific rule.
    
    Examples:
        $ dq quality rules show rule-001
        $ dq quality rules show rule-001 --json-output
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status(f"[bold cyan]Fetching rule {rule_id}...", console=console) as status:
            response = client.get_quality_rule(rule_id)
        
        if not response.get("rule"):
            console.print(f"[yellow]Rule {rule_id} not found[/yellow]")
            return
        
        rule = response["rule"]
        
        if json_output:
            console.print_json(data=rule)
        else:
            # Display rule details
            console.print(f"[bold cyan]{rule.get('name', 'Unknown')}[/bold cyan]")
            console.print()
            
            # Basic info
            table = Table(show_header=False, box=None)
            table.add_column("", style="cyan", width=20)
            table.add_column("", style="green")
            
            table.add_row("ID", rule.get("id", "N/A"))
            table.add_row("Type", rule.get("type", "N/A"))
            table.add_row("Status", "[green]Active[/green]" if rule.get("active", True) else "[red]Inactive[/red]")
            table.add_row("Description", rule.get("description", "N/A"))
            
            console.print(table)
            console.print()
            
            # Configuration
            if rule.get("config"):
                console.print("[bold]Configuration[/bold]")
                config_table = Table(show_header=False, box=None)
                config_table.add_column("", style="cyan", width=20)
                config_table.add_column("", style="green")
                
                for key, value in rule["config"].items():
                    config_table.add_row(str(key), json.dumps(value) if isinstance(value, (dict, list)) else str(value))
                
                console.print(config_table)
    
    except Exception as e:
        console.print(f"[red]Error fetching rule: {e}[/red]")
        ctx.exit(1)


@rules.command("create")
@click.option("--file", type=click.Path(exists=True), required=True, help="YAML file with rules")
@click.pass_context
def rules_create(ctx, file):
    """Create quality rules from YAML file.
    
    YAML Format:
        rules:
          - name: "QB Height"
            type: "business_logic"
            active: true
            description: "Quarterbacks must be at least 6'0\""
            config:
              field: "height"
              operator: ">="
              value: 72
    
    Examples:
        $ dq quality rules create --file rules.yaml
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    # Validate file exists and is readable
    try:
        with open(file, "r") as f:
            file_content = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[red]Error reading YAML file: {e}[/red]")
        ctx.exit(1)
    
    if not file_content or "rules" not in file_content:
        console.print("[red]Invalid YAML format. Expected 'rules:' key at root level[/red]")
        ctx.exit(1)
    
    try:
        with Status("[bold cyan]Creating rules...", console=console) as status:
            response = client.create_quality_rules(file)
        
        if response.get("created"):
            console.print(f"[green]✓ Created {response['created']} rule(s)[/green]")
            if response.get("failed"):
                console.print(f"[yellow]⚠ Failed to create {response['failed']} rule(s)[/yellow]")
            if response.get("errors"):
                for error in response["errors"]:
                    console.print(f"  [red]Error: {error}[/red]")
        else:
            console.print("[yellow]No rules created[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Error creating rules: {e}[/red]")
        ctx.exit(1)


# Violations subcommand group
@quality.group()
def violations():
    """View quality violations."""
    pass


@violations.command("list")
@click.option("--prospect-id", type=str, help="Filter by specific prospect")
@click.option("--severity", type=click.Choice(["error", "warning", "info"]), help="Filter by severity")
@click.option("--limit", default=50, type=int, help="Number of violations to show")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.pass_context
def violations_list(ctx, prospect_id, severity, limit, json_output):
    """Show current data quality violations.
    
    Examples:
        $ dq quality violations list
        $ dq quality violations list --prospect-id abc123
        $ dq quality violations list --severity error --limit 100
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status("[bold cyan]Fetching violations...", console=console) as status:
            response = client.get_quality_violations(prospect_id=prospect_id)
        
        if not response.get("violations"):
            console.print("[green]✓ No violations found![/green]")
            return
        
        violations = response["violations"]
        
        # Apply severity filter if specified
        if severity:
            violations = [v for v in violations if v.get("severity") == severity]
        
        violations = violations[:limit]
        
        if json_output:
            console.print_json(data=violations)
        else:
            # Display as table with severity coloring
            table = Table(title=f"Quality Violations ({len(violations)} found)", 
                         show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan")
            table.add_column("Prospect", style="green")
            table.add_column("Rule", style="yellow")
            table.add_column("Severity", style="white")
            table.add_column("Message", style="white")
            
            for violation in violations:
                severity_color = {
                    "error": "red",
                    "warning": "yellow",
                    "info": "blue"
                }.get(violation.get("severity", "info"), "white")
                
                severity_badge = f"[{severity_color}]{violation.get('severity', 'info').upper()}[/{severity_color}]"
                
                table.add_row(
                    str(violation.get("id", "N/A"))[:12],
                    violation.get("prospect_name", "N/A"),
                    violation.get("rule_name", "N/A"),
                    severity_badge,
                    violation.get("message", "N/A")[:40]
                )
            
            console.print(table)
            
            # Summary statistics
            console.print()
            error_count = len([v for v in violations if v.get("severity") == "error"])
            warning_count = len([v for v in violations if v.get("severity") == "warning"])
            info_count = len([v for v in violations if v.get("severity") == "info"])
            
            console.print(f"[red]{error_count} errors[/red] | [yellow]{warning_count} warnings[/yellow] | [blue]{info_count} infos[/blue]")
    
    except Exception as e:
        console.print(f"[red]Error fetching violations: {e}[/red]")
        ctx.exit(1)


# Main quality commands
@quality.command()
@click.option("--force", is_flag=True, help="Force check even if recently run")
@click.pass_context
def check(ctx, force):
    """Run data quality check on all prospects.
    
    This will evaluate all quality rules against current prospect data
    and update violation records.
    
    Examples:
        $ dq quality check
        $ dq quality check --force
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    if not force:
        if not click.confirm("This will re-evaluate all quality rules. Continue?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    try:
        with Status("[bold cyan]Running quality check...", console=console) as status:
            response = client.run_quality_check(force=force)
        
        console.print(f"[green]✓ Quality check completed[/green]")
        
        if response.get("stats"):
            stats = response["stats"]
            console.print()
            console.print(f"  Records checked: {stats.get('total_records', 'N/A')}")
            console.print(f"  Violations found: {stats.get('violations_found', 'N/A')}")
            console.print(f"  Duration: {stats.get('duration_seconds', 'N/A')}s")
    
    except Exception as e:
        console.print(f"[red]Error running quality check: {e}[/red]")
        ctx.exit(1)


@quality.command()
@click.option("--format", type=click.Choice(["json", "html", "pdf"]), default="json", help="Report format")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.pass_context
def report(ctx, format, output):
    """Generate quality report.
    
    Examples:
        $ dq quality report
        $ dq quality report --format html --output report.html
        $ dq quality report --format pdf --output report.pdf
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status(f"[bold cyan]Generating {format.upper()} report...", console=console) as status:
            response = client.generate_quality_report(format=format)
        
        # Determine output destination
        if output:
            output_path = Path(output)
        else:
            output_path = Path(f"quality_report.{format}")
        
        # Write report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            with open(output_path, "w") as f:
                json.dump(response.get("data", {}), f, indent=2)
        else:
            # For HTML and PDF, write as binary
            with open(output_path, "wb") as f:
                content = response.get("content", response.get("data", ""))
                if isinstance(content, str):
                    f.write(content.encode())
                else:
                    f.write(content)
        
        console.print(f"[green]✓ Report generated[/green]")
        console.print(f"  Format: {format.upper()}")
        console.print(f"  Output: {output_path.resolve()}")
    
    except Exception as e:
        console.print(f"[red]Error generating report: {e}[/red]")
        ctx.exit(1)


@quality.command()
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.pass_context
def metrics(ctx, json_output):
    """Show overall data quality metrics.
    
    Examples:
        $ dq quality metrics
        $ dq quality metrics --json-output
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status("[bold cyan]Fetching quality metrics...", console=console) as status:
            response = client.get_quality_metrics()
        
        metrics_data = response.get("metrics", {})
        
        if json_output:
            console.print_json(data=metrics_data)
        else:
            # Display metrics in a nice panel format
            console.print()
            
            # Overall quality score
            score = metrics_data.get("overall_score", 0)
            score_color = "green" if score >= 90 else "yellow" if score >= 70 else "red"
            
            console.print(Panel(
                f"[bold {score_color}]{score:.1f}%[/{score_color}]",
                title="[bold]Overall Quality Score[/bold]",
                expand=False
            ))
            
            # Breakdown by severity
            console.print()
            table = Table(title="Violations by Severity", show_header=True, header_style="bold magenta")
            table.add_column("Severity", style="cyan")
            table.add_column("Count", style="green")
            table.add_column("Percentage", style="yellow")
            
            total_violations = sum([
                metrics_data.get("total_errors", 0),
                metrics_data.get("total_warnings", 0),
                metrics_data.get("total_infos", 0)
            ])
            
            if total_violations > 0:
                for severity, key in [("Error", "total_errors"), ("Warning", "total_warnings"), ("Info", "total_infos")]:
                    count = metrics_data.get(key, 0)
                    pct = (count / total_violations * 100) if total_violations > 0 else 0
                    
                    color = "red" if severity == "Error" else "yellow" if severity == "Warning" else "blue"
                    table.add_row(
                        f"[{color}]{severity}[/{color}]",
                        str(count),
                        f"{pct:.1f}%"
                    )
                
                console.print(table)
            else:
                console.print("[green]✓ No violations found[/green]")
            
            # Rule breakdown
            console.print()
            if metrics_data.get("rules_triggered"):
                console.print("[bold]Top Rules Triggered[/bold]")
                rules_table = Table(show_header=True, header_style="bold magenta")
                rules_table.add_column("Rule", style="cyan")
                rules_table.add_column("Violations", style="green")
                
                for rule_name, count in list(metrics_data.get("rules_triggered", {}).items())[:10]:
                    rules_table.add_row(rule_name, str(count))
                
                console.print(rules_table)
            
            # Last check info
            console.print()
            last_check = metrics_data.get("last_check_time")
            if last_check:
                console.print(f"[dim]Last quality check: {last_check}[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error fetching metrics: {e}[/red]")
        ctx.exit(1)
