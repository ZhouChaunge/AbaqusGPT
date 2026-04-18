"""ConvergeDoctor - Diagnose Abaqus convergence issues."""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..parsers.msg_parser import MsgParser
from ..parsers.sta_parser import StaParser
from ..knowledge.error_codes import ERROR_DATABASE
from ..llm.client import get_llm_client

console = Console()


class ConvergeDoctor:
    """Agent for diagnosing Abaqus convergence issues."""
    
    def __init__(self, model: str = None):
        self.msg_parser = MsgParser()
        self.sta_parser = StaParser()
        self.llm = get_llm_client(model=model)
    
    def diagnose(self, file_path: Path, verbose: bool = False) -> str:
        """
        Diagnose convergence issues from .msg or .sta file.
        
        Args:
            file_path: Path to .msg or .sta file
            verbose: Show detailed output
            
        Returns:
            Diagnosis report as formatted string
        """
        # Determine file type and parse
        suffix = file_path.suffix.lower()
        
        if suffix == ".msg":
            parsed_data = self.msg_parser.parse(file_path)
        elif suffix == ".sta":
            parsed_data = self.sta_parser.parse(file_path)
        else:
            return f"[red]Unsupported file type: {suffix}[/red]"
        
        # Check for known error patterns
        known_issues = self._check_known_errors(parsed_data)
        
        # Generate diagnosis using LLM
        diagnosis = self._generate_diagnosis(parsed_data, known_issues)
        
        return self._format_report(parsed_data, known_issues, diagnosis, verbose)
    
    def _check_known_errors(self, parsed_data: dict) -> list:
        """Check parsed data against known error patterns."""
        issues = []
        
        for error in parsed_data.get("errors", []):
            for pattern, info in ERROR_DATABASE.items():
                if pattern.lower() in error.lower():
                    issues.append({
                        "pattern": pattern,
                        "error": error,
                        "info": info
                    })
                    break
        
        return issues
    
    def _generate_diagnosis(self, parsed_data: dict, known_issues: list) -> str:
        """Generate diagnosis using LLM."""
        prompt = f"""You are an expert Abaqus analyst. Diagnose the following convergence issue.

Parsed Data:
- Errors: {parsed_data.get('errors', [])}
- Warnings: {parsed_data.get('warnings', [])}
- Last successful increment: {parsed_data.get('last_increment', 'N/A')}
- Total iterations: {parsed_data.get('total_iterations', 'N/A')}

Known issues matched: {[i['pattern'] for i in known_issues]}

Provide:
1. Root cause analysis (most likely cause first)
2. Specific fix recommendations with Abaqus keywords/parameters
3. Prevention tips for future

Be concise and actionable. Use Chinese for the response.
"""
        
        response = self.llm.chat(prompt)
        return response
    
    def _format_report(
        self, 
        parsed_data: dict, 
        known_issues: list, 
        diagnosis: str,
        verbose: bool
    ) -> str:
        """Format the diagnosis report."""
        output = []
        
        # Header
        status = "🔴 收敛失败" if parsed_data.get("errors") else "⚠️ 有警告"
        output.append(Panel(f"[bold]{status}[/bold]", title="诊断结果"))
        
        # Summary table
        if verbose:
            table = Table(title="文件分析摘要")
            table.add_column("项目", style="cyan")
            table.add_column("值", style="white")
            
            table.add_row("错误数", str(len(parsed_data.get("errors", []))))
            table.add_row("警告数", str(len(parsed_data.get("warnings", []))))
            table.add_row("最后增量", str(parsed_data.get("last_increment", "N/A")))
            
            output.append(table)
        
        # Diagnosis
        output.append(Panel(diagnosis, title="💡 诊断分析"))
        
        return "\n".join(str(o) for o in output)
