import os
import sys
from pathlib import Path
import boto3
from dotenv import load_dotenv

# Agregar la raíz del proyecto al sys.path para importar src
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Cargar el .env de la raíz
load_dotenv(PROJECT_ROOT / ".env")

def test_aws_connection():
    print("=== Diagnóstico de Conexión AWS Bedrock ===")
    
    # 1. Verificar variables de entorno
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "").strip("\"'")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip("\"'")
    region = os.getenv("AWS_REGION", "us-east-2").strip("\"'")
    
    print(f"Ruta Proyecto: {PROJECT_ROOT}")
    print(f"AWS_ACCESS_KEY_ID: {access_key[:4]}...{access_key[-4:] if len(access_key)>4 else ''}")
    print(f"AWS_SECRET_ACCESS_KEY: {secret_key[:4]}...{secret_key[-4:] if len(secret_key)>4 else ''}")
    print(f"AWS_REGION: {region}")
    
    if not access_key or not secret_key:
        print("❌ ERROR: Faltan credenciales en el archivo .env")
        return

    # 2. Intentar crear sesión y cliente de Bedrock
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        # Cliente de control (para listar modelos)
        bedrock = session.client("bedrock")
        # Cliente de ejecución (para invocar modelos)
        runtime = session.client("bedrock-runtime")
        
        print("✅ Sesión de boto3 creada correctamente.")
        
        # 3. Listar modelos disponibles (Prueba de permisos base)
        print("\nVerificando permisos para listar modelos...")
        response = bedrock.list_foundation_models(
            byOutputModality='TEXT',
            byInferenceType='ON_DEMAND'
        )
        print(f"✅ Conexión exitosa. Se encontraron {len(response.get('modelSummaries', []))} modelos disponibles.")
        
        # 4. Probar un modelo específico (Amazon Nova Lite)
        model_id = os.getenv("AWS_MODEL_SIMPLE_TEXT", "us.amazon.nova-lite-v1:0").strip("\"'")
        print(f"\nProbando invocación del modelo: {model_id}...")
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": "Hola, responde con la palabra 'CONECTADO'."}]
                }
            ],
            "inferenceConfig": {
                "max_new_tokens": 10,
                "temperature": 0
            }
        }
        
        import json
        response = runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(payload)
        )
        
        result = json.loads(response.get("body").read())
        # Para Nova, la respuesta está en output.message.content[0].text
        answer = result.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
        print(f"✅ Respuesta del modelo: {answer}")
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {str(e)}")
        if "UnrecognizedClientException" in str(e):
            print("   -> La Access Key ID es inválida.")
        elif "SignatureDoesNotMatch" in str(e):
            print("   -> La Secret Access Key es incorrecta.")
        elif "AccessDeniedException" in str(e):
            print("   -> El usuario IAM no tiene permisos para Bedrock o el modelo no está habilitado en la región.")
        elif "EndpointConnectionError" in str(e):
            print(f"   -> No se pudo conectar al endpoint en {region}. Verifica la región o tu internet.")

if __name__ == "__main__":
    test_aws_connection()
