// ============================================================================
// CONFIGURACIÓN
// ============================================================================

const API_BASE = "http://localhost:8000";

// ============================================================================
// FUNCIONES AUXILIARES
// ============================================================================

function mostrarResultado(elementId, estado, titulo, contenido) {
    const elemento = document.getElementById(elementId);
    elemento.innerHTML = `<h3>${titulo}</h3><p>${contenido}</p>`;
    elemento.className = `resultado show ${estado}`;
}

function mostrarResultadoObjeto(elementId, estado, titulo, objeto) {
    const elemento = document.getElementById(elementId);
    let html = `<h3>${titulo}</h3>`;

    for (const [clave, valor] of Object.entries(objeto)) {
        if (typeof valor === 'object') {
            html += `<div class="metric"><strong>${clave}:</strong>`;
            for (const [k, v] of Object.entries(valor)) {
                html += `<br>&nbsp;&nbsp;${k}: ${v}`;
            }
            html += `</div>`;
        } else {
            html += `<div class="metric"><strong>${clave}:</strong> ${valor}</div>`;
        }
    }

    elemento.innerHTML = html;
    elemento.className = `resultado show ${estado}`;
}

function ocultarResultado(elementId) {
    const elemento = document.getElementById(elementId);
    elemento.className = 'resultado';
}

// ============================================================================
// TABS
// ============================================================================

document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', function () {
        const tabName = this.getAttribute('data-tab');

        // Desactivar todos los tabs
        document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

        // Activar tab seleccionado
        this.classList.add('active');
        document.getElementById(tabName).classList.add('active');
    });
});

// ============================================================================
// FUNCIÓN 1: CARGAR ARCHIVO
// ============================================================================

document.getElementById('btn-cargar').addEventListener('click', async function () {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];

    if (!file) {
        mostrarResultado(
            'resultado-carga',
            'error',
            '❌ Error',
            'Por favor selecciona un archivo'
        );
        return;
    }

    mostrarResultado(
        'resultado-carga',
        'loading',
        '⏳ Procesando...',
        'Cargando archivo a la base de datos...'
    );

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/api/cargar_excel`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            mostrarResultadoObjeto(
                'resultado-carga',
                'success',
                '✅ Archivo cargado exitosamente',
                {
                    'Registros guardados': data.registros_guardados,
                    'Mensaje': data.mensaje
                }
            );
            fileInput.value = '';
        } else {
            mostrarResultado(
                'resultado-carga',
                'error',
                '❌ Error',
                data.mensaje || 'Error desconocido'
            );
        }
    } catch (error) {
        mostrarResultado(
            'resultado-carga',
            'error',
            '❌ Error de conexión',
            `No se puede conectar al servidor: ${error.message}`
        );
    }
});

// ============================================================================
// FUNCIÓN 2: CREAR PACIENTE
// ============================================================================

document.getElementById('form-paciente').addEventListener('submit', async function (e) {
    e.preventDefault();

    mostrarResultado(
        'resultado-paciente',
        'loading',
        '⏳ Guardando...',
        'Guardando el paciente en la base de datos...'
    );

    try {
        // Obtener datos del formulario
        const formData = new FormData(this);
        const datos = Object.fromEntries(formData);

        // Convertir booleano
        datos['Resistencia al tratamiento'] = datos['Resistencia al tratamiento'] === 'true';
        
        // Convertir Número de blastos de porcentaje (0-100) a decimal (0-1)
        if (datos['Número de blastos']) {
            datos['Número de blastos'] = parseFloat(datos['Número de blastos']) / 100;
        }

        // Enviar POST
        const response = await fetch(`${API_BASE}/api/paciente/nuevo`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(datos)
        });

        const data = await response.json();

        if (data.status === 'success') {
            let mostrarObjeto = {
                'Edad': datos.Edad,
                'Sexo': datos.Sexo,
                'Riesgo Calculado': data.riesgo_calculado || 'No disponible',
                'Modelo Entrenado': data.modelo_entrenado ? 'Sí' : 'No'
            };
            
            // Si hay predicción natural, agregarla
            if (data.prediccion_natural) {
                mostrarObjeto['Predicción Clínica'] = data.prediccion_natural;
            }
            
            // Si hay mensaje adicional
            if (data.mensaje) {
                mostrarObjeto['Mensaje'] = data.mensaje;
            }
            
            mostrarResultadoObjeto(
                'resultado-paciente',
                'success',
                '✅ Paciente guardado exitosamente',
                mostrarObjeto
            );
            document.getElementById('form-paciente').reset();
        } else {
            mostrarResultado(
                'resultado-paciente',
                'error',
                '❌ Error',
                data.mensaje || 'Error desconocido'
            );
        }
    } catch (error) {
        mostrarResultado(
            'resultado-paciente',
            'error',
            '❌ Error de conexión',
            `No se puede conectar al servidor: ${error.message}`
        );
    }
});

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

console.log('✅ Interfaz web cargada correctamente');