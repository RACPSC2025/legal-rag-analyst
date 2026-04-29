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

def submenu_unit_tests():
    """Submenú para pruebas unitarias."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner()
        
        console.print("\n[bold cyan]═══ PRUEBAS UNITARIAS ═══[/]\n")
        
        table = Table(show_header=False, box=None)
        table.add_row("[bold cyan]1.[/]", "🔍 [bold white]Contextual Compression[/]")
        table.add_row("[bold cyan]2.[/]", "🔎 [bold white]Hybrid Search[/]")
        table.add_row("[bold cyan]3.[/]", "📋 [bold white]Metadata Filters[/]")
        table.add_row("[bold cyan]4.[/]", "🤖 [bold white]Model Hub[/]")
        table.add_row("[bold cyan]5.[/]", "🔄 [bold white]Query Expansion[/]")
        table.add_row("[bold cyan]6.[/]", "📊 [bold white]Table Processor[/] [bold yellow](TASK-015)[/]")
        table.add_row("[bold cyan]7.[/]", "🔥 [bold white]TODOS los tests unitarios[/]")
        table.add_row("[bold cyan]b.[/]", "⬅️  [bold white]Volver al menú principal[/]")
        
        console.print(Panel(table, title="[bold white]Selecciona un módulo[/]", border_style="cyan"))
        
        choice = Prompt.ask("\n[bold yellow]Elección[/]", choices=["1", "2", "3", "4", "5", "6", "7", "b"])
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        unit_path = os.path.join(base_path, "unit")
        
        if choice == "1":
            run_pytest(os.path.join(unit_path, "test_contextual_compression.py"), "Contextual Compression Tests")
        elif choice == "2":
            run_pytest(os.path.join(unit_path, "test_hybrid_search_v2.py"), "Hybrid Search Tests")
        elif choice == "3":
            run_pytest(os.path.join(unit_path, "test_metadata_filters.py"), "Metadata Filters Tests")
        elif choice == "4":
            run_pytest(os.path.join(unit_path, "test_model_hub_v2.py"), "Model Hub Tests")
        elif choice == "5":
            run_pytest(os.path.join(unit_path, "test_query_expansion.py"), "Query Expansion Tests")
        elif choice == "6":
            run_pytest(os.path.join(unit_path, "test_table_processor.py"), "Table Processor Tests")
        elif choice == "7":
            run_pytest(unit_path, "All Unit Tests")
        elif choice == "b":
            break
        
        if choice != "b":
            Prompt.ask("\n[dim]Presiona Enter para continuar...[/]")


def submenu_integration_tests():
    """Submenú para pruebas de integración."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner()
        
        console.print("\n[bold cyan]═══ PRUEBAS DE INTEGRACIÓN ═══[/]\n")
        
        table = Table(show_header=False, box=None)
        table.add_row("[bold cyan]1.[/]", "☁️  [bold white]AWS Bedrock Integration[/]")
        table.add_row("[bold cyan]2.[/]", "🔗 [bold white]General Integration Tests[/]")
        table.add_row("[bold cyan]3.[/]", "🔍 [bold white]Retrieve Integration[/]")
        table.add_row("[bold cyan]4.[/]", "📊 [bold white]Table Integration[/] [bold yellow](TASK-015)[/]")
        table.add_row("[bold cyan]5.[/]", "🌐 [bold white]API Endpoints[/] [bold green](E2E)[/]")
        table.add_row("[bold cyan]6.[/]", "🔥 [bold white]TODAS las pruebas de integración[/]")
        table.add_row("[bold cyan]b.[/]", "⬅️  [bold white]Volver al menú principal[/]")
        
        console.print(Panel(table, title="[bold white]Selecciona un módulo[/]", border_style="cyan"))
        
        choice = Prompt.ask("\n[bold yellow]Elección[/]", choices=["1", "2", "3", "4", "5", "6", "b"])
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        integration_path = os.path.join(base_path, "integration")
        api_path = os.path.join(base_path, "api")
        
        if choice == "1":
            run_pytest(os.path.join(integration_path, "test_aws_bedrock.py"), "AWS Bedrock Tests")
        elif choice == "2":
            run_pytest(os.path.join(integration_path, "test_integration.py"), "General Integration Tests")
        elif choice == "3":
            run_pytest(os.path.join(integration_path, "test_retrieve_integration.py"), "Retrieve Integration Tests")
        elif choice == "4":
            run_pytest(os.path.join(integration_path, "test_table_integration.py"), "Table Integration Tests")
        elif choice == "5":
            run_pytest(os.path.join(api_path, "test_api_endpoints.py"), "API Endpoints Tests")
        elif choice == "6":
            run_pytest(integration_path, "All Integration Tests")
        elif choice == "b":
            break
        
        if choice != "b":
            Prompt.ask("\n[dim]Presiona Enter para continuar...[/]")


def main_menu():
    """Menú principal interactivo."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner()
        
        table = Table(show_header=False, box=None)
        table.add_row("[bold cyan]1.[/]", "🧪 [bold white]Pruebas Unitarias[/] (Componentes aislados)")
        table.add_row("[bold cyan]2.[/]", "🔗 [bold white]Pruebas de Integración[/] (Grafo y AWS)")
        table.add_row("[bold cyan]3.[/]", "📊 [bold white]Pruebas de Evaluación[/] (RAGAS y Salud)")
        table.add_row("[bold cyan]4.[/]", "📋 [bold white]Pruebas de Tablas[/] [bold yellow](TASK-015 Completo)[/]")
        table.add_row("[bold cyan]5.[/]", "🔥 [bold white]EJECUTAR TODO EL SUITE[/]")
        table.add_row("[bold cyan]6.[/]", "📂 [bold white]Ver Scripts de Utilidad[/]")
        table.add_row("[bold cyan]q.[/]", "🚪 [bold red]Salir[/]")
        
        console.print(Panel(table, title="[bold white]Selecciona una opción[/]", border_style="cyan"))
        
        choice = Prompt.ask("\n[bold yellow]Elección[/]", choices=["1", "2", "3", "4", "5", "6", "q"])
        
        # Obtener la ruta base (directorio tests/)
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        if choice == "1":
            submenu_unit_tests()
        elif choice == "2":
            submenu_integration_tests()
        elif choice == "3":
            run_pytest(os.path.join(base_path, "evaluation"), "Evaluation Tests")
            Prompt.ask("\n[dim]Presiona Enter para continuar...[/]")
        elif choice == "4":
            # Ejecutar todos los tests de tablas (unitarios + integración)
            console.print("\n[bold blue]🚀 Ejecutando suite completo de TASK-015: Table Optimization[/]\n")
            run_pytest(os.path.join(base_path, "unit", "test_table_processor.py"), "Table Processor Unit Tests")
            console.print("\n")
            run_pytest(os.path.join(base_path, "integration", "test_table_integration.py"), "Table Integration Tests")
            Prompt.ask("\n[dim]Presiona Enter para continuar...[/]")
        elif choice == "5":
            run_pytest(base_path, "Full Test Suite")
            Prompt.ask("\n[dim]Presiona Enter para continuar...[/]")
        elif choice == "6":
            scripts_path = os.path.join(base_path, "scripts")
            scripts = os.listdir(scripts_path)
            console.print(f"\n[bold cyan]Scripts disponibles en {scripts_path}:[/]")
            for s in scripts:
                console.print(f" • {s}")
            Prompt.ask("\n[dim]Presiona Enter para continuar...[/]")
        elif choice == "q":
            console.print("\n[bold gold1]¡Hasta luego, Ronny! Fénix sigue volando.[/]\n")
            break

if __name__ == "__main__":
    main_menu()
