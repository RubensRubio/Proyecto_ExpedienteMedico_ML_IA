import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os
from typing import Tuple, Dict
from datetime import datetime


class ModeloPredictorEstadoPaciente:
    
    
    def __init__(self):
        self.modelo = None
        self.encoders = {}
        self.scaler = None
        self.features_numericas = None
        self.features_categoricas = None
        self.clases = None
        self.historico = {
            'entrenamiento' :[],
            'evaluaciones':[]
        }
        
    def obtener_datos(self, db_manager) -> pd.DataFrame:
        print("📥 Obteniendo datos de MongoDB...")
        
        try:
            df = db_manager.obtener_datos_pacientes()
            print(f"✅ Datos obtenidos: {len(df)} registros")
            return df
        except Exception as e:
            print(f"❌ Error al obtener datos: {e}")
            return pd.DataFrame()  # Retorna un DataFrame vacío en caso de error
        
    def explorar_datos(self, df: pd.DataFrame) -> None:
        
        print("\n" + "=" * 70)
        print("EXPLORACIÓN DE DATOS")
        print("=" * 70)
        
        print(f"\n📊 Forma del dataset: {df.shape} (filas, columnas)")
        print(f"\n🎯 Variable objetivo (Estado del paciente):")
        print(df["Estado del paciente"].value_counts())
        
        print(f"\n🔢 Tipos de datos:")
        print(df.dtypes)
        
        print(f"\n⚠️  Valores faltantes:")
        print(df.isnull().sum())
        
        print("\n" + "=" * 70 + "\n")
        
    def preparar_datos(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series] :
        
        print("🔧 Preparando datos para el modelo...")
        df_preparado = df.copy()
        
        y = df_preparado["Estado del paciente"]
        X = df_preparado.drop(columns=["Estado del paciente"])
        
        if "fecha_registro" in X.columns:
            X = X.drop("fecha_registro", axis=1)
            
        print(f"   • Features (X): {X.shape}")
        print(f"   • Target (y): {y.shape}")
        
        self.features_numericas = X.select_dtypes(include=[np.number]).columns.tolist()
        self.features_categoricas = X.select_dtypes(include=['object']).columns.tolist()
        
        print(f"\n   Features numéricas ({len(self.features_numericas)}): {self.features_numericas}")
        print(f"   Features categóricas ({len(self.features_categoricas)}): {self.features_categoricas}")
        
        print(f"\n   Codificando variables categóricas...")
        for col in self.features_categoricas:
            print(f"      • {col}: {X[col].unique()}")
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
            self.encoders[col] = le
            
        self.clases = y.unique()
        print(f"\n   Clases en variable objetivo: {self.clases}")
        
        print("Datos preparados con éxito.")
        return X, y
    
    def normalizar_datos(self, X:pd.DataFrame) -> pd.DataFrame:
        print("⚖️ Normalizando datos numéricos...")
        
        X_normalizado = X.copy()
        if self.features_numericas:
            self.scaler = StandardScaler()
            X_normalizado[self.features_numericas] = self.scaler.fit_transform(
                X[self.features_numericas]
            )
            print(f"   ✅ {len(self.features_numericas)} variables normalizadas\n")
            
        return X_normalizado
    
    def dividir_datos(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, random_state: int = 42) -> Tuple:
        
        print("✂️  Dividiendo datos (80% entrenamiento, 20% prueba)...")
        
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=test_size,
                random_state=random_state,
                stratify=y
            )
        except ValueError:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=test_size,
                random_state=random_state
            )
        
        print(f"   • Entrenamiento: {X_train.shape[0]} registros")
        print(f"   • Prueba: {X_test.shape[0]} registros\n")
        
        return X_train, X_test, y_train, y_test
    
    def entrenar(self, X_train: pd.DataFrame, y_train: pd.Series, n_estimators: int = 100, max_depth : int = 10) -> None:
        print("🤖 Entrenando modelo Random Forest...")
        print(f"   • Árboles: {n_estimators}")
        print(f"   • Profundidad máxima: {max_depth}")
        
        self.modelo = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1
        )
        
        self.modelo.fit(X_train, y_train)
        
        info_enternamiento = {
            'fecha' : datetime.now().isoformat(),
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'n_features' : X_train.shape[1],
            'n_samples' : X_train.shape[0],
        }
        
        self.historico['entrenamiento'].append(info_enternamiento)
        
        print("   ✅ Modelo entrenado con éxito\n")
        
    def evaluar(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        
        print("📊 Evaluando modelo...")
        
        y_pred = self.modelo.predict(X_test)
        y_pred_proba = self.modelo.predict_proba(X_test)
        
        accuracy = accuracy_score(y_test, y_pred)
        
        print("\n" + "=" * 70)
        print("RESULTADOS DE EVALUACIÓN")
        print("=" * 70)
        print(f"\n🎯 Accuracy (precisión general): {accuracy:.2%}")
        
        print("\n📈 Reporte de clasificación:")
        clases_presentes = sorted(y_test.unique().tolist())
        print(classification_report(y_test, y_pred, target_names=clases_presentes))
        
        print("\n📉 Matriz de confusión:")
        cm = confusion_matrix(y_test, y_pred)
        print(cm)
        
        print("\n🌟 Importancia de características (Top 5):")
        importancias = pd.DataFrame({
            'feature': X_test.columns,
            'importance': self.modelo.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for idx, row in importancias.head(5).iterrows():
            print(f"   {row['feature']}: {row['importance']:.4f}")
        
        print("\n" + "=" * 70 + "\n")
        
        info_evaluacion = {
            'fecha' : datetime.now().isoformat(),
            'accuracy': accuracy,
            'n_test_samples': len(y_test),
            'matriz_confusion': cm.tolist(),
        }
        self.historico['evaluaciones'].append(info_evaluacion)
        
        return {
            'accuracy': accuracy,
            'y_pred': y_pred,
            'y_pred_proba': y_pred_proba,
            'importancias' : importancias
        }
        
    def guardar_modelo(self, ruta: str = "modelo_predictor_estado.pkl") -> bool:
        
        print(f"💾 Guardando modelo en '{ruta}'...")
        
        try:
            
            os.makedirs(os.path.dirname(ruta) if os.path.dirname(ruta) else '.', exist_ok=True)

            joblib.dump(self.modelo, ruta)       
            encoders_ruta = ruta.replace(".pkl", "_encoders.pkl")
            joblib.dump(self.encoders, encoders_ruta)
            
            scaler_ruta = ruta.replace(".pkl", "_scaler.pkl")
            joblib.dump(self.scaler, scaler_ruta)
            
            print("   ✅ Modelo guardado con éxito\n")
            print(f"   • Modelo: {ruta}")
            print(f"   • Encoders: {encoders_ruta}")
            print(f"   • Scaler: {scaler_ruta}\n")
            return True
        
        except Exception as e:
            print(f"   ❌ Error al guardar el modelo: {e}\n")
            return False
        
    def cargar_modelo(self, ruta: str = "modelo_predictor_estado.pkl") -> bool:
        
        print(f"📂 Cargando modelo desde '{ruta}'...")
        
        try:
            self.modelo = joblib.load(ruta)
            
            encoders_ruta = ruta.replace(".pkl", "_encoders.pkl")
            self.encoders = joblib.load(encoders_ruta)
            
            scaler_ruta = ruta.replace(".pkl", "_scaler.pkl")
            self.scaler = joblib.load(scaler_ruta)
            
            print("   ✅ Modelo cargado con éxito\n")
            return True
        
        except Exception as e:
            print(f"   ❌ Error al cargar el modelo: {e}\n")
            return False
        
    def predecir(self, datos_paciente : pd.DataFrame) -> Dict :
        
        if self.modelo is None:
            print("❌ Error: No hay un modelo cargado para hacer predicciones.")
            return None
        
        try:
            
            datos_preparados = datos_paciente.copy()
            for col in self.features_categoricas:
                if col in datos_preparados.columns:
                    datos_preparados[col] = self.encoders[col].transform(
                        datos_preparados[col].astype(str)
                    )
                    
            if self.scaler:
                datos_preparados[self.features_numericas] = self.scaler.transform(
                    datos_preparados[self.features_numericas]
                )
                
            prediccion = self.modelo.predict(datos_preparados)[0]
            probabilidades = self.modelo.predict_proba(datos_preparados)[0]
            confianza = max(probabilidades)
            
            idx_prediccion = np.argmax(probabilidades)
            
            resultado = {
                'estado_predicho': self.clases[idx_prediccion],
                'confianza': confianza,
                'probabilidades': {
                    self.clases[i]: float(probabilidades[i])
                    for i in range(len(self.clases))
                }
            }
            
            return resultado
        except Exception as e:
            print(f"❌ Error al hacer predicción: {e}")
            return None
        
    def pipeline_completo(self, db_manager, guardar_modelo: bool = True) -> None:
        
        try:
            
            print("\n" + "🚀 " * 20)
            print("INICIANDO PIPELINE DE ENTRENAMIENTO DEL MODELO")
            print("🚀 " * 20 + "\n")
            
            df = self.obtener_datos(db_manager)
            if df.empty:
                print("❌ No se pudieron obtener datos para entrenar el modelo.")
                return False
            
            self.explorar_datos(df)
            
            X, y = self.preparar_datos(df)
            
            X = self.normalizar_datos(X)
            
            X_train, X_test, y_train, y_test = self.dividir_datos(X, y)
            
            self.entrenar(X_train, y_train)
            
            resultados = self.evaluar(X_test, y_test)
            
            if guardar_modelo:
                ruta_modelo = os.path.join(
                    os.path.dirname(__file__),
                    "..", "modelos",
                    "modelo_predictor_estado.pkl"
                )
                self.guardar_modelo(ruta_modelo)
                
            print("  ✅ Pipeline completado con éxito\n")
            return True
        except Exception as e:
            print(f"❌ Error en pipeline completo: {e}")
            return False
        