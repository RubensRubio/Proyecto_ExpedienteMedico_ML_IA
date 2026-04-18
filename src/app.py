import os
from pathlib import Path
from dotenv import load_dotenv
from data_loader import load_excel, ensure_columns
from queries import distribucion_por_diagnostico, edadPromedio_por_diagnostico
from similarity import busqueda_exacta, busqueda_similar
from ml_pipeline import entrenarmodelo_y_evaluar, guardar_modelo, cargar_modelo, predecir_paciente, FEATURE_COLUMNS, TARGET_COLUMN
from risk_classifier import clasificar_pacientes, mostrar_resumen_clasificacion, preparar_pacientes_para_bd
from database import DatabaseManager
from ml_model_pacientes import ModeloPredictorEstadoPaciente

#Carga de variables de entorno
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DATA_PATH = os.path.join(os.path.dirname(
    __file__), "..", "data", "pacientes.xlsx")

db_manager = None

def entrada_numero(prompt, permite_vacios=False):
    while True:
        value = input(prompt).strip()
        if permite_vacios and value == "":
            return None
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            print("Por favor, ingrese un número entero válido o deje vacio.")


def entrada_cadena(prompt, permite_vacios=False):
    while True:
        value = input(prompt).strip()
        if permite_vacios and value == "":
            return None
        if value:
            return value
        print("Entrada invalida . Intente de nuevo.")

def conectad_db():
    global db_manager
    db_manager = DatabaseManager()
    uri = os.getenv("MONGODB_URI")
    
    if uri:
        db_manager.uri = uri
    
    if db_manager.conectar("modelo_pacientes","coleccion1"):
        return True
    else:
        return False

def main():

    global db_manager
    
    print("Aplicación: Sistema de consulta de pacientes + ML (MVP)")
    path = input(f"Ingrese la ruta del archivo excel : ").strip() or DATA_PATH

    try:
        df = load_excel(path)
    except Exception as e:
        print(f"❌ Error al cargar el archivo: {e}")
        return

    columnas_requeridas = FEATURE_COLUMNS + \
        [TARGET_COLUMN, "Diagnóstico", "Sexo", "Edad", "Número de Leucocitos al inicio"]
    try:
        ensure_columns(df, columnas_requeridas)
    except Exception as e:
        print(f"Error en el dataframe: {e}")
        return
    
    modelo = None  # Variable para almacenar el modelo entrenado o cargado
    
      # Pregunta si desea conectar a MongoDB
    print("\n" + "=" * 60)
    conectar = input("¿Desea conectar con MongoDB para guardar clasificaciones? (s/n): ").strip().lower()
    if conectar == "s":
        print("Conectando a Base de datos...")
        conectad_db()
    print("=" * 60)

    while True:
        print("\n" + "=" * 60)
        print("Opciones:")
        print("1. Ver distribución por diagnóstico")
        print("2. Ver edad promedio por diagnóstico")
        print("3. Búsqueda por criterio exacta de pacientes")
        print("4. Búsqueda de pacientes similares")
        print("5. Clasificar pacientes")
        print("6. Ver pacientes guardados en BD")
        print("7. Ver estadísticas de clasificación")
        print("8. Entrenar modelo ERM")
        print("9. Predecir ERM de paciente")
        print("10. Salir")
        print("=" * 60)

        opcion = input("Seleccione una opción (1-10): ")

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
                print("⚠️  No se encontraron pacientes similares.")
            else:
                print(resultado.to_string(index=False))
        elif opcion == "5":
            print("\n⏳ Clasificando pacientes...")
            try:
                df_clasificado = clasificar_pacientes(df)
                mostrar_resumen_clasificacion(df_clasificado)
                
                if db_manager and db_manager.connected:
                    guardar = input("¿Desea guardar los pacientes clasificados en la base de datos? (s/n): ").strip().lower()
                    
                    if guardar == "s":
                        conectad_db()
                        print("⏳ Guardando en base de datos...")
                        
                        try:
                        
                            pacientes = preparar_pacientes_para_bd(df_clasificado)
                            print("\n📋 Ejemplo de dato que se guardará:")
                            
                            if pacientes:
                                primer_paciente = pacientes[0]
                                for clave, valor in primer_paciente.items():
                                    print(f"  • {clave}: {valor}")
                            
                            cantidad = db_manager.guardar_pacientes_batch(pacientes)
                        
                            if cantidad > 0:
                                print(f"✅ Se guardaron {cantidad} pacientes en la base de datos.")
                                print("   Columnas guardadas:")
                                print("   • Edad")
                                print("   • Sexo")
                                print("   • Número de Leucocitos al inicio")
                                print("   • Riesgo calculado")
                                print("   • Tipo leucemia (B, T o M)")
                                print("   • Número de blastos")
                                df = df_clasificado
                        except Exception as e:
                            print(f"❌ Error al guardar en BD: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        df = df_clasificado
                        print("✅ Clasificación completada (sin guardar en BD).")                            
                else:
                    df = df_clasificado
                    if db_manager is None:
                        print("⚠️  MongoDB no está conectado. Los datos no se guardaron.")
                    df = df_clasificado
            except Exception as e:
                print(f"❌ Error durante la clasificación de pacientes: {e}")
                import traceback
                traceback.print_exc()
        
        elif opcion == "6":
            
            if not db_manager or not db_manager.connected:
                print("❌ No hay conexión a la BD")
                continue
            
            print("\n" + "=" * 60)
            print("PACIENTES EN BASE DE DATOS")
            print("=" * 60)
            
            pacientes = db_manager.obtener_pacientes()
            
            if not pacientes.empty:
                print(pacientes.to_string(index=False))
            else:
                print("No se encontraron pacientes en la base de datos.")
                
        elif opcion == "7":
            
            if not db_manager or not db_manager.connected:
                print("❌ No hay conexión a la BD")
                continue
            
            stats = db_manager.obtener_estadisticas()
            if stats:
                print("\n" + "=" * 60)
                print("ESTADÍSTICAS DE CLASIFICACIÓN")
                print("=" * 60)
                print(f"Total de pacientes: {stats['total']}")
                print(f"  • Riesgo alto: {stats['riesgo_alto']} ({stats['porcentaje_alto']:.1f}%)")
                print(f"  • Riesgo estándar: {stats['riesgo_estandar']} ({stats['porcentaje_estandar']:.1f}%)")
                print("=" * 60)
        
        elif opcion == "8":
            
            print("\n⏳ Entrenando modelo ERM...")
            
            if not db_manager or not db_manager.connected:
                print("❌ Necesitas conectar a MongoDB primero")
                continue
            
            print("\nOpciones:")
            print("1. Entrenar nuevo modelo")
            print("2. Cargar modelo existente")
            print("3. Hacer predicción")
            
            opcion_modelo = input("Seleccione una opción (1-3): ")
            
            if opcion_modelo == "1":
                print("\n⏳ Entrenando nuevo modelo...")
                modelo_ml = ModeloPredictorEstadoPaciente()
                if modelo_ml.pipeline_completo(db_manager):
                    print("✅ Modelo entrenado y guardado exitosamente.")
                else:
                    print("❌ Error al entrenar el modelo.")
                    
            elif opcion_modelo == "2":
                print("\n⏳ Cargando modelo existente...")
                modelo_ml = ModeloPredictorEstadoPaciente()
                ruta = os.path.join(os.path.dirname(__file__), "..", "modelos", "modelo_predictor_estado.pkl")
                
                if modelo_ml.cargar(ruta):
                    print("✅ Modelo cargado exitosamente.")
                else:
                    print("❌ Error al cargar el modelo.")
                    
            elif opcion_modelo == "3":
                if 'modelo_ml' not in locals() or modelo_ml.modelo is None:
                    print("❌ No hay modelo disponible. Entrena o carga un modelo primero.")
                else:
                    
                    print("\n" + "=" * 60)
                    print("PREDICCIÓN DE ESTADO DEL PACIENTE")
                    print("=" * 60)
                    
                    try:
                        
                        print("Ingrese los datos del paciente para la predicción:")

                        edad = entrada_numero("Edad: ")
                        sexo = entrada_cadena("Sexo (M/F): ").upper()
                        leucocitos = entrada_numero("Número de Leucocitos al inicio: ")
                        riesgo = entrada_cadena("Riesgo calculado (Riesgo alto/Riesgo estandar): ")
                        tipo_leucemia = entrada_cadena("Tipo leucemia (B/T/M): ").upper()
                        blastos = entrada_numero("Número de blastos: ")
                        cariotipo = entrada_cadena("Clasificación cariotipo (Anormal/No detectado): ")
                        biologia = entrada_cadena("Biología molecular (Favorable/Desfavorable/Negativo): ")
                        gate = entrada_numero("GATE Inmunofenotipo (0-100): ")
                        resistencia = entrada_cadena("Resistencia al tratamiento (True/False): ").lower() == "true"
                        
                        datos_paciente = pd.dataFrame({
                            "Edad": [edad],
                            "Sexo": [sexo],
                            "Número de Leucocitos al inicio": [leucocitos],
                            "Riesgo calculado": [riesgo],
                            "Tipo leucemia (B/T/M)": [tipo_leucemia],
                            "Número de blastos": [blastos],
                            "Clasificación cariotipo (Anormal/No detectado)": [cariotipo],
                            "Biología molecular (Favorable/Desfavorable/Negativo)": [biologia],
                            "GATE Inmunofenotipo (0-100)": [gate],
                            "Resistencia al tratamiento (True/False)": [resistencia]
                        })
                        
                        print("\n⏳ Realizando predicción...")
                        prediccion = modelo_ml.predecir(datos_paciente)
                        
                        if prediccion:
                            print("\n" + "=" * 60)
                            print("RESULTADO DE LA PREDICCIÓN")
                            print("=" * 60)
                            print(f"\n🔮 Estado predicho: {prediccion['estado_predicho']}")
                            print(f"   Confianza: {prediccion['confianza']:.2%}")
                            
                            print(f"\n📊 Probabilidades por clase:")
                            
                            for clase, prob in sorted(
                                prediccion['probabilidades'].items(),
                                key=lambda x: x[1],
                                reverse=True
                            ):
                                barra = "█" * int(prob * 50)
                                print(f"   {clase:20} {barra} {prob:.2%}")
                            
                            print("\n" + "=" * 60)
                        else:
                            print("❌ No se pudo realizar la predicción.")
                            
                    except Exception as e:
                        print(f"❌ Error en la entrada de datos: {e}")
                        import traceback
                        traceback.print_exc()
        
        elif opcion == "9":
            
            print(" Entrenando modelo ERM...")
            try:
                modelo, reporte = entrenarmodelo_y_evaluar(df)
                guardar_modelo(modelo)
                print("✅ Modelo entrenado y guardado exitosamente.")
            except Exception as e:
                print(f"❌ Error al entrenar el modelo: {e}")
        
        elif opcion == "10":
            print("\n👋 Saliendo de la aplicación. ¡Hasta luego!")
            
            if db_manager and db_manager.connected:
                db_manager.desconectar()            
            break
        else:
            print("❌ Opción inválida. Seleccione entre 1 y 10.")


if __name__ == "__main__":
    main()
