# Variable objetivo
TARGET_COLUMN = "ERM"

# Columnas a usar como características para el modelo
FEATURE_COLUMNS = [
    "Diagnóstico",
    "Sexo",
    "Edad",
    "Panel aplicado",
    "Número de Leucocitos al inicio",
    "Número de blastos al inicio",
    "Cariotipo",
    "Clasificación de cariotipo",
    "Biología molecular",
    "Clasificación del Pronostico",
    "GATE Inmunofenotipo",
    "Infiltración",
    "Marcadores aberrantes",
    "Riesgo inicial"
]

# Features numéricas para el preprocesamiento
NUMERIC_FEATURES = [
    "Edad",
    "Número de Leucocitos al inicio",
    "Número de blastos al inicio"
]

# Features categóricas para el preprocesamiento
CATEGORICAL_FEATURES = [f for f in FEATURE_COLUMNS if f not in NUMERIC_FEATURES]

# Ruta del modelo entrenado
MODEL_PATH = "modelo_erm.pkl"


