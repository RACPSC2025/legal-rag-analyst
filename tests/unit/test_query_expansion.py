"""
Test rápido de Query Expansion
Ejecutar: python test_query_expansion.py
"""

import sys
from pathlib import Path

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.query_expansion import expand_query

def test_query_expansion():
    """Test básico de expansión de query."""
    print("=" * 80)
    print("TEST: Query Expansion con HyDE + Multi-Query")
    print("=" * 80)
    
    # Query de prueba
    question = "¿Cuáles son los requisitos para obtener una concesión de aguas?"
    
    print(f"\n📝 Query Original:\n{question}\n")
    
    # Expandir query
    print("🔄 Expandiendo query...")
    expanded = expand_query(question, n_queries=3, use_hyde=True)
    
    # Mostrar resultados
    print("\n" + "=" * 80)
    print("RESULTADOS")
    print("=" * 80)
    
    print(f"\n1️⃣ Query Normalizada (para BM25):")
    print(f"   {expanded.normalized}")
    
    print(f"\n2️⃣ Documento Hipotético (HyDE):")
    if expanded.hyde_doc:
        print(f"   {expanded.hyde_doc[:200]}...")
        print(f"   [Total: {len(expanded.hyde_doc)} caracteres]")
    else:
        print("   ⚠️ No se generó documento hipotético")
    
    print(f"\n3️⃣ Variantes de Query (Multi-Query):")
    for i, q in enumerate(expanded.queries, 1):
        print(f"   {i}. {q}")
    
    print(f"\n4️⃣ Todas las Queries (para retrieval):")
    for i, q in enumerate(expanded.all_queries, 1):
        print(f"   {i}. {q[:80]}...")
    
    print("\n" + "=" * 80)
    print("✅ Test completado exitosamente")
    print("=" * 80)

if __name__ == "__main__":
    test_query_expansion()
