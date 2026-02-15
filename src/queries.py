import pandas as pd
from tabulate import tabulate


def distribucion_por_diagnostico(df: pd.DataFrame, diagnistico_col: str = "Diagnóstico") -> None:
    if diagnistico_col not in df.columns:
        raise ValueError(
            f"La columna '{diagnistico_col}' no se encuentra en el dataframe.")
    counts = df[diagnistico_col].value_counts(dropna=True).rename_axis(diagnistico_col).reset_index(name='count')
    print(tabulate(counts, headers='keys', tablefmt='psql', showindex=False))

def edadPromedio_por_diagnostico(df : pd.DataFrame, edad_col: str = "Edad", diagnostico_col: str = "Diagnóstico") -> None:
     if edad_col not in df.columns or diagnostico_col not in df.columns:
         raise ValueError(f"Las columnas '{edad_col}' y/o '{diagnostico_col}' no se encuentran en el dataframe.")
     
     promedioEdad = df.groupby(diagnostico_col)[edad_col].mean(numeric_only=True).reset_index().rename(columns={edad_col : "edad_promedio"})
     promedioEdad = promedioEdad.sort_values(by="edad_promedio", ascending=False)
     print(tabulate(promedioEdad, headers='keys', tablefmt='psql', showindex=False))