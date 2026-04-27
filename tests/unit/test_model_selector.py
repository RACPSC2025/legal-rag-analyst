"""
Script de prueba para validar el Model Selector - Fase 0, Subtarea 0.2
────────────────────────────────────────────────────────────
Valida la selección dinámica de modelos por tarea (light vs heavy).
"""

import logging
import sys
import os
from pathlib import Path

# Configuración de path para encontrar 'src'
root_path = str(Path(__file__).parent.parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from src.model_hub.selector import get_model_selector

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_selector():
    """Prueba el selector de modelos"""
    try:
        logger.info("=" * 60)
        logger.info("🧪 INICIANDO PRUEBA DE MODEL SELECTOR - SUBTAREA 0.2")
        logger.info("=" * 60)
        
        selector = get_model_selector()
        
        assert selector is not None, "El selector no debe ser None"
        logger.info("✅ Test 1: Selector Singleton inicializado correctamente")
        
        # Test: Selección para tarea ligera (grading)
        logger.info("\n📝 Test: Selección para tarea 'grade' (light)")
        model_light = selector.select_model_id(task="grade")
        assert model_light is not None, "Debe retornar un modelo"
        logger.info(f"   Modelo seleccionado: {model_light}")
        
        # Test: Selección para tarea pesada (generate)
        logger.info("\n📝 Test: Selección para tarea 'generate' (heavy)")
        model_heavy = selector.select_model_id(task="generate")
        assert model_heavy is not None, "Debe retornar un modelo"
        logger.info(f"   Modelo seleccionado: {model_heavy}")
        
        # Test: Diferentes tareas
        logger.info("\n📝 Test: Verificación de mapeo de tareas")
        tasks = ["grade", "verify", "summarize", "generate", "analyze"]
        for task in tasks:
            model = selector.select_model_id(task=task)
            logger.info(f"   {task:12} → {model}")
            assert model is not None
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ TODOS LOS TESTS DE SELECTOR PASARON")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error durante las pruebas: {e}")
        logger.exception("Detalles del error:")
        raise

if __name__ == "__main__":
    test_selector()
