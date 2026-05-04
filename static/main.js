// ============================================================================
// CONFIGURACIÓN
// ============================================================================
// Usar window.location.origin para que funcione en cualquier lugar
// (localhost:8000, Render, etc.)
const API_BASE = window.location.origin;

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
// ============================================================================
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
        
        // Si es el tab de pacientes, recargar la tabla
        if (tabName === 'tab-pacientes') {
            cargarPacientes();
            document.getElementById('filtro-pacientes').value = ''; // Limpiar filtro
        }
    });
});

// ============================================================================
// EVENTO: FILTRO DE BÚSQUEDA
// ============================================================================

document.getElementById('filtro-pacientes').addEventListener('input', function(e) {
    const filtro = e.target.value.trim();
    console.log('🔎 Aplicando filtro:', filtro || 'vacío - mostrando todos');
    
    if (filtro === '') {
        // Si está vacío, mostrar todos los pacientes en memoria
        mostrarPacientes(pacientesEnMemoria);
    } else {
        // Filtrar en memoria
        const resultado = pacientesEnMemoria.filter(p => 
            p.id.includes(filtro)
        );
        mostrarPacientes(resultado);
    }
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
            
            // Recargar tabla de pacientes y limpiar filtro
            setTimeout(() => {
                document.getElementById('filtro-pacientes').value = '';
                cargarPacientes();
            }, 1000);
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
// FUNCIÓN: CARGAR Y MOSTRAR PACIENTES
// ============================================================================

let pacientesEnMemoria = []; // Guardar todos los pacientes para filtrado local

async function cargarPacientes(filtro = "") {
    console.log('🔄 Iniciando carga de pacientes...');
    console.log('📍 API_BASE:', API_BASE);
    console.log('🔎 Filtro:', filtro || 'ninguno');
    
    try {
        const url = filtro.trim() 
            ? `${API_BASE}/api/pacientes?filtro=${encodeURIComponent(filtro)}` 
            : `${API_BASE}/api/pacientes`;
        
        console.log('📡 Fetching:', url);
        
        const response = await fetch(url);
        console.log('✅ Response status:', response.status);
        
        const data = await response.json();
        console.log('📦 Data received:', data);

        if (data.status === 'success') {
            pacientesEnMemoria = data.pacientes; // Guardar en memoria
            mostrarPacientes(data.pacientes);
        } else {
            console.error('❌ Error en respuesta API:', data);
            mostrarError('Error en respuesta del servidor');
        }
    } catch (error) {
        console.error('❌ Error al cargar pacientes:', error);
        mostrarError('Error al cargar los pacientes: ' + error.message);
    }
}

function mostrarPacientes(pacientes) {
    const tbody = document.getElementById('tabla-pacientes-body');
    const contador = document.getElementById('contador-pacientes');
    
    console.log('👥 Total pacientes a mostrar:', pacientes.length);
    
    if (pacientes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: #999;">
                    No hay pacientes registrados
                </td>
            </tr>
        `;
        contador.textContent = 'Total: 0 pacientes';
        return;
    }

    // Limpiar tabla
    tbody.innerHTML = '';

    // Agregar cada paciente
    pacientes.forEach(paciente => {
        const fecha = new Date(paciente.fecha_registro);
        const fechaFormato = fecha.toLocaleDateString('es-ES', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><code style="font-weight: bold;">${paciente.id.substring(0, 12)}...</code></td>
            <td>
                <span style="
                    padding: 4px 8px; 
                    border-radius: 4px;
                    font-size: 0.9em;
                    font-weight: 500;
                    ${paciente.estado === 'Tratamiento' ? 'background: #c8e6c9; color: #2e7d32;' : 
                      paciente.estado === 'Defunción' ? 'background: #ffcdd2; color: #c62828;' :
                      paciente.estado === 'Cuidados paliativos' ? 'background: #ffe0b2; color: #e65100;' :
                      'background: #b3e5fc; color: #01579b;'}
                ">
                    ${paciente.estado}
                </span>
            </td>
            <td>${fechaFormato}</td>
            <td>
                <button 
                    class="btn-erm" 
                    onclick="agregarERM('${paciente.id}')"
                    style="
                        padding: 6px 12px;
                        background-color: #007bff;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 0.9em;
                        font-weight: 500;
                    "
                    onmouseover="this.style.backgroundColor='#0056b3'"
                    onmouseout="this.style.backgroundColor='#007bff'"
                >
                    Agregar ERM
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });

    contador.textContent = `Total: ${pacientes.length} paciente${pacientes.length !== 1 ? 's' : ''}`;
    console.log('✅ Tabla actualizada correctamente');
}

function mostrarError(mensaje) {
    const tbody = document.getElementById('tabla-pacientes-body');
    tbody.innerHTML = `
        <tr>
            <td colspan="4" style="text-align: center; color: #e74c3c;">
                ❌ ${mensaje}
            </td>
        </tr>
    `;
}

// ============================================================================
// FUNCIÓN: AGREGAR ERM
// ============================================================================

function agregarERM(pacienteId) {
    console.log('📝 Agregando ERM para paciente:', pacienteId);
    alert(`Agregar ERM para paciente: ${pacienteId}`);
    // TODO: Implementar la lógica para agregar ERM
}

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

console.log('✅ Interfaz web cargada correctamente');

// Cargar pacientes al abrir la aplicación
document.addEventListener('DOMContentLoaded', cargarPacientes);