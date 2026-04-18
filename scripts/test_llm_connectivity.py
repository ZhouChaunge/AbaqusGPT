#!/usr/bin/env python3
"""
LLM Connectivity Test Script / 大模型连通性测试脚本

Usage / 使用方法:
    python scripts/test_llm_connectivity.py [model_name]

Examples / 示例:
    python scripts/test_llm_connectivity.py              # Test default model
    python scripts/test_llm_connectivity.py glm-4        # Test GLM-4
    python scripts/test_llm_connectivity.py qwen-max     # Test Qwen-Max
    python scripts/test_llm_connectivity.py deepseek-chat # Test DeepSeek
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from abaqusgpt.config import config
from abaqusgpt.llm.client import LLMClient

console = Console()


def test_single_model(model_name: str) -> tuple[bool, str, float]:
    """
    Test a single model's connectivity.

    Returns:
        (success, message, latency_ms)
    """
    try:
        start = time.time()
        client = LLMClient(model=model_name)
        response = client.chat(
            message="Hello, please respond with just 'OK' to confirm you're working.",
            max_tokens=10,
        )
        latency = (time.time() - start) * 1000

        if response and len(response.strip()) > 0:
            return True, response.strip()[:50], latency
        else:
            return False, "Empty response", 0

    except Exception as e:
        return False, str(e)[:100], 0


def test_all_configured_models():
    """Test all models that have API keys configured."""
    available_models = LLMClient.list_available_models()
    configured_providers = config.get_available_providers()

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for provider, models in available_models.items():
            # Check if provider is likely configured
            provider_key = provider.lower().split()[0]
            if configured_providers and provider_key not in [p.lower() for p in configured_providers]:
                continue

            for model in models:
                task = progress.add_task(f"Testing {model}...", total=None)
                success, message, latency = test_single_model(model)
                results.append((provider, model, success, message, latency))
                progress.remove_task(task)

    # Display results
    table = Table(title="LLM Connectivity Test Results / 连通性测试结果")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Response/Error", style="yellow", max_width=40)
    table.add_column("Latency", style="magenta")

    for provider, model, success, message, latency in results:
        status = "✅ OK" if success else "❌ Failed"
        latency_str = f"{latency:.0f}ms" if success else "-"
        table.add_row(provider, model, status, message, latency_str)

    console.print(table)

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r[2])
    console.print(f"\n[bold]Summary:[/bold] {passed}/{total} models working")


def main():
    console.print("[bold cyan]AbaqusGPT LLM Connectivity Test[/bold cyan]\n")

    if len(sys.argv) > 1:
        # Test specific model
        model_name = sys.argv[1]
        console.print(f"Testing model: [bold]{model_name}[/bold]\n")

        success, message, latency = test_single_model(model_name)

        if success:
            console.print("[green]✅ Success![/green]")
            console.print(f"Response: {message}")
            console.print(f"Latency: {latency:.0f}ms")
        else:
            console.print("[red]❌ Failed![/red]")
            console.print(f"Error: {message}")
    else:
        # Test all configured models
        console.print("Testing all models with configured API keys...\n")
        console.print(f"[dim]Default model: {config.default_model}[/dim]")
        console.print(f"[dim]Configured providers: {', '.join(config.get_available_providers())}[/dim]\n")

        test_all_configured_models()


if __name__ == "__main__":
    main()
