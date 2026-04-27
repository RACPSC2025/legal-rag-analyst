#!/usr/bin/env python3
"""
Fénix Legal v2 — Test Orchestrator
────────────────────────────────────────────────────────────
Centro de comando para la ejecución y monitoreo de pruebas.
"""

import os
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def print_banner():
    """Muestra el banner principal de Fénix Legal."""
    banner_text = """
    [bold gold1]
    ███████╗███████╗███╗   ██╗██╗██╗  ██╗    ██╗     ███████╗ ██████╗  █████╗ ██╗     
    ██╔════╝██╔════╝████╗  ██║██║╚██╗██╔╝    ██║     ██╔════╝██╔════╝ ██╔══██╗██║     
    █████╗  █████╗  ██╔██╗ ██║██║ ╚███╔╝     ██║     █████╗  ██║  ███╗███████║██║     
    ██╔══╝  ██╔══╝  ██║╚██╗██║██║ ██╔██╗     ██║     ██╔══╝  ██║   ██║██╔══██║██║     
    ██║     ███████╗██║ ╚████║██║██╔╝ ██╗    ███████╗███████╗╚██████╔╝██║  ██║███████╗
    ╚═╝     ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝    ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝[/]
    [bold white]─────────────────  TEST ORCHESTRATOR — ANALISTA LEGAL v2.5  ─────────────────[/]
    """
    console.print(Panel(banner_text, border_style="gold1", expand=False))

def run_pytest(path: str, title: str):
    """Ejecuta pytest en la ruta indicada con un reporte visual."""
    console.print(f"\n[bold blue]🚀 Iniciando: {title}[/]")
    console.print(f"[dim]Ruta: {path}[/]\n")
    
    try:
        # Ejecutamos pytest y capturamos la salida
        cmd = [sys.executable, "-m", "pytest", path, "-v"]
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            console.print(f"\n[bold green]✅ {title} completado con éxito.[/]")
        else:
            console.print(f"\n[bold red]❌ {title} falló. Revisa los errores arriba.[/]")
            
    except Exception as e:
        console.print(f"[bold red]Error crítico al ejecutar tests: {e}[/]")

def main_menu():
    """Menú principal interactivo."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner()
        
        table = Table(show_header=False, box=None)
        table.add_row("[bold cyan]1.[/]", "🧪 [bold white]Pruebas Unitarias[/] (Componentes aislados)")
        table.add_row("[bold cyan]2.[/]", "🔗 [bold white]Pruebas de Integración[/] (Grafo y AWS)")
        table.add_row("[bold cyan]3.[/]", "📊 [bold white]Pruebas de Evaluación[/] (RAGAS y Salud)")
        table.add_row("[bold cyan]4.[/]", "🔥 [bold white]EJECUTAR TODO EL SUITE[/]")
        table.add_row("[bold cyan]5.[/]", "📂 [bold white]Ver Scripts de Utilidad[/]")
        table.add_row("[bold cyan]q.[/]", "🚪 [bold red]Salir[/]")
        
        console.print(Panel(table, title="[bold white]Selecciona una opción[/]", border_style="cyan"))
        
        choice = Prompt.ask("\n[bold yellow]Elección[/]", choices=["1", "2", "3", "4", "5", "q"])
        
        # Obtener la ruta base (directorio tests/)
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        if choice == "1":
            run_pytest(os.path.join(base_path, "unit"), "Unit Tests")
        elif choice == "2":
            run_pytest(os.path.join(base_path, "integration"), "Integration Tests")
        elif choice == "3":
            run_pytest(os.path.join(base_path, "evaluation"), "Evaluation Tests")
        elif choice == "4":
            run_pytest(base_path, "Full Test Suite")
        elif choice == "5":
            scripts_path = os.path.join(base_path, "scripts")
            scripts = os.listdir(scripts_path)
            console.print(f"\n[bold cyan]Scripts disponibles en {scripts_path}:[/]")
            for s in scripts:
                console.print(f" • {s}")
        elif choice == "q":
            console.print("\n[bold gold1]¡Hasta luego, Ronny! Fénix sigue volando.[/]\n")
            break
            
        Prompt.ask("\n[dim]Presiona Enter para continuar...[/]")

if __name__ == "__main__":
    main_menu()
