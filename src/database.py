
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
from typing import List, Dict
import pandas as pd

class DatabaseManager:
    
    def __init__(self, uri: str = None):
        
        if uri is None:
            uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
            
        self.uri = uri
        self.client = None
        self.db = None
        self.collection = None  
        self.connected = False
        
    def conectar(self, nombre_db: str, nombre_collection: str) -> bool:
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            
            # Verificar la conexión
            self.client.admin.command('ping')
            self.db = self.client[nombre_db]
            self.collection = self.db[nombre_collection]
            self.connected = True
            print(f"✅ Conexión a MongoDB establecida.")
            print(f"   Base de datos: {nombre_db}")
            print(f"   Colección: {nombre_collection}")
            return True
            
        except ServerSelectionTimeoutError as e:
            print(f"Error al conectar a MongoDB: {e}")
            self.connected = False
            return False
        except PyMongoError as e:
            print(f"Error de PyMongo: {e}")
            self.connected = False
            return False
        
    def desconectar(self):
        if self.client:
            self.client.close()
            self.connected = False
            print("Desconectado de MongoDB.")
             
    def guardar_paciente(self, paciente : Dict):
        
        if not self.connected:
            print("No hay conexión a la base de datos.")
            return None
        
        try:
            paciente['fecha_registro'] = datetime.now()
            resultado = self.collection.insert_one(paciente)
            # Devolver el ID del documento insertado en lugar de solo True
            return resultado.inserted_id
        except PyMongoError as e:
            print(f"Error al guardar paciente: {e}")
            return None
        
    def guardar_pacientes_batch(self, pacientes:List[Dict]) -> int:
        
        if not self.connected:
            print("No hay conexión a la base de datos.")
            return False
        
        try:
            for paciente in pacientes:
                paciente['fecha_registro'] = datetime.now()
            resultado = self.collection.insert_many(pacientes)
            print(f"✅ Se guardaron {len(resultado.inserted_ids)} pacientes en MongoDB")
            return len(resultado.inserted_ids)
        except PyMongoError as e:
            print(f"Error al guardar pacientes: {e}")
            return 0
    
    def guardar_respuesta_natural(self, paciente_id, respuesta_natural: str) -> bool:
        """Guardar respuesta en lenguaje natural en colección separada"""
        if not self.connected:
            print("No hay conexión a la base de datos.")
            return False
        
        try:
            coleccion_respuestas = self.db['respuestas_naturales']
            documento = {
                'paciente_id': paciente_id,
                'respuesta': respuesta_natural,
                'fecha_creacion': datetime.now()
            }
            resultado = coleccion_respuestas.insert_one(documento)
            print(f"✅ Respuesta natural guardada con ID: {resultado.inserted_id}")
            return True
        except PyMongoError as e:
            print(f"Error al guardar respuesta natural: {e}")
            return False
    
    def guardar_plan_tratamiento(self, paciente_id, protocolo: str, fase: str) -> bool:
        """Guardar plan de tratamiento en colección separada"""
        if not self.connected:
            print("No hay conexión a la base de datos.")
            return False
        
        try:
            coleccion_planes = self.db['planes_tratamiento']
            documento = {
                'paciente_id': paciente_id,
                'protocolo': protocolo,
                'fase': fase,
                'fecha_creacion': datetime.now()
            }
            resultado = coleccion_planes.insert_one(documento)
            print(f"✅ Plan de tratamiento guardado con ID: {resultado.inserted_id}")
            return True
        except PyMongoError as e:
            print(f"Error al guardar plan de tratamiento: {e}")
            return False
    
    def actualizar_paciente(self, paciente_id, campos_actualizacion: Dict) -> bool:
        """Actualizar campos específicos de un paciente"""
        if not self.connected:
            print("No hay conexión a la base de datos.")
            return False
        
        try:
            resultado = self.collection.update_one(
                {"_id": paciente_id},
                {"$set": campos_actualizacion}
            )
            
            if resultado.matched_count > 0:
                print(f"✅ Paciente {paciente_id} actualizado con campos: {list(campos_actualizacion.keys())}")
                return True
            else:
                print(f"⚠️  Paciente {paciente_id} no encontrado para actualizar")
                return False
        except PyMongoError as e:
            print(f"Error al actualizar paciente: {e}")
            return False
            return False
        
    def obtener_pacientes(self) -> pd.DataFrame:
    
        if not self.connected:
                    print("No hay conexión a la base de datos.")
                    return False
                
        try:
            datos = list(self.collection.find({}, {"_id": 0}))
            if not datos:
                print("No se encontraron pacientes en la base de datos.")
                return pd.DataFrame()
            return pd.DataFrame(datos)
        except PyMongoError as e:
            print(f"Error al obtener pacientes: {e}")
            return pd.DataFrame()
        
    def obtener_pacientes_por_riesgo(self, riesgo:str) -> pd.DataFrame:
    
        if not self.connected:
                    print("No hay conexión a la base de datos.")
                    return False
                
        try:
            datos = list(self.collection.find({"Riesgo calculado": riesgo}, {"_id": 0}))
            if not datos:
                print("No se encontraron pacientes con riesgo '{riesgo}' en la base de datos.")
                return pd.DataFrame()
            return pd.DataFrame(datos)
        except PyMongoError as e:
            print(f"Error al obtener pacientes: {e}")
            return pd.DataFrame() 
        
    def contar_pacientes(self) -> int:
        if not self.connected:
            print("No hay conexión a la base de datos.")
            return 0
        
        try:
            return self.collection.count_documents({})
        except PyMongoError as e:
            print(f"Error al contar pacientes: {e}")
            return 0
        
    def obtener_datos_pacientes(self) -> pd.DataFrame:
        return self.obtener_pacientes()
        
    def obtener_estadisticas(self) -> Dict:
        if not self.connected:
            print("No hay conexión a la base de datos.")
            return {}
        
        try:
            total_pacientes = self.collection.count_documents({})
            riesgo_alto = self.collection.count_documents({"Riesgo calculado": "Alto"})
            riesgo_estandar = self.collection.count_documents({"Riesgo calculado": "estándar"})
            
            return {
                "total_pacientes": total_pacientes,
                "riesgo_alto": riesgo_alto,
                "riesgo_estandar": riesgo_estandar,
                "porcentaje_alto": (riesgo_alto / total_pacientes * 100) if total_pacientes > 0 else 0,
                "porcentaje_estandar": (riesgo_estandar / total_pacientes * 100) if total_pacientes > 0 else 0
            }
        except PyMongoError as e:
            print(f"Error al obtener estadísticas: {e}")
            return {}