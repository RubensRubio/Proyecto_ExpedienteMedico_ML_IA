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
from .risk_classifier import clasificar_pacientes, preparar_pacientes_para_bd, clasificar_paciente, procesar_cariotipo, procesar_biologia_molecular, procesar_gate_inmunofenotipo, clasificar_tipo_infiltracion, procesar_marcadores_aberrantes

#Cargar variables de entorno
# Intentar cargar desde .env si existe (desarrollo local)
# Si no existe, usa las variables del sistema (producción en Render)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # En producción, cargar todas las variables de entorno del sistema
    load_dotenv()

# Verificar que MONGODB_URI está configurada
mongodb_uri = os.getenv("MONGODB_URI")
if not mongodb_uri:
    print("⚠️  ADVERTENCIA: MONGODB_URI no está configurada")
    print("   Variables de entorno disponibles:", list(os.environ.keys())[:5], "...")

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
            print(f"🔍 DEBUG - URI desde entorno: {uri[:50]}..." if uri else "❌ URI no encontrada en entorno")
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
    
    global db_manager, modelo
    
    try:
        if db_manager is None:
            db_manager = DatabaseManager()
            uri = os.getenv("MONGODB_URI")
            print(f"🔍 DEBUG crear_paciente - URI: {uri[:50]}..." if uri else "❌ URI no encontrada")
                
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
        
        # Validar y convertir campos requeridos
        try:
            data['Edad'] = float(data.get('Edad', 0))
            data['Número de Leucocitos al inicio'] = float(data.get('Número de Leucocitos al inicio', 0))
            data['Número de blastos'] = float(data.get('Número de blastos', 0))
            data['GATE Inmunofenotipo'] = float(data.get('GATE Inmunofenotipo', 0))
        except (ValueError, TypeError) as e:
            print(f"Error al convertir campos numéricos: {e}")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": f"Error en conversión de datos: {str(e)}"}
            )
        
        # Calcular el riesgo automáticamente
        try:
            edad = data['Edad']
            leucocitos = data['Número de Leucocitos al inicio']
            
            riesgo_edad, riesgo_leucos, riesgo_final = clasificar_paciente(edad, leucocitos)
            data['Riesgo calculado'] = riesgo_final
            
            print(f"Riesgo calculado: Edad({edad}) → {riesgo_edad}, Leucos({leucocitos}) → {riesgo_leucos}, Final: {riesgo_final}")
            
        except Exception as e:
            print(f"Error al calcular riesgo: {e}")
            data['Riesgo calculado'] = "Riesgo estandar"
        
        # Procesar Tipo de leucemia (del campo Sexo si es que existe)
        if 'Tipo leucemia' not in data and 'Sexo' in data:
            data['Tipo leucemia'] = data.get('Sexo', '')
        
        # Procesar Clasificación cariotipo
        cariotipo_valor = data.get('Clasificación cariotipo', '')
        data['Clasificación cariotipo'] = procesar_cariotipo(cariotipo_valor)
        print(f"Cariotipo: '{cariotipo_valor}' → {data['Clasificación cariotipo']}")
        
        # Procesar Biología molecular (puede estar vacía)
        biologia_valor = data.get('Biología molecular', '')
        data['Biología molecular'] = procesar_biologia_molecular(biologia_valor)
        print(f"Biología: '{biologia_valor}' → {data['Biología molecular']}")
        
        # Calcular Tipo de infiltración basado en GATE
        gate_num = data['GATE Inmunofenotipo']
        data['Tipo infiltración'] = clasificar_tipo_infiltracion(gate_num)
        print(f"Infiltración: GATE({gate_num}) → {data['Tipo infiltración']}")
        
        # Procesar Marcadores aberrantes (puede estar vacía)
        marcadores_valor = data.get('Marcadores aberrantes', '')
        data['Resistencia al tratamiento'] = procesar_marcadores_aberrantes(marcadores_valor)
        print(f"Marcadores: '{marcadores_valor}' → Resistencia={data['Resistencia al tratamiento']}")
        
        # Asegurar que no hay valores None o NaN
        for key in data:
            if data[key] is None:
                print(f"Advertencia: Campo '{key}' es None, se asignará valor por defecto")
                if isinstance(key, str):
                    data[key] = ""
                elif isinstance(key, bool):
                    data[key] = False
                elif isinstance(key, (int, float)):
                    data[key] = 0
        
        print(f"\nDatos finales para guardar: {data}\n")
        
        paciente_guardado = db_manager.guardar_paciente(data)
        
        if not paciente_guardado:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Error al guardar el paciente"}
            )
        
        # Entrenar el modelo automáticamente con los nuevos datos
        print("\n" + "="*60)
        modelo_entrenado = await _entrenar_modelo_interno()
        print("="*60 + "\n")
        
        # Generar predicción en lenguaje natural para el nuevo paciente
        respuesta_natural = None
        print(f"\nDebug predicción:")
        print(f"  modelo_entrenado: {modelo_entrenado}")
        print(f"  modelo is not None: {modelo is not None}")
        print(f"  hasattr(modelo, 'modelo'): {hasattr(modelo, 'modelo') if modelo is not None else 'N/A'}")
        print(f"  modelo.modelo is not None: {modelo.modelo is not None if modelo is not None and hasattr(modelo, 'modelo') else 'N/A'}")
        
        if modelo_entrenado and modelo is not None and hasattr(modelo, 'modelo') and modelo.modelo is not None:
            try:
                # Obtener datos para predicción (convertir diccionario a DataFrame)
                datos_prediccion = {k: v for k, v in data.items() if k not in ['_id', 'fecha_registro']}
                
                # Normalizar nombres de campos para que coincidan con los del entrenamiento
                # El modelo fue entrenado con datos de MongoDB que puede tener diferentes nombres
                mapeo_campos = {
                    'Número de Leucocitos al inicio': 'Número de Leucocitos al inicio',
                    'Leucocitos': 'Número de Leucocitos al inicio'
                }
                
                # Renombrar campos si es necesario
                datos_renombrados = {}
                for key, value in datos_prediccion.items():
                    nuevo_key = mapeo_campos.get(key, key)
                    datos_renombrados[nuevo_key] = value
                
                print(f"Datos para predicción: {datos_renombrados}")
                
                df_prediccion = pd.DataFrame([datos_renombrados])
                print(f"Columnas en DataFrame: {df_prediccion.columns.tolist()}")
                print(f"Tipos en DataFrame: {df_prediccion.dtypes}")
                
                # Realizar predicción
                prediccion = modelo.predecir(df_prediccion)
                
                if prediccion is not None:
                    confianza = float(prediccion.get('confianza', 0))
                    clase_predicha = prediccion.get('clase_predicha')
                    probabilidades = prediccion.get('probabilidades', {})
                    
                    # Generar respuesta en lenguaje natural
                    respuesta_natural = generar_respuesta_natural(
                        clase_predicha, 
                        confianza, 
                        probabilidades, 
                        datos_renombrados
                    )
                    
                    print(f"Predicción generada: {clase_predicha} (confianza: {confianza:.2%})")
                else:
                    print("Advertencia: prediccion retornó None")
                
            except Exception as e:
                print(f"Error al generar predicción: {e}")
                import traceback
                traceback.print_exc()
                respuesta_natural = None
        else:
            print(f"No se puede hacer predicción. modelo_entrenado={modelo_entrenado}, modelo={modelo}, tiene método predecir={hasattr(modelo, 'modelo') if modelo else False}")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success", 
                "mensaje": "Paciente guardado, modelo entrenado y predicción generada",
                "riesgo_calculado": data.get('Riesgo calculado'),
                "modelo_entrenado": modelo_entrenado,
                "prediccion_natural": respuesta_natural
            }
        )
        
    except Exception as e:
        print(f"Error al crear paciente: {e}")
        import traceback
        traceback.print_exc()
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
        