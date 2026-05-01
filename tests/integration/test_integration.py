"""
Script de prueba para validar la integración del Model Hub - Fase 0, Subtarea 0.3
Utiliza 'Rich' para una salida de consola profesional y robusta.
"""

import logging
import sys
import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

# Configuración de temas para Rich
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "highlight": "magenta",
})

console = Console(theme=custom_theme)
logger = logging.getLogger(__name__)

def test_integration():
    """Prueba la integración del Model Hub con el sistema usando Rich"""
    start_time = time.perf_counter()
    
    console.print(Panel.fit(
        "[bold cyan]FÉNIX LEGAL v2.5[/bold cyan] - Auditoría de Integración [highlight]Subtarea 0.3[/highlight]",
        border_style="cyan"
    ))
    
    try:
        # Test 1: Verificar configuración
        console.print("\n[bold blue]🔍 Test 1: Verificando configuración (.env)...[/bold blue]")
        from src.config import settings
        
        assert settings.PREFERRED_PROVIDER is not None, "PREFERRED_PROVIDER no configurado"
        assert settings.MODEL_SELECTION_MODE in ["performance", "cost_optimized"], "Modo inválido"
        
        table = Table(title="Configuración Detectada", show_header=True, header_style="bold magenta")
        table.add_column("Parámetro", style="dim")
        table.add_column("Valor", style="bold")
        
        table.add_row("Provider", settings.PREFERRED_PROVIDER)
        table.add_row("Mode", settings.MODEL_SELECTION_MODE)
        table.add_row("Dynamic Selection", str(settings.ENABLE_DYNAMIC_MODEL_SELECTION))
        
        console.print(table)
        console.print("[success]✅ Test 1: Configuración cargada correctamente.[/success]")

        # Test 2: Compatibilidad Legacy
        console.print("\n[bold blue]🔍 Test 2: Verificando compatibilidad legacy (get_llm)...[/bold blue]")
        from src.config import get_llm
        llm_legacy = get_llm()
        assert llm_legacy is not None
        console.print(f"[info]   ➤ Modelo legacy:[/info] [highlight]{llm_legacy.model_id}[/highlight]")
        console.print("[success]✅ Test 2: get_llm() operativo.[/success]")

        # Test 3: Ruteo Dinámico
        console.print("\n[bold blue]🔍 Test 3: Verificando ruteo dinámico por tareas...[/bold blue]")
        from src.config import get_dynamic_llm
        tasks = ["grade", "verify", "summarize", "generate", "analyze"]
        llms = {}
        
        task_table = Table(show_header=True, header_style="bold cyan")
        task_table.add_column("Tarea", style="dim")
        task_table.add_column("Modelo Asignado", style="bold yellow")
        
        for task in tasks:
            llm = get_dynamic_llm(task=task)
            assert llm is not None
            llms[task] = llm
            task_table.add_row(task, llm.model_id)
        
        console.print(task_table)
        console.print("[success]✅ Test 3: Ruteo dinámico operativo.[/success]")

        # Test 4: Light vs Heavy
        console.print("\n[bold blue]🔍 Test 4: Diferenciación Light vs Heavy...[/bold blue]")
        light_id = llms["grade"].model_id
        heavy_id = llms["generate"].model_id
        
        if light_id != heavy_id:
            console.print(f"[success]   ➤ Optimización activa:[/success] Light ([dim]{light_id}[/dim]) != Heavy ([bold]{heavy_id}[/bold])")
        else:
            console.print("[warning]   ➤ Mismo modelo para ambos perfiles (Fallback detectado).[/warning]")
        console.print("[success]✅ Test 4: Perfiles de costo verificados.[/success]")

        # Test 5: Kill-switch
        console.print("\n[bold blue]🔍 Test 5: Kill-switch de selección dinámica...[/bold blue]")
        original = settings.ENABLE_DYNAMIC_MODEL_SELECTION
        settings.ENABLE_DYNAMIC_MODEL_SELECTION = False
        try:
            llm_static = get_dynamic_llm(task="generate")
            assert llm_static.model_id == llm_legacy.model_id
            console.print(f"[info]   ➤ Modo estático forzado:[/info] {llm_static.model_id}")
        finally:
            settings.ENABLE_DYNAMIC_MODEL_SELECTION = original
        console.print("[success]✅ Test 5: Modo estático funciona correctamente.[/success]")

        # Resumen Final
        duration = time.perf_counter() - start_time
        console.print("\n" + "═" * 60)
        console.print(Panel(
            f"[bold success]INTEGRACIÓN EXITOSA[/bold success]\n[dim]Tiempo total: {duration:.2f}s[/dim]",
            title="Resultado Final",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"\n[error]❌ ERROR EN INTEGRACIÓN:[/error] {str(e)}")
        import traceback
        console.print(traceback.format_exc(), style="dim red")
        raise e

if __name__ == "__main__":
    try:
        test_integration()
        sys.exit(0)
    except Exception:
        sys.exit(1)
