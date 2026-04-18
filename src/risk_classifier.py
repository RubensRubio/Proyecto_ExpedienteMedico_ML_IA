import pandas as pd
from typing import Tuple
from typing import List, Dict


def clasificar_riesgo_por_edad(edad: float) -> str:

    try:
        edad = float(edad)
    except (ValueError, TypeError):
        raise ValueError(f"Edad inválida: '{edad}'. Debe ser un número.")
    
    if edad < 1:
        return "Riesgo alto"
    elif 1 <= edad < 10:
        return "Riesgo estandar"
    else:
        return "Riesgo alto"


def clasificar_riesgo_por_leucos(numeroLeucos: float) -> str:

    try:
        numeroLeucos = float(numeroLeucos)
    except (ValueError, TypeError):
        raise ValueError(f"Número de leucocitos inválido: '{numeroLeucos}'. Debe ser un número.")

    if numeroLeucos < 50:
        return "Riesgo estandar"
    else:
        return "Riesgo alto"


def aplicar_regla_final(riesgo_edad: str, riesgo_leucos: str) -> str:
    if riesgo_edad == "Riesgo alto" or riesgo_leucos == "Riesgo alto":
        return "Riesgo alto"
    else:
        return "Riesgo estandar"


def clasificar_paciente(edad: float, numeroLeucos: float) -> Tuple[str, str, str]:

    riesgo_edad = clasificar_riesgo_por_edad(edad)
    riesgo_leucos = clasificar_riesgo_por_leucos(numeroLeucos)
    riesgo_final = aplicar_regla_final(riesgo_edad, riesgo_leucos)

    return riesgo_edad, riesgo_leucos, riesgo_final


def clasificar_pacientes(df: pd.DataFrame) -> pd.DataFrame:

    df_clasificado = df.copy()
    
    try:
        df_clasificado["Edad"] = pd.to_numeric(df_clasificado["Edad"], errors="coerce")
        df_clasificado["Número de Leucocitos al inicio"] = pd.to_numeric(
            df_clasificado["Número de Leucocitos al inicio"], errors="coerce"
        )
    except KeyError as e:
        raise KeyError(f"Error: El DataFrame debe contener las columnas 'Edad' y 'Número de Leucocitos al inicio'. Columna faltante: {e}")

    if df_clasificado["Edad"].isna().all() or df_clasificado["Número de Leucocitos al inicio"].isna().all():
        raise ValueError("Error: Todas las filas tienen valores no numéricos en 'Edad' o 'Número de Leucocitos al inicio'. No se puede clasificar a ningún paciente.")

    filas_invalidas = df_clasificado[
        df_clasificado["Edad"].isna() | df_clasificado["Número de Leucocitos al inicio"].isna()
    ]
    
    if not filas_invalidas.empty:
        print("⚠️  Advertencia: Se encontraron filas con datos inválidos:")
        print(filas_invalidas[["Edad", "Número de Leucocitos al inicio"]])
        print("Estas filas serán omitidas en la clasificación.\n")
    
    resultados = df_clasificado.apply(
        lambda row: clasificar_paciente(
            row["Edad"], row["Número de Leucocitos al inicio"]
        ) if pd.notna(row["Edad"]) and pd.notna(row["Número de Leucocitos al inicio"])
        else (None, None, None),
        axis=1
    )

    df_clasificado["Riesgo calculado"] = resultados.apply(lambda x: x[0])
    df_clasificado["Riesgo por edad"] = resultados.apply(lambda x: x[1])
    df_clasificado["Riesgo por leucocito"] = resultados.apply(lambda x: x[2])

    return df_clasificado


def mostrar_resumen_clasificacion(df: pd.DataFrame) -> None:

    if "Riesgo calculado" not in df.columns:
        print("El DataFrame no contiene la columna 'Riesgo calculado'. Por favor, clasifique los pacientes primero.")
        return

    print("\n" + "=" * 60)
    print("RESUMEN DE CLASIFICACIÓN DE RIESGO")
    print("=" * 60)
    
    registros_validos = df[df["Riesgo calculado"].notna()]
    if registros_validos.empty:
        print("No se clasificaron pacientes debido a datos inválidos.")
        return

    conteo = df["Riesgo calculado"].value_counts()
    print(f"\n📊 Distribución de riesgo:")

    for riesgo, cantidad in conteo.items():
        porcentaje = (cantidad / len(df)) * 100
        print(f"  • Riesgo {riesgo}: {cantidad} pacientes ({porcentaje:.1f}%)")

    print("\n" + "=" * 60)


def preparar_pacientes_para_bd(df: pd.DataFrame) -> List[Dict]:

    columnas_requeridas = [
        "Edad", 
        "Sexo",
        "Número de Leucocitos al inicio", 
        "Riesgo calculado",
        "Panel aplicado",
        "Número de blastos al inicio"
    ]
    
    para_verificar =[
        "Edad",
        "Sexo",
        "Número de Leucocitos al inicio",
        "Riesgo calculado",
        "Panel aplicado"
    ]

    for col in para_verificar:
        if col not in df.columns:
            raise ValueError(
                f"Error: El DataFrame debe contener la columna '{col}' para preparar los datos para la base de datos.")

    df_filtrado = df[df["Riesgo calculado"].notna()].copy()
    
    if df_filtrado.empty:
        raise ValueError("No hay pacientes con riesgo calculado para guardar en la base de datos.")
        
    pacientes_db = pd.DataFrame()
    pacientes_db["Edad"] = df_filtrado["Edad"]
    pacientes_db["Sexo"] = df_filtrado["Sexo"]
    pacientes_db["Número de Leucocitos al inicio"] = df_filtrado["Número de Leucocitos al inicio"]
    pacientes_db["Riesgo calculado"] = df_filtrado["Riesgo calculado"]
    
    pacientes_db["Tipo leucemia"] = df_filtrado["Panel aplicado"].apply(extraer_tipo_leucemia)
    
    nombre_blastos = None
    if "Número de blastos al inicio" in df_filtrado.columns:
        nombre_blastos = "Número de blastos al inicio"
    elif "Número de blastos al inicio" in df_filtrado.columns:
        nombre_blastos = "Número de blastos al incio"
    
    if nombre_blastos:    
        pacientes_db["Número de blastos"] = df_filtrado[nombre_blastos].apply(procesar_blastos)
    else:
        print("⚠️  Advertencia: Columna 'Número de blastos al incio' no encontrada, se usará 0 para todos")
        pacientes_db["Número de blastos"] = 0
        
    if "Cariotipo" in df_filtrado.columns:
        pacientes_db["Clasificación cariotipo"] = df_filtrado["Cariotipo"].apply(procesar_cariotipo)
    else:
        print("⚠️  Advertencia: Columna 'Cariotipo' no encontrada, se usará 'No detectado' para todos")
        pacientes_db["Clasificación cariotipo"] = "No detectado"
        
    if "Biología molecular" in df_filtrado.columns:
        pacientes_db["Biología molecular"] = df_filtrado["Biología molecular"].apply(procesar_biologia_molecular)
    else:
        print("⚠️  Advertencia: Columna 'Biología molecular' no encontrada, se usará 'Negativo' para todos")
        pacientes_db["Biología molecular"] = "Negativo"
        
    if "GATE Inmunofenotipo" in df_filtrado.columns:
        pacientes_db["GATE Inmunofenotipo"] = df_filtrado["GATE Inmunofenotipo"].apply(procesar_gate_inmunofenotipo)
        pacientes_db["Tipo infiltración"] = pacientes_db["GATE Inmunofenotipo"].apply(clasificar_tipo_infiltracion)
    else:
        print("⚠️  Advertencia: Columna 'GATE Inmunofenotipo' no encontrada, se usará 0 para todos")
        pacientes_db["GATE Inmunofenotipo"] = 0
        pacientes_db["Tipo infiltracion"] = "Baja infiltración"
        
    if "Marcadores aberrantes" in df_filtrado.columns:
        pacientes_db["Resistencia al tratamiento"] = df_filtrado["Marcadores aberrantes"].apply(procesar_marcadores_aberrantes)
    else:
        print("⚠️  Advertencia: Columna 'Marcadores aberrantes' no encontrada, se usará False para todos")
        pacientes_db["Resistencia al tratamiento"] = False
        
    if "Estado del paciente" in df_filtrado.columns:
        pacientes_db["Estado del paciente"] = df_filtrado["Estado del paciente"].apply(clasificar_estado_paciente)
    else:
        print("⚠️  Advertencia: Columna 'Estado del paciente' no encontrada, se usará 'Otra enfermedad' para todos")
        pacientes_db["Estado del paciente"] = "Otra enfermedad"
        
    pacientes = pacientes_db.to_dict(orient="records")
    return pacientes

def extraer_tipo_leucemia(panel_aplicado: str) -> str:
    
    if pd.isna(panel_aplicado):
        return ""

    panel_str = str(panel_aplicado).strip()
    
    if "Panel B" in panel_str:
        return "B"
    elif "Panel T" in panel_str:
        return "T"
    elif "Panel Mieloide" in panel_str:
        return "M"
    else:
        return ""
    
def procesar_blastos(blastos:any) -> float:
    
    if pd.isna(blastos):
        return 0
    
    try:
        valor = float(blastos)
        return valor
    except (ValueError, TypeError):
        return 0
    
def procesar_cariotipo(cariotipo: str) -> str:
    
    if pd.isna(cariotipo):
        return "No detectado"
    
    cariotipo_str = str(cariotipo).strip()
    
    if cariotipo_str == "" or cariotipo_str.lower() == "no detectado":
        return "No detectado"
    else:
        return "Anormal"    
    
def procesar_biologia_molecular(biologia: str) -> str:
    
    if pd.isna(biologia):
        return "Negativo"
    
    biologia_str = str(biologia).strip()
    
    if biologia_str == "":
        return "Negativo"
    elif "T 9:22" in biologia_str:
        return "Desfavorable"
    else:
        return "Favorable"    
    
def procesar_gate_inmunofenotipo(gate : any) -> float:
    
    if pd.isna(gate):
        return 0
    
    try:
        
        if isinstance(gate, str):
            gate_str = gate.strip().replace("%", "").strip()
            valor = float(gate_str)
        else:
            valor = float(gate)
            
        if 0 <= valor <= 1:
            valor = valor * 100
            
        return valor
    except (ValueError, TypeError):
        return 0
    
def clasificar_tipo_infiltracion(gate : float) -> str:
    
    try:
        valor = float(gate)
    except(ValueError, TypeError):
        valor = 0
        
    if valor >= 70:
        return "Alta infiltración"
    elif valor >= 10:
        return "Moderada moderada"
    else:
        return "Baja infiltración"
    
def procesar_marcadores_aberrantes(marcadores: str) -> bool:
    
    if pd.isna(marcadores):
        return False
    
    marcadores_str = str(marcadores).strip()
    
    if marcadores_str == "" or marcadores_str.lower() == "negativos":
        return False
    else:
        return True
    
def clasificar_estado_paciente(estado : str)-> str:
    
    if pd.isna(estado):
        return "Otra enfermedad"
    
    estado_str = str(estado).strip().lower()
    
    if "defunción" in estado_str:
        return "Defunción"
    elif "seguimiento" in estado_str:
        return "Tratamiento"
    elif "paliativos" in estado_str or "paliativo" in estado_str:
        return "Cuidados paliativos"
    else:
        return "Otra enfermedad"