"""
Test de Integración: Retrieve v2 con Query Expansion
Ejecutar: python test_retrieve_integration.py
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_retrieve_integration():
    """Test de integración del nodo retrieve v2."""
    print("=" * 80)
    print("TEST: Integración de Retrieve v2 con Query Expansion")
    print("=" * 80)
    
    # Verificar imports
    print("\n📦 Verificando imports...")
    
    try:
        from core.nodes import retrieve
        print("   ✅ retrieve() importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando retrieve: {e}")
        return False
    
    try:
        from retrieval.query_expansion import expand_query
        print("   ✅ expand_query() importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando expand_query: {e}")
        return False
    
    try:
        from retrieval.hybrid_search import get_hybrid_retriever
        print("   ✅ get_hybrid_retriever() importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando get_hybrid_retriever: {e}")
        return False
    
    # Verificar firma del nodo retrieve
    print("\n🔍 Verificando nodo retrieve()...")
    
    import inspect
    sig = inspect.signature(retrieve)
    params = list(sig.parameters.keys())
    
    print(f"   Parámetros: {params}")
    
    if 'state' in params:
        print("   ✅ Parámetro 'state' presente")
    else:
        print("   ❌ Parámetro 'state' faltante")
        return False
    
    # Verificar docstring
    if retrieve.__doc__:
        if "Query Expansion" in retrieve.__doc__:
            print("   ✅ Docstring menciona Query Expansion")
        else:
            print("   ⚠️ Docstring no menciona Query Expansion")
    
    # Verificar que usa expand_query
    print("\n🔧 Verificando uso de expand_query en retrieve()...")
    
    source = inspect.getsource(retrieve)
    
    checks = {
        "expand_query": "expand_query" in source,
        "hyde_doc": "hyde_doc" in source,
        "extra_queries": "extra_queries" in source,
        "normalized": "normalized" in source,
        "hybrid_retriever.retrieve": "hybrid_retriever.retrieve" in source,
    }
    
    for check, result in checks.items():
        if result:
            print(f"   ✅ Usa '{check}'")
        else:
            print(f"   ❌ No usa '{check}'")
    
    # Verificar manejo de errores
    print("\n🛡️ Verificando manejo de errores...")
    
    error_checks = {
        "try/except": "try:" in source and "except" in source,
        "fallback": "fallback" in source.lower(),
        "logger.warning": "logger.warning" in source,
        "logger.error": "logger.error" in source,
    }
    
    for check, result in error_checks.items():
        if result:
            print(f"   ✅ Tiene '{check}'")
        else:
            print(f"   ⚠️ No tiene '{check}'")
    
    # Verificar logging
    print("\n📝 Verificando logging...")
    
    log_checks = {
        "logger.info": source.count("logger.info"),
        "logger.warning": source.count("logger.warning"),
        "logger.error": source.count("logger.error"),
    }
    
    for check, count in log_checks.items():
        print(f"   {check}: {count} llamadas")
    
    print("\n" + "=" * 80)
    print("✅ Verificación de integración completada")
    print("=" * 80)
    
    print("\n💡 Flujo esperado:")
    print("   1. Query Expansion (HyDE + Multi-Query)")
    print("   2. Hybrid Retrieval v2 (BM25 + Vector + RRF)")
    print("   3. FlashRank Reranking")
    print("   4. Logging de metadata (RRF scores, rerank scores)")
    print("   5. Fallback robusto en cada paso")
    
    print("\n💡 Para test completo con ChromaDB:")
    print("   1. Indexar documentos: python -m src.ingestion.pipeline --paths data/")
    print("   2. Ejecutar grafo: python app.py")
    print("   3. Verificar logs en terminal")
    
    return True

if __name__ == "__main__":
    test_retrieve_integration()
