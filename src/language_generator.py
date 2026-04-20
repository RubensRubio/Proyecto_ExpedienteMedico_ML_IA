# src/language_generator.py

def generar_respuesta_natural(prediccion, confianza, probabilidades, datos_paciente):
    """
    Convierte una predicción ML a lenguaje natural explicativo.
    
    Args:
        prediccion: str - Estado predicho (ej: "Tratamiento")
        confianza: float - Nivel de confianza (0 a 1)
        probabilidades: dict - Probabilidades por clase
        datos_paciente: dict - Datos clínicos del paciente
    
    Returns:
        str - Respuesta en lenguaje natural
    """
    
    edad = datos_paciente.get("Edad", "desconocida")
    leucocitos = datos_paciente.get("Número de Leucocitos al inicio", 0)
    cariotipo = datos_paciente.get("Clasificación cariotipo", "")
    infiltracion = datos_paciente.get("Tipo infiltración", "")
    resistencia = datos_paciente.get("Resistencia al tratamiento", False)
    tipo_leucemia = datos_paciente.get("Tipo leucemia", "")
    biologia = datos_paciente.get("Biología molecular", "")
    
    # Determinar factores de riesgo
    factores = []
    
    if leucocitos > 100:
        factores.append(f"nivel extremadamente alto de leucocitos ({leucocitos})")
    elif leucocitos > 50:
        factores.append(f"nivel muy alto de leucocitos ({leucocitos})")
    elif leucocitos > 20:
        factores.append(f"nivel elevado de leucocitos ({leucocitos})")
    
    if cariotipo == "Anormal":
        factores.append("clasificación cariotipo anormal")
    
    if infiltracion == "Alta infiltración":
        factores.append("alta infiltración de células malignas")
    elif infiltracion == "Moderada moderada":
        factores.append("infiltración moderada")
    
    if resistencia:
        factores.append("resistencia al tratamiento")
    
    if biologia == "Desfavorable":
        factores.append("biología molecular desfavorable")
    
    # Construir respuesta
    factores_texto = ", ".join(factores) if factores else "factores clínicos relevantes"
    
    confianza_pct = f"{confianza:.0%}"
    
    # Respuestas personalizadas por estado
    if prediccion == "Tratamiento":
        respuesta = (
            f"📋 DIAGNÓSTICO CLÍNICO:\n\n"
            f"Basado en la edad ({edad} años), {factores_texto}, "
            f"el modelo predice con {confianza_pct} de confianza que "
            f"este paciente REQUIERE TRATAMIENTO ACTIVO.\n\n"
            f"🏥 RECOMENDACIÓN: Se sugiere proceder inmediatamente con el protocolo de tratamiento. "
            f"Monitor continuo y seguimiento oncológico especializado es esencial."
        )
    elif prediccion == "Defunción":
        respuesta = (
            f"📋 DIAGNÓSTICO CLÍNICO:\n\n"
            f"Considerando la edad ({edad} años) y {factores_texto}, "
            f"el modelo indica con {confianza_pct} de confianza un PRONÓSTICO CRÍTICO. "
            f"Este paciente presenta características asociadas con alto riesgo de desenlace fatal.\n\n"
            f"🏥 RECOMENDACIÓN: Se recomienda enfoque intensivo en cuidados paliativos, "
            f"comunicación familiar transparente y evaluación multidisciplinaria urgente."
        )
    elif prediccion == "Cuidados paliativos":
        respuesta = (
            f"📋 DIAGNÓSTICO CLÍNICO:\n\n"
            f"Con edad ({edad} años) y {factores_texto}, "
            f"el modelo predice ({confianza_pct} confianza) que el paciente es candidato a "
            f"TRANSICIÓN A CUIDADOS PALIATIVOS.\n\n"
            f"🏥 RECOMENDACIÓN: Se sugiere enfoque multidisciplinario en confort, dignidad y calidad de vida. "
            f"Consulta con equipo paliativo y apoyo psicosocial."
        )
    else:  # Otra enfermedad
        respuesta = (
            f"📋 DIAGNÓSTICO CLÍNICO:\n\n"
            f"El análisis del paciente de {edad} años con {factores_texto} "
            f"sugiere ({confianza_pct} confianza) que puede presentar OTRA CONDICIÓN CLÍNICA diferente a leucemia.\n\n"
            f"🏥 RECOMENDACIÓN: Se recomienda investigación adicional y consulta con especialistas "
            f"para descartar diagnósticos alternativos."
        )
    
    return respuesta
