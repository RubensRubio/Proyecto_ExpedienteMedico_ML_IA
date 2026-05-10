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
        
        # Validar que la edad esté en rango permitido (0-18 años)
        edad = data['Edad']
        if edad < 0 or edad > 18:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Error: La edad debe estar entre 0 y 18 años"}
            )
        
        # Validar que el campo "Inmunofenotipo marcadores" no esté vacío
        inmunofenotipo_marcadores = data.get('Inmunofenotipo marcadores', '').strip()
        if not inmunofenotipo_marcadores:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Error: El campo 'Inmunofenotipo marcadores' es obligatorio"}
            )
        
        # Validar que no exceda los 500 caracteres
        if len(inmunofenotipo_marcadores) > 500:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Error: El campo 'Inmunofenotipo marcadores' no puede exceder 500 caracteres"}
            )
        
        # Calcular el riesgo automáticamente
        try:
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
        
        # Procesar campos opcionales que vienen del chat
        # Convertir "No tengo" y "No aplica" a cadenas vacías
        optional_fields = ['Clasificación cariotipo', 'Biología molecular', 'Marcadores aberrantes']
        for field in optional_fields:
            if field in data:
                value_str = str(data[field]).lower().strip()
                if 'no tengo' in value_str or 'no aplica' in value_str:
                    data[field] = ''
                    print(f"✅ Campo '{field}' convertido a vacío (era '{data[field]}')")
        
        # Asegurar que tiene "Estado del paciente" con valor por defecto
        if "Estado del paciente" not in data or data["Estado del paciente"] is None:
            data["Estado del paciente"] = "Tratamiento"  # Valor por defecto
            print(f"✅ Estado del paciente establecido a 'Tratamiento'")
        
        paciente_guardado = db_manager.guardar_paciente(data)
        
        if not paciente_guardado:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Error al guardar el paciente"}
            )
        
        print(f"✅ Paciente guardado con ID: {paciente_guardado}")
        
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
                    criterio_clinico = prediccion.get('criterio_clinico', False)
                    razon_clinica = prediccion.get('razon', '')
                    
                    # Generar respuesta en lenguaje natural
                    respuesta_natural = generar_respuesta_natural(
                        clase_predicha, 
                        confianza, 
                        probabilidades, 
                        datos_renombrados
                    )
                    
                    # Si se activó criterio clínico, agregar nota a la respuesta
                    if criterio_clinico and razon_clinica:
                        respuesta_natural = f"🏥 **CRITERIO CLÍNICO:** {razon_clinica}\n\n{respuesta_natural}"
                    
                    print(f"Predicción generada: {clase_predicha} (confianza: {confianza:.2%})")
                    if criterio_clinico:
                        print(f"   → Activado por criterio clínico: {razon_clinica}")
                else:
                    print("Advertencia: prediccion retornó None")
                
            except Exception as e:
                print(f"Error al generar predicción: {e}")
                import traceback
                traceback.print_exc()
                respuesta_natural = None
        else:
            print(f"No se puede hacer predicción. modelo_entrenado={modelo_entrenado}, modelo={modelo}, tiene método predecir={hasattr(modelo, 'modelo') if modelo else False}")
        
        # Guardar respuesta natural en colección separada
        if respuesta_natural and paciente_guardado:
            if db_manager.guardar_respuesta_natural(paciente_guardado, respuesta_natural):
                print(f"✅ Respuesta natural guardada para paciente {paciente_guardado}")
            else:
                print(f"⚠️  Error al guardar respuesta natural para paciente {paciente_guardado}")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success", 
                "mensaje": "Paciente guardado, modelo entrenado y predicción generada",
                "paciente_id": str(paciente_guardado),
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

# ============================================================================
# ENDPOINT 5: OBTENER LISTA DE PACIENTES
# ============================================================================

@app.get("/api/pacientes")
async def obtener_pacientes(filtro: str = ""):
    """Obtener lista de todos los pacientes registrados con filtro opcional"""
    
    global db_manager
    
    try:
        if db_manager is None:
            print("🔍 DEBUG: db_manager es None, inicializando...")
            db_manager = DatabaseManager()
            uri = os.getenv("MONGODB_URI")
            
            print(f"📍 MONGODB_URI disponible: {'Sí' if uri else 'No'}")
            if uri:
                print(f"   URI preview: {uri[:80]}...")
                db_manager.uri = uri
            else:
                print("❌ MONGODB_URI no configurada en variables de entorno")
            
            conexion_exitosa = db_manager.conectar("modelo_pacientes", "coleccion1")
            print(f"📊 Resultado de conexión: {conexion_exitosa}")
            print(f"   db_manager.connected: {db_manager.connected}")
            print(f"   db_manager.collection: {db_manager.collection}")
            
            if not conexion_exitosa or db_manager.collection is None:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "error",
                        "message": "Error al conectar a la base de datos MongoDB",
                        "details": "La conexión a MongoDB falló. Verifica que MONGODB_URI esté configurado correctamente en Render."
                    }
                )
        
        # Validar que collection está disponible
        if db_manager.collection is None:
            print("❌ ERROR: db_manager.collection es None")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "message": "La colección no está disponible",
                    "details": "db_manager.collection es None - conexión no inicializada"
                }
            )
        
        # Crear filtro de búsqueda si existe
        query = {}
        if filtro.strip():
            # Buscar en el ID (ObjectId convertido a string)
            from bson import ObjectId
            try:
                query["_id"] = ObjectId(filtro.strip())
            except:
                # Si no es un ObjectId válido, buscar en string
                query["_id"] = ObjectId.from_string(filtro.strip()) if len(filtro.strip()) == 24 else None
        
        # Obtener todos los documentos ordenados por fecha descendente
        if query and query.get("_id"):
            pacientes_cursor = db_manager.collection.find({"_id": query["_id"]}).sort("fecha_registro", -1)
        else:
            pacientes_cursor = db_manager.collection.find().sort("fecha_registro", -1)
        
        pacientes = []
        for paciente in pacientes_cursor:
            pacientes.append({
                "id": str(paciente.get("_id", "")),
                "tipo_leucemia": paciente.get("Tipo leucemia", "N/A"),
                "estado": paciente.get("Estado del paciente", "Desconocido"),
                "riesgo_calculado": paciente.get("Riesgo calculado", "-"),
                "estatus_tratamiento": paciente.get("estatus_tratamiento"),
                "fecha_tratamiento": paciente.get("fecha_tratamiento").isoformat() if paciente.get("fecha_tratamiento") else None,
                "fecha_registro": paciente.get("fecha_registro").isoformat() if paciente.get("fecha_registro") else ""
            })
        
        print(f"✅ Pacientes encontrados: {len(pacientes)}")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "total": len(pacientes),
                "pacientes": pacientes
            }
        )
        
    except Exception as e:
        print(f"❌ Error al obtener pacientes: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error al obtener pacientes: {str(e)}"}
        )


# ============================================================================
# ENDPOINT: OBTENER RESPUESTA NATURAL (DIAGNÓSTICO) DEL PACIENTE
@app.get("/api/paciente/{paciente_id}/respuesta-natural")
async def obtener_respuesta_natural(paciente_id: str):
    """Obtener la respuesta natural (diagnóstico) generado para un paciente"""
    
    try:
        from bson import ObjectId
        
        if db_manager is None or not db_manager.connected:
            return JSONResponse(status_code=503, content={"status": "error", "message": "BD no conectada"})
        
        # Obtener documento del paciente
        try:
            oid = ObjectId(paciente_id)
        except:
            oid = ObjectId.from_string(paciente_id) if len(paciente_id) == 24 else None
        
        if not oid:
            return JSONResponse(status_code=400, content={"status": "error", "message": "ID inválido"})
        
        paciente = db_manager.collection.find_one({"_id": oid})
        
        if not paciente:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Paciente no encontrado"})
        
        # Primero intentar obtener de prediccion_natural
        respuesta_natural = paciente.get("prediccion_natural", None)
        
        # Si no hay prediccion_natural, buscar en la colección respuestas_naturales
        if not respuesta_natural or respuesta_natural == "No disponible":
            db = db_manager.db
            
            # Intentar buscar por ObjectId primero, luego por string
            respuesta_doc = db.respuestas_naturales.find_one(
                {"paciente_id": oid},
                {"respuesta": 1, "_id": 0}
            )
            
            # Si no lo encuentra por ObjectId, intentar por string
            if not respuesta_doc:
                respuesta_doc = db.respuestas_naturales.find_one(
                    {"paciente_id": paciente_id},
                    {"respuesta": 1, "_id": 0}
                )
            
            if respuesta_doc and respuesta_doc.get("respuesta"):
                respuesta_natural = respuesta_doc.get("respuesta")
        
        riesgo = paciente.get("Riesgo calculado", "-")
        estado = paciente.get("Estado del paciente", "Desconocido")
        
        return JSONResponse(status_code=200, content={
            "status": "success",
            "paciente_id": paciente_id,
            "respuesta_natural": respuesta_natural if respuesta_natural else "No disponible",
            "riesgo_calculado": riesgo,
            "estado": estado
        })
        
    except Exception as e:
        print(f"❌ Error al obtener respuesta natural: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ============================================================================
# ENDPOINT: OBTENER PLANES DE TRATAMIENTO DEL PACIENTE
@app.get("/api/paciente/{paciente_id}/planes-tratamiento")
async def obtener_planes_tratamiento(paciente_id: str):
    """Obtener protocolo y fase de los planes de tratamiento del paciente"""
    
    try:
        from bson import ObjectId
        
        if db_manager is None or not db_manager.connected:
            return JSONResponse(status_code=503, content={"status": "error", "message": "BD no conectada"})
        
        # Convertir ID
        try:
            oid = ObjectId(paciente_id)
        except:
            oid = ObjectId.from_string(paciente_id) if len(paciente_id) == 24 else None
        
        if not oid:
            return JSONResponse(status_code=400, content={"status": "error", "message": "ID inválido"})
        
        # Obtener planes de tratamiento desde la colección planes_tratamiento
        db = db_manager.db
        
        # Buscar documentos con el ID del paciente
        planes = list(db.planes_tratamiento.find(
            {"paciente_id": paciente_id},
            {"protocolo": 1, "fase": 1, "_id": 0}
        ).limit(1))
        
        if not planes:
            # Intentar con ObjectId si el primer intento no funciona
            planes = list(db.planes_tratamiento.find(
                {"paciente_id": oid},
                {"protocolo": 1, "fase": 1, "_id": 0}
            ).limit(1))
        
        if planes:
            plan = planes[0]
            protocolo = plan.get("protocolo", "No especificado")
            fase = plan.get("fase", "No especificada")
            return JSONResponse(status_code=200, content={
                "status": "success",
                "protocolo": protocolo,
                "fase": fase
            })
        else:
            return JSONResponse(status_code=200, content={
                "status": "success",
                "protocolo": "No disponible",
                "fase": "No disponible"
            })
        
    except Exception as e:
        print(f"❌ Error al obtener planes de tratamiento: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ============================================================================
# ENDPOINT: GUARDAR OTRO DIAGNÓSTICO
@app.post("/api/paciente/{paciente_id}/otro-diagnostico")
async def guardar_otro_diagnostico(paciente_id: str, data: dict):
    """Guardar otro diagnóstico del paciente y cambiar su estado"""
    
    try:
        from bson import ObjectId
        from datetime import datetime
        
        if db_manager is None or not db_manager.connected:
            return JSONResponse(status_code=503, content={"status": "error", "message": "BD no conectada"})
        
        # Convertir ID
        try:
            oid = ObjectId(paciente_id)
        except:
            return JSONResponse(status_code=400, content={"status": "error", "message": "ID inválido"})
        
        otro_diagnostico = data.get("diagnostico", "").strip()
        if not otro_diagnostico:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Diagnóstico vacío"})
        
        # Actualizar documento
        resultado = db_manager.collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "Estado del paciente": "Otro diagnóstico",
                    "otro_diagnostico": otro_diagnostico,
                    "fecha_otro_diagnostico": datetime.now()
                }
            }
        )
        
        if resultado.matched_count == 0:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Paciente no encontrado"})
        
        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": "Otro diagnóstico guardado exitosamente",
            "paciente_id": paciente_id
        })
        
    except Exception as e:
        print(f"❌ Error al guardar otro diagnóstico: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ============================================================================
# ENDPOINT: GUARDAR DEFUNCIÓN
@app.post("/api/paciente/{paciente_id}/defuncion")
async def guardar_defuncion(paciente_id: str, data: dict):
    """Registrar la defunción de un paciente"""
    
    try:
        from bson import ObjectId
        from datetime import datetime
        
        if db_manager is None or not db_manager.connected:
            return JSONResponse(status_code=503, content={"status": "error", "message": "BD no conectada"})
        
        # Convertir ID
        try:
            oid = ObjectId(paciente_id)
        except:
            return JSONResponse(status_code=400, content={"status": "error", "message": "ID inválido"})
        
        motivo_defuncion = data.get("motivo", "").strip()
        if not motivo_defuncion:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Motivo vacío"})
        
        # Actualizar documento
        resultado = db_manager.collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "Estado del paciente": "Defunción",
                    "motivo_defuncion": motivo_defuncion,
                    "fecha_defuncion": datetime.now()
                }
            }
        )
        
        if resultado.matched_count == 0:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Paciente no encontrado"})
        
        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": "Defunción registrada exitosamente",
            "paciente_id": paciente_id
        })
        
    except Exception as e:
        print(f"❌ Error al registrar defunción: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ============================================================================
# ENDPOINT: CHAT - EXTRAER ENTIDADES
# ============================================================================

@app.post("/api/chat/extract")
async def extract_from_natural_language(data: dict):
    """Extrae valores de lenguaje natural para los campos del paciente"""
    
    try:
        field_name = data.get("field_name", "")
        field_type = data.get("field_type", "")
        user_input = data.get("user_input", "").strip().lower()
        
        print(f"🔍 Extrayendo para campo: {field_name} (tipo: {field_type})")
        print(f"   Input: {user_input}")
        
        extracted_value = None
        
        # ===== TIPO: NUMBER =====
        if field_type == "number":
            # Extraer primer número del input
            import re
            numbers = re.findall(r'\d+\.?\d*', user_input)
            if numbers:
                extracted_value = float(numbers[0])
                print(f"   ✅ Número extraído: {extracted_value}")
        
        # ===== TIPO: OPTION =====
        elif field_type == "option":
            if field_name == "Sexo":
                if 'masculino' in user_input or user_input.startswith('m'):
                    extracted_value = "M"
                elif 'femenino' in user_input or user_input.startswith('f'):
                    extracted_value = "F"
                print(f"   ✅ Sexo extraído: {extracted_value}")
            
            elif field_name == "Tipo leucemia":
                if 'b' in user_input:
                    extracted_value = "B"
                elif 't' in user_input:
                    extracted_value = "T"
                elif 'm' in user_input:
                    extracted_value = "M"
                print(f"   ✅ Leucemia extraída: {extracted_value}")
        
        # ===== TIPO: TEXT =====
        elif field_type == "text":
            # Para texto, aceptar como está (con límite de caracteres)
            if len(user_input) <= 100:
                extracted_value = user_input.capitalize()
            else:
                extracted_value = user_input[:100].capitalize()
            print(f"   ✅ Texto extraído: {extracted_value}")
        
        # ===== TIPO: OPTIONAL (campos opcionales del chat) =====
        elif field_type == "optional":
            # Detectar si el usuario dice "no tengo" o "no aplica"
            if 'no tengo' in user_input or 'no aplica' in user_input:
                extracted_value = "No tengo" if 'no tengo' in user_input else "No aplica"
                print(f"   ✅ Campo opcional extraído: {extracted_value}")
            else:
                # Aceptar el texto como está
                if len(user_input) <= 100 and user_input:
                    extracted_value = user_input.capitalize()
                    print(f"   ✅ Campo opcional extraído: {extracted_value}")
                else:
                    print(f"   ⚠️  Campo vacío para campo opcional")
                    extracted_value = None
        
        if extracted_value is not None:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "extracted_value": extracted_value,
                    "field_name": field_name
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"No se pudo extraer valor para {field_name}",
                    "extracted_value": None
                }
            )
    
    except Exception as e:
        print(f"❌ Error extrayendo valor: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error extrayendo valor: {str(e)}", "extracted_value": None}
        )

@app.post("/api/tratamiento/guardar")
async def guardar_plan_tratamiento(data: dict):
    """Guardar plan de tratamiento (protocolo y fase)"""
    global db_manager
    
    try:
        paciente_id_str = data.get('paciente_id')
        protocolo = data.get('protocolo')
        fase = data.get('fase')
        
        if not paciente_id_str or not protocolo or not fase:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Faltan campos requeridos: paciente_id, protocolo, fase"}
            )
        
        # Convertir string a ObjectId si es necesario
        from bson.objectid import ObjectId
        try:
            if isinstance(paciente_id_str, str):
                paciente_id = ObjectId(paciente_id_str)
            else:
                paciente_id = paciente_id_str
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": f"ID de paciente inválido: {str(e)}"}
            )
        
        # Conectar si es necesario
        if db_manager is None or not db_manager.connected:
            db_manager = DatabaseManager()
            uri = os.getenv("MONGODB_URI")
            if uri:
                db_manager.uri = uri
            if not db_manager.conectar("modelo_pacientes", "coleccion1"):
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": "Error al conectar a la base de datos"}
                )
        
        # Guardar el plan de tratamiento
        if db_manager.guardar_plan_tratamiento(paciente_id, protocolo, fase):
            # Actualizar el documento del paciente con el estatus y fecha del tratamiento
            from datetime import datetime
            actualizado = db_manager.actualizar_paciente(
                paciente_id, 
                {
                    'estatus_tratamiento': 'Proceso',
                    'fecha_tratamiento': datetime.now()
                }
            )
            
            if actualizado:
                print(f"✅ Documento del paciente actualizado con estatus y fecha del tratamiento")
            else:
                print(f"⚠️  Advertencia: No se pudo actualizar el documento del paciente")
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Plan de tratamiento guardado exitosamente",
                    "paciente_id": str(paciente_id),
                    "protocolo": protocolo,
                    "fase": fase
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Error al guardar el plan de tratamiento"}
            )
    
    except Exception as e:
        print(f"Error al guardar plan de tratamiento: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error al guardar plan de tratamiento: {str(e)}"}
        )
        
        