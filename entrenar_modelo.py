# entrenar_modelo.py - Script para entrenar el modelo con datos de MongoDB

import sys
sys.path.insert(0, 'src')

from database import DatabaseManager
from ml_model_pacientes import ModeloPredictorEstadoPaciente
import os
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno
env_path = Path(__file__).parent / "src" / ".env"
load_dotenv(dotenv_path=env_path)

# Conectar a BD
print("📡 Conectando a MongoDB...")
db_manager = DatabaseManager()
uri = os.getenv("MONGODB_URI")
if uri:
    db_manager.uri = uri

if db_manager.conectar("modelo_pacientes", "coleccion1"):
    print("✅ Conexión exitosa")
    
    # Crear modelo
    print("\n🤖 Iniciando entrenamiento...")
    modelo = ModeloPredictorEstadoPaciente()
    
    # Pipeline completo (obtener datos, preparar, entrenar, evaluar)
    resultado = modelo.pipeline_completo(db_manager, guardar_modelo=True)
    
    if resultado:
        print("\n✅ ¡Modelo entrenado exitosamente!")
    else:
        print("\n❌ Error en el entrenamiento")
else:
    print("❌ No se pudo conectar a MongoDB")
