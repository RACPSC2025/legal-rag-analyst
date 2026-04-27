"""
Script de prueba para validar el Model Hub - Fase 0, Subtarea 0.1
────────────────────────────────────────────────────────────
Valida la conexión con Bedrock y la generación del catálogo de modelos.
"""

import logging
import sys
import os
from pathlib import Path

# Configuración de path para encontrar 'src'
root_path = str(Path(__file__).parent.parent.parent)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from src.model_hub.registry import initialize_model_catalog, CATALOG_PATH, load_catalog

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_registry():
    """Prueba el registro de modelos de Bedrock"""
    try:
        logger.info("=" * 60)
        logger.info("🧪 INICIANDO PRUEBA DE MODEL HUB - SUBTAREA 0.1")
        logger.info("=" * 60)
        
        # Test 1: Generar catálogo
        logger.info("\n📝 Test 1: Generando catálogo de modelos...")
        catalog = initialize_model_catalog(force_refresh=True)
        
        # Validaciones
        assert catalog is not None, "El catálogo no debe ser None"
        assert "models" in catalog, "El catálogo debe tener la clave 'models'"
        assert len(catalog["models"]) > 0, "Debe haber al menos un modelo"
        
        logger.info(f"✅ Test 1 PASADO: {len(catalog['models'])} modelos encontrados")
        
        # Test 2: Verificar archivo JSON
        logger.info("\n📝 Test 2: Verificando persistencia del catálogo...")
        assert CATALOG_PATH.exists(), f"El archivo {CATALOG_PATH} debe existir"
        logger.info(f"✅ Test 2 PASADO: Archivo generado en {CATALOG_PATH}")
        
        # Test 3: Cargar desde disco
        logger.info("\n📝 Test 3: Cargando catálogo desde disco...")
        loaded_catalog = load_catalog()
        assert loaded_catalog is not None, "El catálogo cargado no debe ser None"
        assert len(loaded_catalog["models"]) > 0, "Debe tener modelos cargados"
        
        logger.info(f"✅ Test 3 PASADO: Catálogo cargado correctamente")
        
        # Test 4: Resumen
        providers = {}
        for model in catalog["models"]:
            provider = model["provider"]
            providers[provider] = providers.get(provider, 0) + 1
        
        logger.info("\n📋 MODELOS POR PROVEEDOR:")
        for provider, count in sorted(providers.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   {provider}: {count} modelos")
            
        logger.info("\n" + "=" * 60)
        logger.info("✅ TODOS LOS TESTS DE REGISTRY PASARON")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error durante las pruebas: {e}")
        logger.exception("Detalles del error:")
        raise

if __name__ == "__main__":
    test_registry()
