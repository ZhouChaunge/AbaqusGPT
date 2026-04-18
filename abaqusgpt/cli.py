"""Command-line interface for AbaqusGPT."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="abaqusgpt",
    help="Your AI copilot for Abaqus: modeling, meshing, convergence debugging, and beyond.",
    add_completion=False,
)
console = Console()


@app.command()
def diagnose(
    file: Path = typer.Argument(..., help="Path to .msg or .sta file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use (e.g., glm-4, qwen-max, deepseek-chat)"),
):
    """Diagnose convergence issues from Abaqus output files."""
    from .agents.converge_doctor import ConvergeDoctor
    
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)
    
    doctor = ConvergeDoctor(model=model)
    result = doctor.diagnose(file, verbose=verbose)
    console.print(result)


@app.command()
def generate(
    description: str = typer.Argument(..., help="Natural language description of the model"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("inp", "--format", "-f", help="Output format: inp or python"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use (e.g., glm-4, qwen-max, deepseek-chat)"),
):
    """Generate Abaqus input file or Python script from description."""
    from .agents.inp_generator import InpGenerator
    
    generator = InpGenerator(model=model)
    result = generator.generate(description, format=format)
    
    if output:
        output.write_text(result)
        console.print(f"[green]✓[/green] Generated: {output}")
    else:
        console.print(Panel(result, title="Generated Code"))


@app.command("mesh-check")
def mesh_check(
    file: Path = typer.Argument(..., help="Path to .inp file"),
    report: Path = typer.Option(None, "--report", "-r", help="Save report to file"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use (e.g., glm-4, qwen-max, deepseek-chat)"),
):
    """Analyze mesh quality and provide optimization suggestions."""
    from .agents.mesh_advisor import MeshAdvisor
    
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)
    
    advisor = MeshAdvisor(model=model)
    result = advisor.analyze(file)
    
    if report:
        report.write_text(result)
        console.print(f"[green]✓[/green] Report saved: {report}")
    else:
        console.print(result)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Your question about Abaqus"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use (e.g., glm-4, qwen-max, deepseek-chat)"),
):
    """Ask any question about Abaqus."""
    from .agents.qa_agent import QAAgent
    
    agent = QAAgent(model=model)
    result = agent.answer(question)
    console.print(Panel(result, title="AbaqusGPT"))


@app.command()
def models():
    """List all supported LLM models. / 列出所有支持的大模型"""
    from .llm.client import LLMClient
    from .config import config
    
    available_models = LLMClient.list_available_models()
    configured_providers = config.get_available_providers()
    
    table = Table(title="Supported Models / 支持的模型")
    table.add_column("Provider / 提供商", style="cyan")
    table.add_column("Models / 模型", style="green")
    table.add_column("Status / 状态", style="yellow")
    
    for provider, model_list in available_models.items():
        models_str = ", ".join(model_list)
        
        # Check if provider is configured
        provider_key = provider.lower().split()[0]
        if any(p in provider_key for p in configured_providers):
            status = "✅ Configured"
        else:
            status = "⚠️ API Key not set"
        
        table.add_row(provider, models_str, status)
    
    console.print(table)
    console.print(f"\n[bold]Default model:[/bold] {config.default_model}")
    console.print("[dim]Set API keys in .env file to enable providers[/dim]")


@app.command()
def version():
    """Show version information."""
    from . import __version__
    console.print(f"AbaqusGPT v{__version__}")


if __name__ == "__main__":
    app()
