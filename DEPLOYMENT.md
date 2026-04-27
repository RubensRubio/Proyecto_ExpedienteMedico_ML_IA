# 🏥 Asistente Clínico - Predicción de Estado del Paciente

Sistema de predicción de estado clínico basado en Machine Learning. Permite cargar datos de pacientes y generar predicciones clínicas automáticas con reportes en lenguaje natural.

## 🚀 Features

- ✅ Carga masiva de pacientes desde Excel/CSV
- ✅ Registro individual de pacientes
- ✅ Entrenamiento automático del modelo con cada nuevo paciente
- ✅ Predicciones clínicas con confianza porcentual
- ✅ Reportes en lenguaje natural en español
- ✅ Interfaz web intuitiva con tabs
- ✅ Base de datos MongoDB Atlas

## 🛠️ Tecnologías

**Backend:**
- FastAPI (Python)
- scikit-learn (Machine Learning)
- pandas (Procesamiento de datos)
- MongoDB (Base de datos)

**Frontend:**
- HTML5/CSS3/JavaScript
- Bootstrap (Estilos)

## 📋 Requisitos

- Python 3.13+
- MongoDB Atlas (gratuito en https://www.mongodb.com/cloud/atlas)
- pip

## 🔧 Instalación Local

### 1. Clonar repositorio
```bash
git clone https://github.com/tuusuario/asistente-clinico.git
cd asistente-clinico/paciente-search
```

### 2. Crear entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env y agregar tu MongoDB URI
# Obtener de: https://www.mongodb.com/cloud/atlas
```

### 5. Ejecutar servidor
```bash
cd paciente-search
python3 -m uvicorn src.api:app --reload --port 8000
```

Acceder a: http://localhost:8000

## 🌐 Despliegue en Render (Sencillo)

### Opción 1: Automático desde GitHub

1. **Sube código a GitHub:**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Crear cuenta en Render:**
   - Ve a https://render.com
   - Regístrate con GitHub

3. **Crear nuevo Web Service:**
   - Click en "New" → "Web Service"
   - Conectar tu repositorio de GitHub
   - Configurar:
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `uvicorn src.api:app --host 0.0.0.0 --port 8080`
   - Agregar variables de entorno:
     - `MONGODB_URI`: Tu URI de MongoDB Atlas

4. **Deploy automático:**
   - Render desplegará automáticamente con cada push a GitHub

### Opción 2: Desde Archivo YAML

El archivo `render.yaml` está preconfigurado. Solo necesitas:
1. Conectar tu repo a Render
2. Agregar variable de entorno `MONGODB_URI`
3. Hacer push a GitHub

---

## 📚 Estructura del Proyecto

```
paciente-search/
├── src/
│   ├── api.py                      # Endpoints FastAPI
│   ├── ml_model_pacientes.py       # Modelo ML
│   ├── database.py                 # Conexión MongoDB
│   ├── language_generator.py       # Reportes en lenguaje natural
│   ├── risk_classifier.py          # Clasificación de riesgo
│   ├── data_loader.py              # Carga de Excel
│   └── .env                        # Variables de entorno
├── templates/
│   └── index.html                  # UI principal
├── static/
│   ├── main.js                     # Lógica del navegador
│   └── style.css                   # Estilos
├── modelos/                        # Modelos ML entrenados
├── requirements.txt                # Dependencias Python
├── render.yaml                     # Configuración Render
├── build.sh                        # Script de build
└── README.md                       # Este archivo
```

## 🔌 API Endpoints

### POST `/api/cargar_excel`
Cargar archivo Excel con datos de pacientes
- **Body:** FormData con archivo

### POST `/api/paciente/nuevo`
Crear nuevo paciente y generar predicción
- **Body:** JSON con datos del paciente

### POST `/api/entrenar_modelo`
Entrenar modelo manualmente
- **Body:** (Vacío)

### POST `/api/prediccion`
Realizar predicción para un paciente
- **Body:** JSON con datos clínicos

## 👤 Usuarios de Prueba

Para probar el formulario:
- **Edad:** 50
- **Sexo:** Masculino/Femenino
- **Leucocitos al inicio:** 45000
- **Blastos (%):** 75
- **Cariotipo:** Normal
- **GATE Inmunofenotipo:** 2.8

## 🐛 Troubleshooting

**"No se puede conectar a MongoDB"**
- Verificar MONGODB_URI en .env
- Asegurar que MongoDB Atlas está activo
- Whitelist IP en MongoDB Atlas

**"Modelo no entrenado"**
- Se requieren mínimo 10 pacientes
- Los primeros pacientes son de entrenamiento
- El modelo se reentrena automáticamente

## 📝 Licencia

MIT License - Libre para usar y modificar

## 📞 Contacto

Para más información o reporte de bugs, contactar al equipo de desarrollo.

---

**Última actualización:** 26 de abril de 2026
