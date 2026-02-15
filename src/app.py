import os
from data_loader import load_excel, ensure_columns
from queries import distribucion_por_diagnostico, edadPromedio_por_diagnostico
from similarity import busqueda_exacta, busqueda_similar

DATA_PATH = os.path.join(os.path.dirname(
    __file__), "..", "data", "pacientes.xlsx")


def entrada_numero(prompt, permite_vacios=False):
    while True:
        value = input(prompt)
        if permite_vacios and value == "":
            return None
        try:
            return int(value)
        except ValueError:
            print("Por favor, ingrese un número entero válido o deje vacio.")


def entrada_cadena(prompt, permite_vacios=False):
    while True:
        value = input(prompt)
        if permite_vacios and value == "":
            return None
        if value:
            return value
        print("Entrada invalida . Intente de nuevo.")


def main():

    print("Aplicación: Sistema de consulta de pacientes - Fase 1")
    path = input(f"Ingrese la ruta del archivo excel : ") or DATA_PATH

    try:
        df = load_excel(path)
    except Exception as e:
        print(f"Error al cargar el archivo: {e}")
        return

    columnas_requeridad = ['Edad', 'Sexo', 'Diagnóstico']
    try:
        ensure_columns(df, columnas_requeridad)
    except Exception as e:
        print(f"Error en el dataframe: {e}")
        return

    while True:
        print("\nOpciones:")
        print("1. Ver distribución por diagnóstico")
        print("2. Ver edad promedio por diagnóstico")
        print("3. Búsqueda por criterio exacta de pacientes")
        print("4. Búsqueda de pacientes similares")
        print("5. Salir")

        opcion = input("Seleccione una opción (1-5): ")

        if opcion == "1":
            distribucion_por_diagnostico(df)
        elif opcion == "2":
            edadPromedio_por_diagnostico(df)
        elif opcion == "3":
            edad = entrada_numero(
                "Ingrese la edad del paciente (o deje vacio): ", permite_vacios=True)
            sexo = entrada_cadena(
                "Ingrese el sexo del paciente (M/F) o deje vacio: ", permite_vacios=True)
            diagnostico = entrada_cadena(
                "Ingrese el diagnóstico del paciente (o deje vacio): ", permite_vacios=True)
            resultado = busqueda_exacta(df, edad, sexo, diagnostico)

            if resultado.empty:
                print(
                    "No se encontraron pacientes que coincidan con los criterios exactos.")
            else:
                print(resultado.to_string(index=False))
        elif opcion == "4":
            edad = entrada_numero("Ingrese la edad del paciente: ")
            sexo = entrada_cadena("Ingrese el sexo del paciente: ")
            diagnostico = entrada_cadena(
                "Ingrese el diagnóstico del paciente: ")
            numero_resultados = entrada_numero(
                "¿Cuántos pacientes similares desea ver? (default 5): ", permite_vacios=True)
            resultado = busqueda_similar(
                df, edad, sexo, diagnostico, numberTop=numero_resultados)

            if resultado.empty:
                print("No se encontraron pacientes similares.")
            else:
                print(resultado.to_string(index=False))
        elif opcion == "5":
            print("Saliendo de la aplicación.")
            break
        else:
            print("Opción inválida. Por favor, seleccione una opción entre 1 y 5.")


if __name__ == "__main__":
    main()
