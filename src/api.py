from fastapi import FastAPI, File, UploadFile, HttpException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

from data_loader import load_excel, ensure_columns
from risk_classifier import clasificar_pacientes, preparar_pacientes_para_bd
from database import DatabaseManager
from ml_model_pacientes import ModeloPredictorEstadoPaciente
from ml_pipeline import FEATURE_COLUMNS, TARGET_COLUMN

#Cargar variables de entorno
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# ============================================================================
# CONFIGURACIÓN DE FASTAPI
# ============================================================================

app = FastAPI(title="Asistente Clínico - Predicción de Estado del Paciente",
    description="Sistema de predicción de estado clínico basado en ML",
    version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

db_manager = None
modelo = None

@app.get("/")
async def root():
    return FileResponse("templates/index.html")

@app.post("/entrenar")
async def entrenar_modelo(file: UploadFile = File(...)):
     """
    Endpoint para entrenar el modelo con nuevos datos.
    
    Pasos:
    1. Validar que el archivo sea .xlsx o .csv
    2. Guardar archivo temporalmente
    3. Cargar con pandas
    4. Conectar a MongoDB
    5. Clasificar pacientes (risk_classifier)
    6. Guardar en BD
    7. Entrenar modelo (ModeloPredictorEstadoPaciente)
    8. Guardar modelo
    9. Devolver JSON con resultado
    """
    
    global db_manager, modelo
    
    try:
        
        if not file.filename.endswith(('.xlsx', '.csv', '.xls')):
            raise HttpException(
                status_code = 400,
                detail="Archivo no soportado. Por favor suba un archivo .xlsx, .xls o .csv"
            )
            
        print(f"Archivo recibido: {file.filename}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            contents = await file.read()
            temp_file.write(contents)
            temp_path = temp_file.name
            
        try:
            print(f"Cargando datos desde: {temp_path}")
            df = load_excel(temp_path)
            
            columas_requeridas = FEATURE_COLUMNS + [
                TARGET_COLUMN, "Diagnóstico", "Sexo", "Edad", "Número de Leucocitos al inicio"
            ]
            
            ensure_columns(df, columas_requeridas)
            
            print(f"✅ Excel cargado: {len(df)} registros, {len(df.columns)} columnas")
            
            print("Conectando a MongoDB...")
            if db_manager is None:
                db_manager = DatabaseManager()
                print("Conexión a MongoDB establecida")
                uri = os.getenv("MONGODB_URI")
                
                if uri:
                    db_manager.uri = uri
                    
                if not db_manager.conectar("modelo_pacientes", "coleccion1"):
                    return JSONResponse(
                        status_code=500,
                        content = {
                            "status": "error",
                            "message": "Error al conectar a la base de datos"
                        }
                    )
            
        except Exception as e:
        
    Exception as e:
        print(f"Error al recibir el archivo: {e}")