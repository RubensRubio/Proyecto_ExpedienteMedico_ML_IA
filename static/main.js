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
        
        // Si es el tab de chat, inicializar si no está activo
        if (tabName === 'tab-chat') {
            if (!chatState.conversationActive) {
                initializeChat();
            }
        }
    });
});

// ============================================================================
// EVENTO: FILTRO DE BÚSQUEDA
// ============================================================================

document.getElementById('filtro-pacientes').addEventListener('input', function(e) {
    const filtro = e.target.value.trim();
    console.log('🔎 Aplicando filtro:', filtro || 'vacío - mostrando todos');
    
    let resultado = pacientesEnMemoria;
    
    if (filtro !== '') {
        // Filtrar en memoria
        resultado = pacientesEnMemoria.filter(p => 
            p.id.includes(filtro)
        );
    }
    
    // Actualizar paginación con resultados filtrados
    actualizarPaginacion(resultado);
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
        
        // Nota: El número de blastos ya se captura en escala 0-100 (ej: 10, 25, 42)
        // No se requiere conversión adicional

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
let paginaActual = 1;
let registrosPorPagina = 25;
let pacientesFiltrados = [];

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
            paginaActual = 1; // Reset a primera página
            actualizarPaginacion(data.pacientes);
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
    const contador = document.querySelector('.pagination-info');
    
    console.log('👥 Total pacientes a mostrar:', pacientes.length);
    
    if (pacientes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: #999;">
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
        
        // Formatear fecha del tratamiento si existe
        const fechaTratamiento = paciente.fecha_tratamiento 
            ? new Date(paciente.fecha_tratamiento).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
              })
            : '-';
        
        // Determinar qué botón mostrar
        const tieneTratamiento = !!paciente.fecha_tratamiento;
        const botonAccion = tieneTratamiento 
            ? `<button 
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
                    Ver ERM
                </button>`
            : `<button 
                    class="btn-tratamiento" 
                    onclick="agregarTratamiento('${paciente.id}')"
                    style="
                        padding: 6px 12px;
                        background-color: #27ae60;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 0.9em;
                        font-weight: 500;
                    "
                    onmouseover="this.style.backgroundColor='#1e8449'"
                    onmouseout="this.style.backgroundColor='#27ae60'"
                >
                    Agregar Tratamiento
                </button>`;

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><code style="font-weight: bold;">${paciente.id.substring(0, 12)}...</code></td>
            <td>${paciente.tipo_leucemia || 'N/A'}</td>
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
            <td>
                <span style="
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.9em;
                    font-weight: 500;
                    ${paciente.estatus_tratamiento === 'Proceso' ? 'background: #fff3cd; color: #856404;' :
                      paciente.estatus_tratamiento === 'Completado' ? 'background: #d4edda; color: #155724;' :
                      'background: #e2e3e5; color: #383d41;'}
                ">
                    ${paciente.estatus_tratamiento || '-'}
                </span>
            </td>
            <td>${fechaTratamiento}</td>
            <td>${fechaFormato}</td>
            <td>${botonAccion}</td>
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
            <td colspan="7" style="text-align: center; color: #e74c3c;">
                ❌ ${mensaje}
            </td>
        </tr>
    `;
}

// FUNCIONES: PAGINACIÓN
// ============================================================================

function actualizarPaginacion(pacientes) {
    pacientesFiltrados = pacientes;
    paginaActual = 1;
    
    const totalPaginas = Math.ceil(pacientes.length / registrosPorPagina);
    
    mostrarPagina(1);
    generarBotonesPagina(totalPaginas);
    
    // Actualizar contador
    const inicio = (paginaActual - 1) * registrosPorPagina + 1;
    const fin = Math.min(paginaActual * registrosPorPagina, pacientes.length);
    const contador = document.querySelector('.pagination-info');
    if (contador) {
        contador.textContent = `Mostrando ${inicio} a ${fin} de ${pacientes.length} pacientes`;
    }
}

function mostrarPagina(numero) {
    const totalPaginas = Math.ceil(pacientesFiltrados.length / registrosPorPagina);
    
    if (numero < 1 || numero > totalPaginas) return;
    
    paginaActual = numero;
    
    const inicio = (numero - 1) * registrosPorPagina;
    const fin = inicio + registrosPorPagina;
    const pacientesPagina = pacientesFiltrados.slice(inicio, fin);
    
    mostrarPacientes(pacientesPagina);
    
    // Actualizar contador
    const inicio2 = inicio + 1;
    const fin2 = Math.min(numero * registrosPorPagina, pacientesFiltrados.length);
    const contador = document.querySelector('.pagination-info');
    if (contador) {
        contador.textContent = `Mostrando ${inicio2} a ${fin2} de ${pacientesFiltrados.length} pacientes`;
    }
    
    // Deshabilitar botones según corresponda
    const btnAnterior = document.querySelector('button[onclick="cambiarPagina(-1)"]');
    const btnSiguiente = document.querySelector('button[onclick="cambiarPagina(1)"]');
    
    if (btnAnterior) btnAnterior.disabled = numero === 1;
    if (btnSiguiente) btnSiguiente.disabled = numero === totalPaginas;
    
    // Resaltar página actual
    document.querySelectorAll('.page-button').forEach(btn => {
        btn.classList.remove('active');
        if (parseInt(btn.textContent) === numero) {
            btn.classList.add('active');
        }
    });
}

function cambiarPagina(direccion) {
    const nuevaPagina = paginaActual + direccion;
    const totalPaginas = Math.ceil(pacientesFiltrados.length / registrosPorPagina);
    
    if (nuevaPagina >= 1 && nuevaPagina <= totalPaginas) {
        mostrarPagina(nuevaPagina);
    }
}

function cambiarRegistrosPorPagina() {
    const selectElement = document.getElementById('registros-por-pagina');
    registrosPorPagina = parseInt(selectElement.value);
    actualizarPaginacion(pacientesFiltrados);
}

function generarBotonesPagina(totalPaginas) {
    const container = document.getElementById('paginacion-numeros');
    container.innerHTML = '';
    
    // Mostrar un máximo de 5 botones de página
    let inicio = Math.max(1, paginaActual - 2);
    let fin = Math.min(totalPaginas, paginaActual + 2);
    
    if (totalPaginas <= 5) {
        inicio = 1;
        fin = totalPaginas;
    }
    
    // Botón "Primera" si no estamos al inicio
    if (inicio > 1) {
        const btnPrimera = document.createElement('button');
        btnPrimera.className = 'page-button';
        btnPrimera.textContent = '1';
        btnPrimera.onclick = () => mostrarPagina(1);
        container.appendChild(btnPrimera);
        
        if (inicio > 2) {
            const puntos = document.createElement('span');
            puntos.textContent = '...';
            puntos.style.padding = '5px';
            container.appendChild(puntos);
        }
    }
    
    // Botones de página
    for (let i = inicio; i <= fin; i++) {
        const btn = document.createElement('button');
        btn.className = 'page-button' + (i === paginaActual ? ' active' : '');
        btn.textContent = i;
        btn.onclick = () => mostrarPagina(i);
        container.appendChild(btn);
    }
    
    // Botón "Última" si no estamos al final
    if (fin < totalPaginas) {
        if (fin < totalPaginas - 1) {
            const puntos = document.createElement('span');
            puntos.textContent = '...';
            puntos.style.padding = '5px';
            container.appendChild(puntos);
        }
        
        const btnUltima = document.createElement('button');
        btnUltima.className = 'page-button';
        btnUltima.textContent = totalPaginas;
        btnUltima.onclick = () => mostrarPagina(totalPaginas);
        container.appendChild(btnUltima);
    }
}

// FUNCIÓN: AGREGAR TRATAMIENTO
// ============================================================================

let tratamientoState = {
    conversationActive: false,
    currentQuestionIndex: 0,
    extractedData: {},
    pacienteId: null,
    questions: [
        {
            question: '¿Cuál es el protocolo de tratamiento? (Protocolo XV o Protocolo New York)',
            field: 'protocolo',
            options: ['Protocolo XV', 'Protocolo New York']
        },
        {
            question: '¿Cuál es la fase del tratamiento? (Inducción, Consolidación o Mantenimiento)',
            field: 'fase',
            options: ['Inducción', 'Consolidación', 'Mantenimiento']
        }
    ]
};

function agregarTratamiento(pacienteId) {
    console.log('💊 Abriendo chat de tratamiento para paciente:', pacienteId);
    abrirModalTratamiento(pacienteId);
}

function abrirModalTratamiento(pacienteId) {
    const modal = document.getElementById('modal-tratamiento');
    modal.style.display = 'flex';
    
    // Resetear estado del chat
    tratamientoState = {
        conversationActive: true,
        currentQuestionIndex: 0,
        extractedData: {},
        pacienteId: pacienteId,
        questions: [
            {
                question: '¿Cuál es el protocolo de tratamiento? (Protocolo XV o Protocolo New York)',
                field: 'protocolo',
                options: ['Protocolo XV', 'Protocolo New York']
            },
            {
                question: '¿Cuál es la fase del tratamiento? (Inducción, Consolidación o Mantenimiento)',
                field: 'fase',
                options: ['Inducción', 'Consolidación', 'Mantenimiento']
            }
        ]
    };
    
    // Limpiar mensajes
    const messagesDiv = document.getElementById('tratamiento-chat-messages');
    messagesDiv.innerHTML = `
        <div class="chat-message assistant">
            <div class="message-content">
                👋 Hola, voy a ayudarte a registrar el plan de tratamiento. Responde en lenguaje natural.
            </div>
        </div>
    `;
    
    // Hacer la primera pregunta
    hacerSiguientePreguntaTratamiento();
    
    // Limpiar input y enfocar
    document.getElementById('tratamiento-chat-input').value = '';
    document.getElementById('tratamiento-chat-input').focus();
    
    console.log('✅ Modal de tratamiento abierto para paciente:', pacienteId);
}

function hacerSiguientePreguntaTratamiento() {
    if (tratamientoState.currentQuestionIndex < tratamientoState.questions.length) {
        const pregunta = tratamientoState.questions[tratamientoState.currentQuestionIndex];
        addMessageTratamiento('assistant', pregunta.question);
    } else {
        finalizarChatTratamiento();
    }
}

function addMessageTratamiento(sender, text) {
    const messagesDiv = document.getElementById('tratamiento-chat-messages');
    const mensaje = document.createElement('div');
    mensaje.className = `chat-message ${sender}`;
    mensaje.innerHTML = `<div class="message-content">${text.replace(/\n/g, '<br>')}</div>`;
    messagesDiv.appendChild(mensaje);
    
    // Scroll al final
    const container = document.getElementById('tratamiento-chat-container');
    container.scrollTop = container.scrollHeight;
}

function enviarMensajeTratamiento() {
    const input = document.getElementById('tratamiento-chat-input');
    const mensaje = input.value.trim();
    
    if (!mensaje) return;
    
    // Mostrar mensaje del usuario
    addMessageTratamiento('user', mensaje);
    input.value = '';
    
    if (tratamientoState.currentQuestionIndex < tratamientoState.questions.length) {
        const pregunta = tratamientoState.questions[tratamientoState.currentQuestionIndex];
        const field = pregunta.field;
        
        // Extraer valor basado en opciones disponibles
        let valor = null;
        const mensajeLower = mensaje.toLowerCase();
        
        for (const opcion of pregunta.options) {
            if (mensajeLower.includes(opcion.toLowerCase())) {
                valor = opcion;
                break;
            }
        }
        
        if (!valor) {
            addMessageTratamiento('assistant', `❌ Por favor especifica una de estas opciones: ${pregunta.options.join(', ')}`);
        } else {
            tratamientoState.extractedData[field] = valor;
            addMessageTratamiento('assistant', `✅ ${field}: ${valor}`);
            
            tratamientoState.currentQuestionIndex++;
            
            // Esperar un poco antes de hacer la siguiente pregunta
            setTimeout(() => {
                hacerSiguientePreguntaTratamiento();
                document.getElementById('tratamiento-chat-input').focus();
            }, 500);
        }
    }
}

async function finalizarChatTratamiento() {
    const pacienteId = tratamientoState.pacienteId;
    const protocolo = tratamientoState.extractedData.protocolo;
    const fase = tratamientoState.extractedData.fase;
    
    if (!protocolo || !fase) {
        addMessageTratamiento('assistant', '❌ Error: No se completaron todos los datos. Por favor cierra e intenta de nuevo.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/tratamiento/guardar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                paciente_id: pacienteId,
                protocolo: protocolo,
                fase: fase
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            addMessageTratamiento('assistant', `✅ Plan de tratamiento guardado correctamente!\n\nProtocolo: ${protocolo}\nFase: ${fase}\n\nPuedes cerrar este modal.`);
            
            // Recargar tabla después de 2 segundos
            setTimeout(() => {
                cargarPacientes();
                cerrarModalTratamiento();
            }, 2000);
        } else {
            addMessageTratamiento('assistant', `❌ Error: ${data.message}`);
        }
    } catch (error) {
        console.error('Error:', error);
        addMessageTratamiento('assistant', `❌ Error al guardar: ${error.message}`);
    }
}

function cerrarModalTratamiento() {
    const modal = document.getElementById('modal-tratamiento');
    modal.style.display = 'none';
    tratamientoState.conversationActive = false;
    console.log('✅ Modal de tratamiento cerrado');
}

// ============================================================================
// FUNCIÓN: AGREGAR ERM (placeholder for future implementation)
// ============================================================================
function agregarERM(pacienteId) {
    alert('Función ERM en desarrollo...');
    console.log('📝 ERM para paciente:', pacienteId);
}

// ============================================================================
// CHAT ASISTENTE - STATE Y CONFIGURACIÓN
// ============================================================================

let chatState = {
    conversationActive: false,
    currentFieldIndex: 0,
    extractedData: {},
    fields: [
        { field: 'Edad', type: 'number', question: '¿Cuál es la edad del paciente? (entre 0 y 18 años)', validation: (v) => !isNaN(v) && v >= 0 && v <= 18 },
        { field: 'Sexo', type: 'option', question: '¿Cuál es el sexo del paciente? (M para Masculino, F para Femenino)', options: ['M', 'F'], validation: (v) => ['M', 'F'].includes(v.toUpperCase()) },
        { field: 'Número de Leucocitos al inicio', type: 'number', question: '¿Cuál es el número de leucocitos al inicio?', validation: (v) => !isNaN(v) && v > 0 },
        { field: 'Número de blastos', type: 'number', question: '¿Cuál es el porcentaje de blastos? (0-100)\n⚠️ DATO SENSIBLE: Este es un valor crítico. Por favor verifica que sea correcto.', validation: (v) => !isNaN(v) && v >= 0 && v <= 100, requiresConfirmation: true },
        { field: 'Tipo leucemia', type: 'option', question: '¿Cuál es el tipo de leucemia? (B, T o M)', options: ['B', 'T', 'M'], validation: (v) => ['B', 'T', 'M'].includes(v.toUpperCase()) },
        { field: 'Clasificación cariotipo', type: 'string', question: '¿Cuál es la clasificación cariotipo? (Puedes escribir el valor, "No detectado" o "No aplica")', validation: (v) => true },
        { field: 'Biología molecular', type: 'string', question: '¿Cuál es la biología molecular? (Puedes escribir el valor, "No detectado" o "No aplica")', validation: (v) => true },
        { field: 'GATE Inmunofenotipo', type: 'number', question: '¿Cuál es el GATE Inmunofenotipo?', validation: (v) => !isNaN(v) && v >= 0 },
        { field: 'Inmunofenotipo marcadores', type: 'isoform_markers', question: '¿Cuál es el Inmunofenotipo marcadores? (máximo 500 caracteres, este campo es obligatorio)', validation: (v) => v && v.length > 0 && v.length <= 500 },
        { field: 'Marcadores aberrantes', type: 'aberrant_markers', question: '¿Hay marcadores aberrantes? (Escribe el valor detectado o "No detectado")', validation: (v) => true }
    ]
};

// ============================================================================
// CHAT ASISTENTE - FUNCIONES
// ============================================================================

function initializeChat() {
    console.log('🤖 Inicializando chat...');
    chatState.conversationActive = true;
    chatState.currentFieldIndex = 0;
    chatState.extractedData = {};
    
    const messagesDiv = document.getElementById('chat-messages');
    messagesDiv.innerHTML = `
        <div class="chat-message assistant">
            <div class="message-content">
                👋 ¡Hola! Soy tu asistente de captura de datos. Te guiaré a través de un cuestionario para registrar un nuevo paciente. Vamos a empezar...
            </div>
        </div>
    `;
    
    // Hacer scroll al final
    const container = document.getElementById('chat-container');
    container.scrollTop = container.scrollHeight;
    
    // Hacer la primera pregunta
    askNextQuestion();
}

function askNextQuestion() {
    if (chatState.currentFieldIndex >= chatState.fields.length) {
        finalizeChat();
        return;
    }
    
    const currentField = chatState.fields[chatState.currentFieldIndex];
    addMessage('assistant', currentField.question);
    document.getElementById('chat-input').focus();
}

function addMessage(sender, text) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    // Primero escapar HTML, luego reemplazar \n con <br>
    const escapedText = escapeHtml(text).replace(/\n/g, '<br>');
    messageDiv.innerHTML = `<div class="message-content">${escapedText}</div>`;
    messagesDiv.appendChild(messageDiv);
    
    // Auto-scroll
    const container = document.getElementById('chat-container');
    setTimeout(() => {
        container.scrollTop = container.scrollHeight;
    }, 100);
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

async function processUserInput(userInput) {
    const currentField = chatState.fields[chatState.currentFieldIndex];
    let processedValue = userInput.trim();
    
    // Enviar el input del usuario al chat
    addMessage('user', userInput);
    
    // Validar según el tipo de campo
    let isValid = false;
    let extractedValue = processedValue;
    
    try {
        // Campos de tipo string (cariotipo, biología molecular, etc.)
        if (currentField.type === 'string') {
            const inputLower = userInput.toLowerCase();
            
            // Aceptar "No detectado" o "No aplica"
            if (inputLower.includes('no detectado') || inputLower === 'no detectado') {
                extractedValue = 'No detectado';
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = No detectado`);
            } else if (inputLower.includes('no aplica') || inputLower === 'no aplica') {
                extractedValue = 'No aplica';
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = No aplica`);
            } else if (userInput.trim() !== '') {
                // Aceptar cualquier otro valor no vacío
                extractedValue = userInput.trim();
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = ${extractedValue}`);
            } else {
                addMessage('error', `❌ Este campo es obligatorio. ${currentField.question}`);
                document.getElementById('chat-input').value = '';
                document.getElementById('chat-input').focus();
                return;
            }
        } 
        // Campo de Inmunofenotipo marcadores (string obligatorio, máximo 500 caracteres)
        else if (currentField.type === 'isoform_markers') {
            const inputTrimmed = userInput.trim();
            if (inputTrimmed === '') {
                addMessage('error', `❌ Este campo es obligatorio. ${currentField.question}`);
                document.getElementById('chat-input').value = '';
                document.getElementById('chat-input').focus();
                return;
            } else if (inputTrimmed.length > 500) {
                addMessage('error', `❌ El valor es muy largo (máximo 500 caracteres). Intenta de nuevo.`);
                document.getElementById('chat-input').value = '';
                document.getElementById('chat-input').focus();
                return;
            } else {
                extractedValue = inputTrimmed;
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = "${extractedValue}"`);
            }
        }
        // Campo de Marcadores aberrantes (solo valor capturado o "No detectado")
        else if (currentField.type === 'aberrant_markers') {
            const inputLower = userInput.toLowerCase();
            if (inputLower === 'no detectado' || inputLower.includes('no detectado')) {
                extractedValue = 'No detectado';
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = No detectado`);
            } else if (userInput.trim() !== '') {
                extractedValue = userInput.trim();
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = "${extractedValue}"`);
            } else {
                addMessage('error', `❌ Por favor escribe el valor o "No detectado".`);
                document.getElementById('chat-input').value = '';
                document.getElementById('chat-input').focus();
                return;
            }
        }
        // Campos opcionales antiguos
        else if (currentField.type === 'optional') {
            const inputLower = userInput.toLowerCase();
            
            if (inputLower.includes('no tengo') || inputLower === 'no tengo') {
                extractedValue = 'No tengo';
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = No tengo`);
            } else if (inputLower.includes('no aplica') || inputLower === 'no aplica') {
                extractedValue = 'No aplica';
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = No aplica`);
            } else if (inputLower === '' || userInput === '') {
                addMessage('assistant', `Veo que no escribiste nada. ¿Quieres poner "No tengo" o "No aplica"? Escribe cualquiera de esas dos opciones o proporciona el valor.`);
                document.getElementById('chat-input').value = '';
                document.getElementById('chat-input').focus();
                return;
            } else {
                extractedValue = userInput.charAt(0).toUpperCase() + userInput.slice(1);
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = ${extractedValue}`);
            }
        } 
        // Para otros tipos, usar el endpoint de extracción
        else {
            const response = await fetch(`${API_BASE}/api/chat/extract`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    field_name: currentField.field,
                    field_type: currentField.type,
                    user_input: userInput
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success' && data.extracted_value !== null) {
                extractedValue = data.extracted_value;
                isValid = currentField.validation(extractedValue);
                
                if (isValid) {
                    // Validación especial para blastos >= 20%
                    if (currentField.field === 'Número de blastos' && currentField.requiresConfirmation && extractedValue >= 20) {
                        addMessage('assistant', `⚠️ ADVERTENCIA SENSIBLE:\nEl porcentaje de blastos que ingresaste es ${extractedValue}%, lo que es significativo.\n\n¿Estás completamente seguro de que este valor es correcto? (Escribe "Sí" para confirmar o "No" para cambiar)`);
                        
                        // Guardar temporalmente pero pedir confirmación
                        chatState.pendingValue = { field: currentField.field, value: extractedValue };
                        chatState.awaitingConfirmation = true;
                        document.getElementById('chat-input').value = '';
                        document.getElementById('chat-input').focus();
                        return;
                    }
                    
                    addMessage('system', `✅ Entendido: ${currentField.field} = ${extractedValue}`);
                } else {
                    addMessage('error', `❌ Valor no válido. ${currentField.question}`);
                    document.getElementById('chat-input').value = '';
                    document.getElementById('chat-input').focus();
                    return;
                }
            } else {
                addMessage('error', `❌ No entendí bien. ${currentField.question}`);
                document.getElementById('chat-input').value = '';
                document.getElementById('chat-input').focus();
                return;
            }
        }
    } catch (error) {
        console.error('Error extrayendo valor:', error);
        addMessage('error', `❌ Error procesando la respuesta. Intenta de nuevo: ${currentField.question}`);
        document.getElementById('chat-input').value = '';
        document.getElementById('chat-input').focus();
        return;
    }
    
    // Guardar el valor extraído
    chatState.extractedData[currentField.field] = extractedValue;
    console.log('💾 Datos recopilados:', chatState.extractedData);
    
    // Pasar al siguiente campo
    chatState.currentFieldIndex++;
    document.getElementById('chat-input').value = '';
    
    // Pequeña pausa antes de la siguiente pregunta
    setTimeout(askNextQuestion, 800);
}

async function finalizeChat() {
    addMessage('assistant', '✅ ¡Perfecto! He recopilado todos los datos. Ahora voy a guardar el paciente...');
    
    try {
        // Convertir datos para enviar al servidor
        const datosFinales = {
            'Edad': parseFloat(chatState.extractedData['Edad']),
            'Sexo': String(chatState.extractedData['Sexo']).toUpperCase(),
            'Número de Leucocitos al inicio': parseFloat(chatState.extractedData['Número de Leucocitos al inicio']),
            'Tipo leucemia': String(chatState.extractedData['Tipo leucemia']).toUpperCase(),
            'Número de blastos': parseFloat(chatState.extractedData['Número de blastos']),
            'Clasificación cariotipo': String(chatState.extractedData['Clasificación cariotipo'] || 'No detectado'),
            'Biología molecular': String(chatState.extractedData['Biología molecular'] || ''),
            'GATE Inmunofenotipo': parseFloat(chatState.extractedData['GATE Inmunofenotipo']),
            'Inmunofenotipo marcadores': String(chatState.extractedData['Inmunofenotipo marcadores'] || ''),
            'Marcadores aberrantes': String(chatState.extractedData['Marcadores aberrantes'] || '')
        };
        
        console.log('📤 Enviando datos:', datosFinales);
        
        const response = await fetch(`${API_BASE}/api/paciente/nuevo`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(datosFinales)
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            addMessage('assistant', '🎉 ¡Paciente guardado exitosamente! El paciente ha sido registrado en el sistema.');
            
            // Mostrar el ID del paciente para seguimiento
            if (data.paciente_id) {
                const idMsg = `📋 **ID del Paciente para seguimiento:** ${data.paciente_id}\n\nUsa este ID para buscar y dar seguimiento al paciente en la sección "Pacientes Registrados"`;
                addMessage('system', idMsg);
            }
            
            // Mostrar la respuesta natural de la predicción en el chat con riesgo calculado
            if (data.prediccion_natural) {
                let diagnosticoMsg = `📊 Resultado del análisis:\n\n${data.prediccion_natural}`;
                
                // Agregar el riesgo calculado si está disponible
                if (data.riesgo_calculado) {
                    diagnosticoMsg += `\n\n⚠️ **Riesgo Calculado:** ${data.riesgo_calculado}`;
                }
                
                addMessage('assistant', diagnosticoMsg);
            } else {
                addMessage('assistant', '✅ El modelo está procesando... (Se necesitan más datos para entrenar el modelo completamente)');
            }
            
            // Mostrar información del modelo
            if (data.modelo_entrenado) {
                addMessage('system', '🤖 El modelo se ha entrenado correctamente con los nuevos datos.');
            }
            
            chatState.conversationActive = false;
            
            // Recargar tabla de pacientes después de 2 segundos
            setTimeout(() => {
                document.getElementById('filtro-pacientes').value = '';
                cargarPacientes();
                addMessage('assistant', '✅ La tabla de pacientes se ha actualizado. ¡Puedes ver el nuevo registro en la pestaña "Pacientes Registrados"!');
            }, 2000);
        } else {
            addMessage('error', `❌ Error al guardar: ${data.mensaje || 'Error desconocido'}`);
            chatState.conversationActive = false;
        }
    } catch (error) {
        addMessage('error', `❌ Error de conexión: ${error.message}`);
        chatState.conversationActive = false;
    }
}

function cancelChat() {
    chatState.conversationActive = false;
    chatState.currentFieldIndex = 0;
    chatState.extractedData = {};
    
    const messagesDiv = document.getElementById('chat-messages');
    messagesDiv.innerHTML = `
        <div class="chat-message assistant">
            <div class="message-content">
                👋 Chat cancelado. Para iniciar nuevamente, recarga la página o haz click en "Chat Asistente" otra vez.
            </div>
        </div>
    `;
    
    document.getElementById('chat-input').value = '';
    document.getElementById('chat-input').disabled = true;
    document.getElementById('chat-send-btn').disabled = true;
}

// ============================================================================
// CHAT ASISTENTE - EVENT LISTENERS
// ============================================================================

// Enviar mensaje cuando se hace click en el botón
document.getElementById('chat-send-btn').addEventListener('click', async function() {
    const input = document.getElementById('chat-input');
    const userInput = input.value.trim();
    
    if (!userInput) {
        input.focus();
        return;
    }
    
    if (!chatState.conversationActive) {
        alert('Por favor inicia una nueva conversación primero');
        return;
    }
    
    await processUserInput(userInput);
});

// Enviar mensaje con Enter
document.getElementById('chat-input').addEventListener('keypress', async function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('chat-send-btn').click();
    }
});

// Cancelar chat
document.getElementById('chat-cancel-btn').addEventListener('click', function() {
    if (confirm('¿Estás seguro de que quieres cancelar la captura?')) {
        cancelChat();
    }
});

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

// Event listeners para modal ERM (En desarrollo)
// TODO: Implementar funcionalidad ERM cuando esté lista
/*
document.getElementById('erm-chat-send-btn').addEventListener('click', function() {
    const input = document.getElementById('erm-chat-input');
    const userInput = input.value.trim();
    
    if (!userInput) {
        input.focus();
        return;
    }
    
    // Por ahora, solo mostrar el mensaje de forma visual
    const messagesDiv = document.getElementById('erm-chat-messages');
    
    // Agregar mensaje del usuario
    const userMsgDiv = document.createElement('div');
    userMsgDiv.className = 'chat-message user';
    userMsgDiv.innerHTML = `<div class="message-content">${escapeHtml(userInput)}</div>`;
    messagesDiv.appendChild(userMsgDiv);
    
    // Limpiar input
    input.value = '';
    
    // Auto-scroll
    const container = document.getElementById('erm-chat-container');
    setTimeout(() => {
        container.scrollTop = container.scrollHeight;
    }, 100);
    
    input.focus();
});

// Enviar con Enter en modal ERM
document.getElementById('erm-chat-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('erm-chat-send-btn').click();
    }
});

// Cerrar modal al hacer click fuera
document.getElementById('modal-erm').addEventListener('click', function(e) {
    if (e.target === this) {
        cerrarModalERM();
    }
});
*/

console.log('✅ Interfaz web cargada correctamente');

// Cargar pacientes al abrir la aplicación
document.addEventListener('DOMContentLoaded', () => cargarPacientes());