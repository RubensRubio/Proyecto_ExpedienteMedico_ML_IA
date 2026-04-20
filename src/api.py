from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

from .data_loader import load_excel, ensure_columns
from .database import DatabaseManager
from .ml_model_pacientes import ModeloPredictorEstadoPaciente
from .language_generator import generar_respuesta_natural
from .risk_classifier import clasificar_pacientes, preparar_pacientes_para_bd

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

@app.post("/api/status")
async def status():
    """Endpoint temporal para verificar que la API funciona"""
    return JSONResponse(
        status_code=200,
        content={"status": "API funcionando", "mensaje": "Listos para Fase 2"}
    )

# ============================================================================
# FUNCIÓN AUXILIAR: ENTRENAR MODELO DE MANERA INTERNA
# ============================================================================
async def _entrenar_modelo_interno():
    """Función auxiliar para entrenar el modelo sin retornar respuesta HTTP"""
    global db_manager, modelo
    
    try:
        print("Iniciando entrenamiento automático del modelo...")
        
        if db_manager is None:
            db_manager = DatabaseManager()
            uri = os.getenv("MONGODB_URI")
            if uri:
                db_manager.uri = uri
            if not db_manager.conectar("modelo_pacientes", "coleccion1"):
                print("Error: No se pudo conectar a la base de datos para entrenar")
                return False
        
        df = db_manager.obtener_datos_pacientes()
        
        if df.empty or len(df) < 10:
            print(f"Advertencia: No hay suficientes datos ({len(df)} registros). Se requieren al menos 10.")
            return False
        
        modelo = ModeloPredictorEstadoPaciente()
        resultado = modelo.pipeline_completo(db_manager, guardar_modelo=True)
        
        if resultado:
            print("✓ Modelo entrenado exitosamente")
            return True
        else:
            print("Error: Fallo el entrenamiento del modelo")
            return False
            
    except Exception as e:
        print(f"Error al entrenar el modelo internamente: {e}")
        return False

# ============================================================================
# ENDPOINTS PARA FASE 1 - 4 OPERACIONES PRINCIPALES
# ============================================================================

# ENDPOINT 1: CARGAR ARCHIVO EXCEL
@app.post("/api/cargar_excel")
async def cargar_excel(file: UploadFile = File(...)):
    
    global db_manager
    
    try:
        
        if not file.filename.endswith(('.xlsx', '.csv', '.xls')):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Archivo no soportado. Por favor suba un archivo .xlsx, .xls o .csv"}
            )
            
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            contents = await file.read()
            temp_file.write(contents)
            temp_path = temp_file.name
            
        try:
            print(f"Cargando datos desde: {file.filename}")
            df = load_excel(temp_path)
            
            if db_manager is None:
                db_manager = DatabaseManager()
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
                    
            # registros = df.to_dict(orient="records")
            # for registro in registros:
            #     if '_id' in registro:
            #         del registro['_id']
                    
            print("Clasificando pacienetes")
            df_clasificado = clasificar_pacientes(df)
            
            print("Guardando pacientes en la base de datos...")
            pacientes = preparar_pacientes_para_bd(df_clasificado)
            
            cantidad = db_manager.guardar_pacientes_batch(pacientes=pacientes)
            
            # Entrenar el modelo automáticamente con los nuevos datos
            print("\n" + "="*60)
            modelo_entrenado = await _entrenar_modelo_interno()
            print("="*60 + "\n")
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": f"{cantidad} registros guardados y modelo entrenado automáticamente",
                    "cantidad_registros": cantidad,
                    "modelo_entrenado": modelo_entrenado
                }
            )
            
        finally:
            os.remove(temp_path)
    
    except Exception as e:
        print(f"Error al cargar el archivo: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error al cargar el archivo: {str(e)}"}
        )
        
@app.post("/api/entrenar_modelo")
async def entrenar_modelo():
    
    global db_manager, modelo
    
    try:
        resultado = await _entrenar_modelo_interno()
        
        if not resultado:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "No hay suficientes datos para entrenar el modelo. Se requieren al menos 10 registros."}
            )
        
        # Obtener métricas del modelo entrenado
        ultima_evaluacion = modelo.historico['evaluaciones'][-1] if modelo and modelo.historico and modelo.historico['evaluaciones'] else {}
        df = db_manager.obtener_datos_pacientes() if db_manager else None
        
        return JSONResponse(
            status_code=200,
            content= {
                "status": "success",
                "message": "Modelo entrenado exitosamente",
                "metricas" :{
                    "accuracy" : f"{ultima_evaluacion.get('accuracy', 0):.2%}",
                    "total_registros" : len(df) if df is not None else 0
                }
            }       
        )
    except Exception as e:
        print(f"Error al entrenar el modelo: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error al entrenar el modelo: {str(e)}"}
        )
        
@app.post("/api/paciente/nuevo")
async def crear_paciente(data : dict):
    
    global db_manager
    
    try:
        if db_manager is None:
            db_manager = DatabaseManager()
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
                
        paciente_guardado = db_manager.guardar_paciente(data)
        
        if paciente_guardado:
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "Paciente guardado exitosamente"}
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Error al guardar el paciente"}
            )
        
    except Exception as e:
        print(f"Error al crear paciente: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error al crear paciente: {str(e)}"}
        )
        
@app.post("/api/prediccion")
async def realizar_prediccion(data : dict):
    
    global modelo
    
    try:
        
        if modelo is None or modelo.modelo is None:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "El modelo no está entrenado. Por favor entrena el modelo antes de realizar predicciones."}
            )
            
        df_paciente = pd.DataFrame([data])
        
        resultado = modelo.predecir(df_paciente)
        
        if resultado is None:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Error al realizar la predicción"}
            )
            
        respuesta_natural = generar_respuesta_natural(
            prediccion=resultado['estado_predicho'],
            confianza=resultado['confianza'],
            probabilidades=resultado['probabilidades'],
            datos_paciente=df_paciente.to_dict('records')[0]
        )
            
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Predicción realizada exitosamente",
                "prediccion": resultado['estado_predicho'],
                "confianza" : f"{resultado['confianza']:.2%}",
                "probabilidades": {
                    estado : f"{prob:.2%}" 
                    for estado, prob in resultado['probabilidades'].items()
                },
                "respuesta_natural": respuesta_natural
            }
        )
    
    except Exception as e:
        print(f"Error al realizar la predicción: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error al realizar la predicción: {str(e)}"}
        )
        