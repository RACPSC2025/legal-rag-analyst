import sys
import os

# Añadir el directorio raíz al path
sys.path.append(os.getcwd())

from src.model_hub import initialize_model_catalog, get_llm_for_task

try:
    print("🚀 Inicializando catálogo...")
    catalog = initialize_model_catalog(force_refresh=False)
    print(f"✅ Catálogo cargado con {len(catalog.get('models', []))} modelos.")

    print("\n🔍 Probando selección de modelo para 'grade'...")
    llm_grade = get_llm_for_task("grade")
    print(f"✅ Modelo para 'grade': {llm_grade.model_id}")

    print("\n🔍 Probando selección de modelo para 'generate'...")
    llm_generate = get_llm_for_task("generate")
    print(f"✅ Modelo para 'generate': {llm_generate.model_id}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
