import pandas as pd
from typing import Optional


def busqueda_exacta(df: pd.DataFrame, edad: Optional[int] = None, sexo: Optional[str] = None, diagnostico: Optional[str] = None) -> pd.DataFrame:
    query = df.copy()

    if edad is not None:
        query = query[query['Edad'] == edad]
    if sexo is not None:
        query = query[query['Sexo'].astype(str).str.lower() == sexo.lower()]
    if diagnostico is not None:
        query = query[query['Diagnóstico'].astype(str).str.lower() == diagnostico.lower()]
        
    return query

def busqueda_similar(df: pd.DataFrame, edad: int, sexo: str, diagnostico: str, numberTop: int = 5) -> pd.DataFrame:
    
    requerido = ['Edad', 'Sexo', 'Diagnóstico']
    
    for col in requerido:
        if col not in df.columns:
            raise ValueError(f"La columna '{col}' es requerida pero no se encuentra en el dataframe.")
    
    filtro = df[
        (df["Diagnóstico"].astype(str).str.lower() == diagnostico.lower()) &
        (df["Sexo"].astype(str).str.lower() == sexo.lower())
    ].copy()
    
    if filtro.empty:
        return filtro
    
    filtro = filtro.dropna(subset=['Edad'])
    filtro['diferencia_edad'] = (filtro['Edad'].astype(float) - float(edad)).abs()
    filtro = filtro.sort_values(by='diferencia_edad').head(numberTop)
    return filtro