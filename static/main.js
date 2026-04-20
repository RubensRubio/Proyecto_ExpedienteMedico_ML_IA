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
            mostrarResultadoObjeto(
                'resultado-paciente',
                'success',
                '✅ Paciente guardado exitosamente',
                {
                    'Edad': datos.Edad,
                    'Sexo': datos.Sexo,
                    'Estado': 'Pendiente de predicción',
                    'Mensaje': data.mensaje
                }
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
// FUNCIÓN 3: ENTRENAR MODELO
// ============================================================================

document.getElementById('btn-entrenar').addEventListener('click', async function () {
    this.disabled = true;

    mostrarResultado(
        'resultado-entrenamiento',
        'loading',
        '🤖 Entrenando...',
        'Esto puede tomar algunos minutos...'
    );

    try {
        const response = await fetch(`${API_BASE}/api/entrenar-modelo`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.status === 'success') {
            mostrarResultadoObjeto(
                'resultado-entrenamiento',
                'success',
                '✅ Modelo entrenado exitosamente',
                data.metricas
            );
        } else {
            mostrarResultado(
                'resultado-entrenamiento',
                'error',
                '❌ Error',
                data.mensaje || 'Error desconocido'
            );
        }
    } catch (error) {
        mostrarResultado(
            'resultado-entrenamiento',
            'error',
            '❌ Error de conexión',
            `No se puede conectar al servidor: ${error.message}`
        );
    } finally {
        this.disabled = false;
    }
});

// ============================================================================
// FUNCIÓN 4: REALIZAR PREDICCIÓN
// ============================================================================

document.getElementById('btn-predecir').addEventListener('click', async function () {
    // Obtener datos del formulario del paciente
    const formData = new FormData(document.getElementById('form-paciente'));

    if (formData.entries().length === 0) {
        mostrarResultado(
            'resultado-prediccion',
            'error',
            '❌ Error',
            'Por favor completa el formulario de paciente primero'
        );
        return;
    }

    const datos = Object.fromEntries(formData);
    datos['Resistencia al tratamiento'] = datos['Resistencia al tratamiento'] === 'true';

    mostrarResultado(
        'resultado-prediccion',
        'loading',
        '🎯 Realizando predicción...',
        'Analizando datos del paciente...'
    );

    try {
        const response = await fetch(`${API_BASE}/api/prediccion`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(datos)
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Mostrar respuesta natural
            const elemento = document.getElementById('resultado-prediccion');
            elemento.innerHTML = `
        <h3 style="color: #2e7d32; margin-bottom: 15px;">✅ Resultado del Análisis</h3>
        <div style="background: #f0f8f0; padding: 15px; border-radius: 5px; border-left: 5px solid #4caf50;">
            <p style="white-space: pre-wrap; line-height: 1.8; color: #1b5e20;">
                ${data.respuesta_natural}
            </p>
        </div>
    `;
            elemento.className = 'resultado show success';
            // mostrarResultadoObjeto(
            //     'resultado-prediccion',
            //     'success',
            //     `🎯 Predicción: ${data.prediccion}`,
            //     {
            //         'Predicción': data.prediccion,
            //         'Confianza': data.confianza,
            //         'Probabilidades': data.probabilidades
            //     }
            // );
        } else {
            mostrarResultado(
                'resultado-prediccion',
                'error',
                '❌ Error',
                data.mensaje || 'Error desconocido'
            );
        }
    } catch (error) {
        mostrarResultado(
            'resultado-prediccion',
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