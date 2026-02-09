"""Authentication commands (US-030)."""

import click
from rich.console import Console
from rich.status import Status
from rich.table import Table
from rich.prompt import Prompt

console = Console()


@click.group()
def auth():
    """Manage authentication with the backend."""
    pass


@auth.command()
@click.pass_context
def login(ctx):
    """Authenticate with the backend.
    
    Prompts for username and password, then stores authentication token
    securely in system keyring.
    
    Example:
        $ dq auth login
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    # Check if already authenticated
    try:
        status = client.get_auth_status()
        if status.get("authenticated"):
            console.print("[yellow]⚠ Already authenticated[/yellow]")
            if click.confirm("Login with different credentials?"):
                pass
            else:
                return
    except Exception:
        pass
    
    # Prompt for credentials
    console.print("[bold cyan]Authenticating with draft-queen backend[/bold cyan]")
    console.print()
    
    username = Prompt.ask("[yellow]Username[/yellow]")
    password = Prompt.ask("[yellow]Password[/yellow]", password=True)
    
    try:
        with Status("[bold cyan]Authenticating...", console=console) as status:
            result = client.login(username, password)
        
        if result.get("access_token"):
            console.print("[green]✓ Authentication successful[/green]")
            console.print(f"  User: {result.get('user', {}).get('username', username)}")
            console.print(f"  Token stored securely in system keyring")
        else:
            console.print("[red]Authentication failed[/red]")
            if result.get("detail"):
                console.print(f"  Error: {result['detail']}")
    
    except Exception as e:
        console.print(f"[red]Authentication error: {e}[/red]")
        ctx.exit(1)


@auth.command()
@click.pass_context
def logout(ctx):
    """Clear authentication token.
    
    Removes stored authentication token from system keyring.
    
    Example:
        $ dq auth logout
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        client.logout()
        console.print("[green]✓ Logged out successfully[/green]")
        console.print("  Authentication token cleared")
    except Exception as e:
        console.print(f"[red]Error logging out: {e}[/red]")
        ctx.exit(1)


@auth.command()
@click.pass_context
def status(ctx):
    """Show current authentication status.
    
    Example:
        $ dq auth status
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status("[bold cyan]Checking authentication status...", console=console) as status:
            response = client.get_auth_status()
        
        console.print()
        
        if response.get("authenticated"):
            console.print("[green]✓ Authenticated[/green]")
            
            table = Table(show_header=False, box=None)
            table.add_column("", style="cyan", width=20)
            table.add_column("", style="green")
            
            user = response.get("user", {})
            table.add_row("User", user.get("username", "N/A"))
            table.add_row("Email", user.get("email", "N/A"))
            table.add_row("Role", user.get("role", "N/A"))
            
            console.print(table)
        else:
            console.print("[yellow]Not authenticated[/yellow]")
            console.print("Run 'dq auth login' to authenticate")
    
    except Exception as e:
        console.print(f"[red]Error checking status: {e}[/red]")
        ctx.exit(1)
