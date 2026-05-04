
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