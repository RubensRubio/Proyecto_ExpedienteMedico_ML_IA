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
        
        print(f"   Filas originales: {len(df_preparado)}")
        print(f"   Columnas: {df_preparado.columns.tolist()}")
        
        # Normalizar tipos de datos ANTES de rellenar NaN
        print(f"\n   Normalizando tipos de datos...")
        for col in df_preparado.columns:
            # Convertir strings booleanos a booleanos reales
            if col in ['Resistencia al tratamiento']:
                df_preparado[col] = df_preparado[col].apply(
                    lambda x: x if isinstance(x, bool) else (str(x).lower() == 'true' if pd.notna(x) else False)
                )
                print(f"      • {col}: Convertido a booleano")
            
            # Intentar convertir a números si es posible
            elif col in ['Edad', 'Número de Leucocitos al inicio', 'Número de blastos', 'GATE Inmunofenotipo']:
                try:
                    df_preparado[col] = pd.to_numeric(df_preparado[col], errors='coerce')
                    print(f"      • {col}: Convertido a numérico")
                except:
                    print(f"      • {col}: No se pudo convertir a numérico")
        
        print(f"\n   Rellenando valores NaN...")
        for col in df_preparado.columns:
            nan_count = df_preparado[col].isna().sum()
            if nan_count > 0:
                if df_preparado[col].dtype == 'bool' or col in ['Resistencia al tratamiento']:
                    # Para booleanos, llenar con False
                    df_preparado[col] = df_preparado[col].fillna(False).astype(bool)
                    print(f"      • {col}: {nan_count} NaN → False (bool)")
                elif df_preparado[col].dtype in ['int64', 'float64']:
                    # Para números, llenar con 0
                    df_preparado[col] = df_preparado[col].fillna(0)
                    print(f"      • {col}: {nan_count} NaN → 0 (numérico)")
                else:
                    # Para strings, llenar con 'Desconocido'
                    df_preparado[col] = df_preparado[col].fillna('Desconocido').astype(str)
                    print(f"      • {col}: {nan_count} NaN → 'Desconocido' (string)")
        
        print(f"   Filas después de rellenar NaN: {len(df_preparado)}")
        print(f"\n   Tipos finales de datos:\n{df_preparado.dtypes}")
        
        y = df_preparado["Estado del paciente"]
        X = df_preparado.drop(columns=["Estado del paciente"])
        
        if "fecha_registro" in X.columns:
            X = X.drop("fecha_registro", axis=1)
        
        if "_id" in X.columns:
            X = X.drop("_id", axis=1)
            
        print(f"   • Features (X): {X.shape}")
        print(f"   • Target (y): {y.shape}")
        
        self.features_numericas = X.select_dtypes(include=[np.number]).columns.tolist()
        self.features_categoricas = X.select_dtypes(include=['object', 'bool']).columns.tolist()
        
        print(f"\n   Features numéricas ({len(self.features_numericas)}): {self.features_numericas}")
        print(f"   Features categóricas ({len(self.features_categoricas)}): {self.features_categoricas}")
        
        print(f"\n   Codificando variables categóricas...")
        for col in self.features_categoricas:
            unique_vals = X[col].unique()
            print(f"      • {col}: {unique_vals[:5]}...")  # Solo mostrar primeros 5 valores
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
        # Usar todas las clases del modelo, no solo las presentes en y_test
        clases_reporte = sorted(self.clases.tolist())
        print(classification_report(y_test, y_pred, labels=clases_reporte, target_names=clases_reporte, zero_division=0))
        
        print("\n📉 Matriz de confusión:")
        cm = confusion_matrix(y_test, y_pred, labels=clases_reporte)
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
            
            print(f"\n📊 Predicción - Preparando datos...")
            print(f"   Columnas de entrada: {datos_preparados.columns.tolist()}")
            
            # ========== CRITERIO CLÍNICO: BLASTOS >= 20% ==========
            # Si el número de blastos es >= 20%, es diagnóstico de leucemia
            # y requiere tratamiento obligatorio
            num_blastos = None
            if 'Número de blastos' in datos_paciente.columns:
                num_blastos = float(datos_paciente['Número de blastos'].values[0])
                print(f"   🔬 Número de blastos: {num_blastos:.2%} (valor: {num_blastos})")
                
                if num_blastos >= 0.20:  # 20% o más
                    print(f"   ⚠️  CRITERIO CLÍNICO ACTIVADO: Blastos >= 20%")
                    print(f"   🏥 DIAGNÓSTICO AUTOMÁTICO: TRATAMIENTO OBLIGATORIO")
                    print(f"   💊 Razón: Alto porcentaje de blastos indica leucemia confirmada")
                    
                    resultado = {
                        'clase_predicha': 'Tratamiento',
                        'confianza': 1.0,  # 100% de confianza
                        'probabilidades': {
                            'Tratamiento': 1.0,
                            'Defunción': 0.0,
                            'Cuidados paliativos': 0.0
                        },
                        'criterio_clinico': True,
                        'razon': 'Número de blastos >= 20% indica leucemia confirmada. Tratamiento obligatorio.'
                    }
                    
                    return resultado
            
            #All features that the model was trained with
            todas_las_features = self.features_numericas + self.features_categoricas
            
            # Add missing columns
            for col in todas_las_features:
                if col not in datos_preparados.columns:
                    if col in self.features_numericas:
                        datos_preparados[col] = 0.0
                    else:
                        datos_preparados[col] = 'Desconocido'
            
            # Remove unexpected columns
            columnas_a_eliminar = [col for col in datos_preparados.columns if col not in todas_las_features]
            if columnas_a_eliminar:
                print(f"   ⚠️  Eliminando columnas no esperadas: {columnas_a_eliminar}")
                datos_preparados = datos_preparados.drop(columns=columnas_a_eliminar)
            
            # Reorder columns to MATCH training order
            # The training order is: all numeric features first, then categorical features
            # which matches self.features_numericas + self.features_categoricas
            datos_preparados = datos_preparados[self.features_numericas + self.features_categoricas]
            
            print(f"   Orden final de columnas: {datos_preparados.columns.tolist()}")
            
            # Convert numeric types
            for col in self.features_numericas:
                if col in datos_preparados.columns:
                    datos_preparados[col] = pd.to_numeric(datos_preparados[col], errors='coerce')
                    if datos_preparados[col].isna().any():
                        datos_preparados[col] = datos_preparados[col].fillna(0)
            
            # Encode categorical variables
            for col in self.features_categoricas:
                if col in datos_preparados.columns and col in self.encoders:
                    valor_str = str(datos_preparados[col].values[0])
                    try:
                        datos_preparados[col] = self.encoders[col].transform([valor_str])
                    except (ValueError, KeyError) as e:
                        print(f"   ⚠️  Valor desconocido para '{col}': '{valor_str}' ({e}), usando 'Desconocido'")
                        try:
                            datos_preparados[col] = self.encoders[col].transform(['Desconocido'])
                        except (ValueError, KeyError):
                            print(f"   ⚠️  Encoder para '{col}' tampoco tiene 'Desconocido', asignando 0")
                            datos_preparados[col] = 0
            
            # Normalize numeric data
            if self.scaler and self.features_numericas:
                # Get only numeric columns as a 2D array for the scaler
                X_numeric = datos_preparados[self.features_numericas].values
                X_scaled = self.scaler.transform(X_numeric)
                datos_preparados[self.features_numericas] = X_scaled
            
            # Convert to numpy array if needed for prediction
            # sklearn expects (n_samples, n_features) shape
            X_array = datos_preparados.values
            
            print(f"   ✅ Shape final: {X_array.shape}, dtypes: {datos_preparados.dtypes.to_dict() if hasattr(datos_preparados, 'dtypes') else 'array'}")
            print(f"   🤖 Realizando predicción con sklearn (predicción del modelo)...")
            print(f"   📋 Clases conocidas: {self.clases}")
            
            # Perform prediction
            prediccion = self.modelo.predict([X_array[0]])[0]
            probabilidades = self.modelo.predict_proba([X_array[0]])[0]
            confianza = max(probabilidades)
            
            print(f"   📊 Probabilidades shape: {probabilidades.shape}, valores: {probabilidades}")
            print(f"   📋 Clases del modelo: {self.clases} (length: {len(self.clases)})")
            
            # Find prediction index
            idx_prediccion = np.argmax(probabilidades)
            clase_predicha = self.clases[idx_prediccion]
            
            # ⚠️ FIX: Usar len(probabilidades) en lugar de len(self.clases)
            # porque el array de probabilidades puede tener un tamaño diferente
            num_clases = len(probabilidades)
            
            resultado = {
                'clase_predicha': str(clase_predicha),
                'confianza': float(confianza),
                'probabilidades': {
                    str(self.clases[i]): float(probabilidades[i])
                    for i in range(num_clases) if i < len(self.clases)
                },
                'criterio_clinico': False
            }
            
            print(f"   ✅ Predicción del modelo: {clase_predicha} (confianza: {confianza:.2%})")
            
            return resultado
        except Exception as e:
            print(f"❌ Error al hacer predicción: {e}")
            import traceback
            traceback.print_exc()
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
        