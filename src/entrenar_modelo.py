import sys
sys.path.insert(0, 'src')

from .database import DatabaseManager
from .ml_model_pacientes import ModeloPredictorEstadoPaciente
import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent / "src" / ".env"
load_dotenv(dotenv_path=env_path)

print("Conectando a la base de datos...")
db_manager = DatabaseManager()
uri = os.getenv("MONGODB_URI")

if uri:
    db_manager.uri = uri
    
if db_manager.conectar("modelo_pacientes", "coleccion1"):
    print("Conexión exitosa")
    
    print("Entrenando el modelo...")
    modelo = ModeloPredictorEstadoPaciente()
    
    resultado = modelo.pipeline_completo(db_manager, guardar_modelo=True)
    
    if resultado:
        print("Modelo entrenado y guardado exitosamente.")
    else:
        print("Error al entrenar o guardar el modelo.")
else:
    print("Error al conectar a la base de datos.")