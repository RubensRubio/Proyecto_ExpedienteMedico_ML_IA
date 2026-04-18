import pandas as pd
from ml_model_pacientes import ModeloPredictorEstadoPaciente
from database import DatabaseManager
import os

class PredictorHelper:
    
    def __init__(self):
        self.modelo_predictor = ModeloPredictorEstadoPaciente()
        self.cargado = False
        
    def cargar_modelo(self, ruta_modelo: str = None) -> bool:
        
        if ruta_modelo is None:
            ruta_modelo = os.path.join(
                os.path.dirname(__file__), 
                "..","modelos", 
                "modelo_predictor_estado.pkl"
            )
            
        if self.modelo.cargar(ruta_modelo):
            self.cargado = True
            return True
        return False
    
    def predecir_desde_diccionario(self, datos: dict) -> dict:
        
        if not self.cargado:
            print("❌ El modelo no está cargado. No se pueden hacer predicciones.")
            return None
        
        try:
            df = pd.DataFrame([datos])
            return self.modelo.predecir(df)
        except Exception as e:
            print(f"❌ Error al predecir: {e}")
            return None
        
    def predecir_desde_bd(self, db_manager: DatabaseManager, id_paciente: str = None) -> dict:
        
        if not self.cargado:
            print("❌ El modelo no está cargado. No se pueden hacer predicciones.")
            return None
        
        try:
            pacientes = db_manager.obtene_todos_pacientes()
            
            if pacientes.empty:
                print("⚠️ No se encontraron pacientes en la base de datos.")
                return None
            
            if id_paciente is None:
                paciente = pacientes.iloc[0:1]
            else:
                paciente = pacientes.iloc[0:1]
                
            prediccion = self.modelo.predecir(paciente)
            return prediccion
            
        except Exception as e:
            print(f"❌ Error al predecir desde la base de datos: {e}")
            return None
        
    def evaluar_modelo(self, db_manager : DatabaseManager) -> None:
        
        if not self.cargado:
            print("❌ El modelo no está cargado. No se pueden evaluar.")
            return
        print("📊 Evaluando modelo con datos de BD...")
        
        try:
            df = db_manager.obtene_todos_pacientes()
            
            if df.empty:
                print("⚠️ No se encontraron pacientes en la base de datos para evaluar.")
                return
            
            X, y = self.modelo.preparar_datos(df)
            X = self.modelo.normalizar(X)
            
            predicciones = self.modelo.modelo.predict(X)
            
            from sklearn.metrics import accuracy_score
            accurancy = accuracy_score(y, predicciones)
            
            print("📊 Evaluando modelo con datos de BD...")
        except Exception as e:
            print(f"❌ Error al evaluar el modelo con la base de datos: {e}")