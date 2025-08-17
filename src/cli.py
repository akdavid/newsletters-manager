#!/usr/bin/env python3

import asyncio
import json
from typing import Any, Dict

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.table import Table

from .agents.orchestrator import OrchestratorAgent
from .utils.config import get_settings
from .utils.logger import get_logger, setup_logger

console = Console()
logger = get_logger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx, verbose):
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    log_level = "DEBUG" if verbose else "INFO"
    setup_logger(log_level)


@cli.command()
@click.pass_context
def collect(ctx):
    """Collect emails from all configured accounts."""
    console.print("🔍 [bold blue]Collecting emails from all accounts...[/bold blue]")

    async def collect_emails():
        orchestrator = OrchestratorAgent({})
        try:
            await orchestrator.start()
            result = await orchestrator.collect_emails_only()
            return result
        finally:
            await orchestrator.stop()

    result = asyncio.run(collect_emails())

    if result.get("status") == "failed":
        console.print(
            f"❌ [bold red]Collection failed:[/bold red] {result.get('error')}"
        )
        return

    collected_count = result.get("collected_count", 0)
    errors = result.get("errors", [])

    console.print(f"✅ [bold green]Collected {collected_count} emails[/bold green]")

    if errors:
        console.print(f"⚠️  [yellow]{len(errors)} errors occurred:[/yellow]")
        for error in errors:
            console.print(f"   • {error}")


@cli.command()
@click.pass_context
def detect(ctx):
    """Detect newsletters from unprocessed emails."""
    console.print("🔎 [bold blue]Detecting newsletters...[/bold blue]")

    async def detect_newsletters():
        orchestrator = OrchestratorAgent({})
        try:
            await orchestrator.start()
            result = await orchestrator.detect_newsletters_only()
            return result
        finally:
            await orchestrator.stop()

    result = asyncio.run(detect_newsletters())

    if result.get("status") == "failed":
        console.print(f"❌ [bold red]Detection failed:[/bold red] {result.get('error')}")
        return

    detected_count = result.get("detected_count", 0)
    processed_count = result.get("processed_count", 0)

    console.print(
        f"✅ [bold green]Detected {detected_count} newsletters from {processed_count} emails[/bold green]"
    )


@cli.command()
@click.pass_context
def summarize(ctx):
    """Generate summary from detected newsletters."""
    console.print("📝 [bold blue]Generating newsletter summary...[/bold blue]")

    async def generate_summary():
        orchestrator = OrchestratorAgent({})
        try:
            await orchestrator.start()
            result = await orchestrator.generate_summary_only()
            return result
        finally:
            await orchestrator.stop()

    result = asyncio.run(generate_summary())

    if result.get("status") == "failed":
        console.print(
            f"❌ [bold red]Summary generation failed:[/bold red] {result.get('error')}"
        )
        return

    if result.get("message"):
        console.print(f"ℹ️  [yellow]{result['message']}[/yellow]")
        return

    summary_id = result.get("summary_id")
    newsletters_count = result.get("newsletters_count", 0)
    email_sent = result.get("email_sent", False)

    console.print(f"✅ [bold green]Summary generated:[/bold green] {summary_id}")
    console.print(f"   📊 {newsletters_count} newsletters summarized")
    console.print(f"   📧 Email sent: {'Yes' if email_sent else 'No'}")


@cli.command()
@click.pass_context
def pipeline(ctx):
    """Run the full newsletter processing pipeline."""
    console.print(
        "🚀 [bold blue]Running full newsletter processing pipeline...[/bold blue]"
    )

    async def run_pipeline():
        orchestrator = OrchestratorAgent({})
        try:
            await orchestrator.start()
            result = await orchestrator.run_full_pipeline()
            return result
        finally:
            await orchestrator.stop()

    result = asyncio.run(run_pipeline())

    console.print("\n📋 [bold]Pipeline Results:[/bold]")

    status = result.get("status", "unknown")
    if status == "failed":
        console.print(f"❌ [bold red]Pipeline failed:[/bold red] {result.get('error')}")
        return

    steps = result.get("steps", {})
    total_duration = result.get("total_duration", 0)

    table = Table(title="Pipeline Step Results")
    table.add_column("Step", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Duration", style="yellow")
    table.add_column("Details", style="white")

    for step_name, step_data in steps.items():
        details = []

        # Email Collection
        if "collected_count" in step_data:
            details.append(f"Collected: {step_data['collected_count']}")

        # Newsletter Detection
        if "detected_count" in step_data:
            details.append(f"Detected: {step_data['detected_count']}")

        # Content Summarization
        if "newsletters_count" in step_data:
            details.append(f"Summarized: {step_data['newsletters_count']}")

        # Email Sending
        if "recipients" in step_data:
            details.append(f"Recipients: {step_data['recipients']}")
        elif "email_sent" in step_data and step_data["email_sent"]:
            details.append("Email sent ✅")

        # Mark Emails Read
        if "emails_marked" in step_data:
            details.append(f"Marked: {step_data['emails_marked']}")
        if "success_rate" in step_data:
            details.append(f"Success: {step_data['success_rate']}")

        table.add_row(
            step_name.replace("_", " ").title(),
            step_data.get("status", "unknown"),
            f"{step_data.get('duration', 0):.2f}s",
            " | ".join(details) if details else "",
        )

    console.print(table)
    console.print(f"\n⏱️  [bold]Total Duration:[/bold] {total_duration:.2f} seconds")
    console.print(f"✅ [bold green]Pipeline completed successfully![/bold green]")


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status and health information."""
    console.print("🏥 [bold blue]Checking system health...[/bold blue]")

    async def get_health():
        orchestrator = OrchestratorAgent({})
        try:
            await orchestrator.start()
            health = await orchestrator.get_system_health()
            return health
        finally:
            await orchestrator.stop()

    health = asyncio.run(get_health())

    console.print("\n🏥 [bold]System Health Report[/bold]")

    orchestrator_health = health.get("orchestrator", {})
    agents_health = health.get("agents", {})

    # Orchestrator status
    orchestrator_panel = Panel(
        f"Status: {orchestrator_health.get('status', 'unknown')}\n"
        f"Agents: {orchestrator_health.get('agents_count', 0)}\n"
        f"Message Broker: {'Running' if orchestrator_health.get('message_broker_running') else 'Stopped'}",
        title="Orchestrator",
        style="green" if orchestrator_health.get("status") == "running" else "red",
    )
    console.print(orchestrator_panel)

    # Agents status table
    table = Table(title="Agents Status")
    table.add_column("Agent", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="white")

    for agent_name, agent_health in agents_health.items():
        status = agent_health.get("status", "unknown")
        details = []

        if "gmail_services" in agent_health:
            details.append(f"Gmail: {agent_health['gmail_services']}")
        if "outlook_service" in agent_health:
            details.append(
                f"Outlook: {'OK' if agent_health['outlook_service'] else 'Error'}"
            )
        if "scheduler_running" in agent_health:
            details.append(
                f"Scheduler: {'Running' if agent_health['scheduler_running'] else 'Stopped'}"
            )
        if "ai_service" in agent_health:
            details.append(f"AI: {'OK' if agent_health['ai_service'] else 'Error'}")

        table.add_row(
            agent_name.replace("_", " ").title(),
            status,
            " | ".join(details) if details else "N/A",
        )

    console.print(table)


@cli.command()
@click.option("--limit", "-l", default=10, help="Number of recent summaries to show")
@click.pass_context
def summaries(ctx, limit):
    """Show recent summaries."""
    console.print(f"📑 [bold blue]Showing {limit} most recent summaries...[/bold blue]")

    async def get_summaries():
        orchestrator = OrchestratorAgent({})
        try:
            await orchestrator.start()
            summaries = await orchestrator.get_recent_summaries(limit)
            return summaries
        finally:
            await orchestrator.stop()

    summaries_data = asyncio.run(get_summaries())

    if not summaries_data:
        console.print("ℹ️  [yellow]No summaries found[/yellow]")
        return

    table = Table(title=f"Recent Summaries (Last {limit})")
    table.add_column("ID", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Newsletters", style="white")
    table.add_column("Duration", style="magenta")

    for summary in summaries_data:
        date_str = summary.get("generation_date", "")[:19].replace("T", " ")
        duration = summary.get("processing_duration", 0)

        table.add_row(
            summary.get("id", "N/A")[:12] + "...",
            date_str,
            summary.get("status", "unknown"),
            str(summary.get("newsletters_count", 0)),
            f"{duration:.1f}s" if duration else "N/A",
        )

    console.print(table)


@cli.command()
@click.pass_context
def config(ctx):
    """Show current configuration."""
    console.print("⚙️  [bold blue]Current Configuration:[/bold blue]")

    settings = get_settings()

    config_data = {
        "Daily Summary Time": settings.daily_summary_time,
        "Timezone": settings.timezone,
        "OpenAI Model": settings.openai_model,
        "Max Tokens": settings.openai_max_tokens,
        "Min Confidence Score": settings.min_confidence_score,
        "Max Emails Per Run": settings.max_emails_per_run,
        "Summary Max Newsletters": settings.summary_max_newsletters,
        "Database URL": settings.database_url,
        "Log Level": settings.log_level,
    }

    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    for key, value in config_data.items():
        table.add_row(key, str(value))

    console.print(table)


if __name__ == "__main__":
    cli()
