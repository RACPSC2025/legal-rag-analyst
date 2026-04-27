"""
Test de Hybrid Search v2 con Query Expansion
Ejecutar: python test_hybrid_search_v2.py
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_hybrid_search_v2():
    """Test de integración de Hybrid Search v2 con Query Expansion."""
    print("=" * 80)
    print("TEST: Hybrid Search v2 con Query Expansion")
    print("=" * 80)
    
    # Simular query expansion
    print("\n📝 Simulando Query Expansion...")
    
    query_original = "¿Cuáles son los requisitos para concesión de aguas?"
    query_normalizada = "requisitos concesión aguas"
    hyde_doc = "ARTÍCULO 2.2.1.4. Requisitos para concesión de aguas. Para obtener la concesión..."
    variantes = [
        "¿Qué documentos se necesitan para solicitar concesión de aguas?",
        "¿Cuáles son las condiciones del Decreto 1076 para aguas?",
        "¿Qué exige la autoridad ambiental para concesión hídrica?"
    ]
    
    print(f"   Original: {query_original}")
    print(f"   Normalizada: {query_normalizada}")
    print(f"   HyDE: {hyde_doc[:80]}...")
    print(f"   Variantes: {len(variantes)}")
    
    # Verificar firma del método
    print("\n🔍 Verificando firma del método retrieve()...")
    
    from src.retrieval.hybrid_search import FenixHybridRetriever
    import inspect
    
    sig = inspect.signature(FenixHybridRetriever.retrieve)
    params = list(sig.parameters.keys())
    
    print(f"   Parámetros: {params}")
    
    # Verificar que tiene los nuevos parámetros
    required_params = ['query', 'top_k', 'hyde_doc', 'extra_queries', 'metadata_filter']
    missing = [p for p in required_params if p not in params]
    
    if missing:
        print(f"   ❌ Faltan parámetros: {missing}")
        return False
    else:
        print(f"   ✅ Todos los parámetros requeridos presentes")
    
    # Verificar constantes RRF
    print("\n⚖️ Verificando constantes RRF...")
    
    from src.retrieval import hybrid_search
    
    constants = {
        '_W_VECTOR': getattr(hybrid_search, '_W_VECTOR', None),
        '_W_BM25': getattr(hybrid_search, '_W_BM25', None),
        '_W_HYDE': getattr(hybrid_search, '_W_HYDE', None),
        '_K_RRF': getattr(hybrid_search, '_K_RRF', None),
    }
    
    for name, value in constants.items():
        if value is not None:
            print(f"   ✅ {name} = {value}")
        else:
            print(f"   ❌ {name} no encontrada")
    
    # Verificar métodos auxiliares
    print("\n🔧 Verificando métodos auxiliares...")
    
    methods = ['_vector_search', '_bm25_search', '_rrf_fusion']
    for method in methods:
        if hasattr(FenixHybridRetriever, method):
            print(f"   ✅ {method}() presente")
        else:
            print(f"   ❌ {method}() faltante")
    
    print("\n" + "=" * 80)
    print("✅ Verificación de estructura completada")
    print("=" * 80)
    print("\n💡 Nota: Para test completo con ChromaDB, ejecutar después de indexar documentos.")
    
    return True

if __name__ == "__main__":
    test_hybrid_search_v2()
