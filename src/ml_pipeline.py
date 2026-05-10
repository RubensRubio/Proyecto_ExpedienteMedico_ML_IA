
import pandas as pd
from typing import Tuple
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
import joblib
from .config import FEATURE_COLUMNS, TARGET_COLUMN, NUMERIC_FEATURES, CATEGORICAL_FEATURES, MODEL_PATH


def preparar_datos_para_modelo(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Selecciona features y target, elimina nulos, normaliza target.
    Retorna (X, y) listos para entrenamiento.
    """
    columnas_necesarias = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing_columns = [
        columna for columna in columnas_necesarias if columna not in df.columns]

    if missing_columns:
        raise ValueError(
            f"Las siguientes columnas son necesarias pero no se encuentran en el dataframe: {missing_columns}")

    df_modelo = df[columnas_necesarias].copy()
    
    # LIMPIAR VALORES NUMERICOS: Convertir texto invalido en NaN
    for col in NUMERIC_FEATURES:
        if col in df_modelo.columns:
            df_modelo[col] = pd.to_numeric(df_modelo[col], errors="coerce")

    # Eliminar filas con target nulo
    df_modelo = df_modelo.dropna(subset=[TARGET_COLUMN])
    print(
        f"Datos después de eliminar filas con target nulo: {len(df_modelo)} registros restantes.")
    
    # Eliminar filas con NaN
    df_modelo = df_modelo.dropna(subset=NUMERIC_FEATURES)
    print(f"Datos después de eliminar filas con NaN en features numéricas: {len(df_modelo)} registros restantes.")

    # Normalizar target a valores consistentes
    df_modelo[TARGET_COLUMN] = df_modelo[TARGET_COLUMN].astype(
        str).str.strip().str.lower()

    # Estandarizar valores de target a "detectable" y "no detectable"
    df_modelo[TARGET_COLUMN] = df_modelo[TARGET_COLUMN].replace({
        "no_detectable": "no detectable",
        "nodetectable": "no detectable",
        "no-detectable": "no detectable",
    })

    # Filtrar solo registros con target válido
    clases_validadas = ['detectable', 'no detectable']
    df_modelo = df_modelo[df_modelo[TARGET_COLUMN].isin(clases_validadas)]

    print(f"Distribución de clases:")
    print(df_modelo[TARGET_COLUMN].value_counts())

    X = df_modelo[FEATURE_COLUMNS].copy()
    y = df_modelo[TARGET_COLUMN].copy()

    return X, y


def crear_pipeline() -> Pipeline:
    """"
    Crear pipeline completo de procesamiento + modelo
    """

    # Transformadores para features numéricas y categóricas
    numeric_transformer = Pipeline(steps=[
        ("scaler", StandardScaler())
    ])

    # Transformador categorico
    categorical_transformer = Pipeline(steps=[
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])

    # Combinar transformador
    preprocessor = ColumnTransformer(transformers=[
        ("num", numeric_transformer, NUMERIC_FEATURES),
        ("cat", categorical_transformer, CATEGORICAL_FEATURES)
    ],
        remainder="drop"
    )

    # Pipeline completo con modelo
    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("clf", LogisticRegression(max_iter=1000, random_state=42, solver="lbfgs"))
    ])

    return pipeline


def entrenarmodelo_y_evaluar(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> Pipeline:
    """
    Entrena el modelo ERM usando el dataframe dado, evalúa su desempeño y retorna el modelo entrenado junto con las métricas de evaluación.
    """
    print("\nPreparando datos para entrenamiento...")
    X, y = preparar_datos_para_modelo(df)

    if len(X) < 20:
        print("⚠️  ADVERTENCIA: Dataset muy pequeño (<20 muestras). Resultados pueden ser muy variables.")

    print("\n ==== Dividiendo DataSet ====")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    print(
        f"Datos de entrenamiento: {len(X_train)} registros | Datos de prueba: {len(X_test)} registros")

    print("\n ==== Entrenando modelo ====")
    modelo = crear_pipeline()
    modelo.fit(X_train, y_train)
    print("Modelo entrenado exitosamente.")

    # Predicciones y evaluación
    print("\n ==== Evaluando modelo ====")
    y_pred = modelo.predict(X_test)

    # Metricas

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(
        y_test, y_pred, pos_label="detectable", zero_division=0)
    rec = recall_score(y_test, y_pred, pos_label="detectable", zero_division=0)
    f1 = f1_score(y_test, y_pred, pos_label="detectable", zero_division=0)

    print(f"Accuracy: {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall: {rec:.4f}")
    print(f"F1 Score: {f1:.4f}")

    print("\nReporte de clasificación:")
    print(classification_report(y_test, y_pred, digits=4))

    print("===== Matriz de confusión =====")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)

    return modelo


def guardar_modelo(modelo: Pipeline) -> None:
    """
    Guardar modelo entrenado
    """
    joblib.dump(modelo, MODEL_PATH)
    print(f"Modelo guardado en {MODEL_PATH}")


def cargar_modelo() -> Pipeline:
    """
    Cargar modelo entrenado desde disco
    """
    try:
        modelo = joblib.load(MODEL_PATH)
        return modelo
    except FileNotFoundError:
        raise FileNotFoundError(
            f"No se encontró el archivo del modelo en {MODEL_PATH}. Asegúrate de entrenar un modelo primero (Opción 5) o de que el archivo exista.")


def predecir_paciente(modelo: Pipeline, paciente: dict) -> str:
    """
    Dado un diccionario con las características de un paciente, predecir su ERM usando el modelo entrenado.
    """
    df_paciente = pd.DataFrame([paciente])
    
    #Limpiar valores numericos
    for col in NUMERIC_FEATURES:
        if col in df_paciente.columns:
            df_paciente[col] = pd.to_numeric(df_paciente[col], errors="coerce")
            
    # verificar que no haya NaN en las features numericas
    if df_paciente[NUMERIC_FEATURES].isna().any().any():
        columnas_con_nan = df_paciente[FEATURE_COLUMNS].columns[df_paciente[FEATURE_COLUMNS].isna().any()].tolist()
        raise ValueError(f"No se pudieron procesar valores en: {columnas_con_nan}. Asegúrate de ingresar valores numéricos válidos para estas características.")
    
    prediccion = modelo.predict(df_paciente)[0]
    return prediccion
