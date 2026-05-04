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
// CHAT ASISTENTE - STATE Y CONFIGURACIÓN
// ============================================================================

let chatState = {
    conversationActive: false,
    currentFieldIndex: 0,
    extractedData: {},
    fields: [
        { field: 'Edad', type: 'number', question: '¿Cuál es la edad del paciente? (entre 0 y 120 años)', validation: (v) => !isNaN(v) && v >= 0 && v <= 120 },
        { field: 'Sexo', type: 'option', question: '¿Cuál es el sexo del paciente? (M para Masculino, F para Femenino)', options: ['M', 'F'], validation: (v) => ['M', 'F'].includes(v.toUpperCase()) },
        { field: 'Número de Leucocitos al inicio', type: 'number', question: '¿Cuál es el número de leucocitos al inicio?', validation: (v) => !isNaN(v) && v > 0 },
        { field: 'Tipo leucemia', type: 'option', question: '¿Cuál es el tipo de leucemia? (B, T o M)', options: ['B', 'T', 'M'], validation: (v) => ['B', 'T', 'M'].includes(v.toUpperCase()) },
        { field: 'Número de blastos', type: 'number', question: '¿Cuál es el porcentaje de blastos? (0-100)', validation: (v) => !isNaN(v) && v >= 0 && v <= 100 },
        { field: 'Clasificación cariotipo', type: 'optional', question: '¿Cuál es la clasificación cariotipo? (Di "no tengo" o "no aplica" si no tienes esta información)', validation: (v) => true },
        { field: 'Biología molecular', type: 'optional', question: '¿Cuál es la biología molecular? (Puedo decir "no tengo" o "no aplica" si no tienes esta información)', validation: (v) => true },
        { field: 'GATE Inmunofenotipo', type: 'number', question: '¿Cuál es el GATE Inmunofenotipo?', validation: (v) => !isNaN(v) && v >= 0 },
        { field: 'Marcadores aberrantes', type: 'optional', question: '¿Hay marcadores aberrantes? (Puedes decir "no tengo", "no aplica" o "negativos" si no hay)', validation: (v) => true }
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
        // Campos opcionales - detectar "no tengo" o "no aplica"
        if (currentField.type === 'optional') {
            const inputLower = userInput.toLowerCase();
            
            // Si el usuario dice que no tiene o no aplica, usar eso
            if (inputLower.includes('no tengo') || inputLower === 'no tengo') {
                extractedValue = 'No tengo';
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = No tengo`);
            } else if (inputLower.includes('no aplica') || inputLower === 'no aplica') {
                extractedValue = 'No aplica';
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = No aplica`);
            } else if (inputLower === '' || userInput === '') {
                // Campo vacío en opcional - pedir confirmación
                addMessage('assistant', `Veo que no escribiste nada. ¿Quieres poner "No tengo" o "No aplica"? Escribe cualquiera de esas dos opciones o proporciona el valor.`);
                document.getElementById('chat-input').value = '';
                document.getElementById('chat-input').focus();
                return;
            } else {
                // Usuario escribió algo diferente
                extractedValue = userInput.capitalize ? userInput.charAt(0).toUpperCase() + userInput.slice(1) : userInput;
                isValid = true;
                addMessage('system', `✅ Entendido: ${currentField.field} = ${extractedValue}`);
            }
        } else {
            // Para campos no opcionales, usar el endpoint de extracción
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
            
            // Mostrar la respuesta natural de la predicción en el chat
            if (data.prediccion_natural) {
                addMessage('assistant', `📊 Resultado del análisis:\n\n${data.prediccion_natural}`);
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

console.log('✅ Interfaz web cargada correctamente');

// Cargar pacientes al abrir la aplicación
document.addEventListener('DOMContentLoaded', cargarPacientes);