import pandas as pd
from typing import List


def load_excel(path: str) -> pd.DataFrame:
    """
    Cargar un archivo excel y retornar un datafreme.
    Mostrar cantidad de registros y columnas.
    """
    try:
        df = pd.read_excel(path, engine='openpyxl')
    except FileNotFoundError:
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    except Exception as e:
        raise RuntimeError(f"Error al cargar el archivo: {e}")

    print(f"Archivo cargado exitosamente: {path}")
    print(f"Cantidad de registros: {len(df)}")
    print(f"Cantidad de columnas: ", ", ".join(
        df.columns.astype(str).tolist()))
    return df


def ensure_columns(df: pd.DataFrame, required_columns: List[str]) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(
            f"Las siguientes columnas son requeridas pero no se encuentran en el dataframe: {missing}")
