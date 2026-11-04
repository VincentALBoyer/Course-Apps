try:
    import ipywidgets as widgets
    from IPython.display import display, HTML, clear_output
    HAS_NOTEBOOK_DEPS = True
except ImportError:
    HAS_NOTEBOOK_DEPS = False

import unicodedata

# Puzzles with Narrative and Educational Facts (v4)
PUZZLES = [
    {
        "id": 1,
        "title": "Nivel 1: El Acceso al Almacén",
        "story": "¡Emergencia! El sistema de gestión de inventarios se ha bloqueado. Para entrar al almacén principal, debes validar la variable base del lote económico.",
        "type": "text",
        "clue": "Busca la fórmula de 'Tamaño de lote económico' (EOQ).",
        "task": "¿Qué variable representa el 'Costo de preparación'?",
        "answer": "S",
        "hint": "Consulta la página 26.",
        "fact": "EL EOQ ayuda a minimizar la suma de los costos de mantenimiento y de pedido.",
        "img": "room1_almacen_1772051105275.png"
    },
    {
        "id": 2,
        "title": "Nivel 2: Laboratorio de Análisis",
        "story": "Has entrado, pero los sensores de demanda están descalibrados. Necesitamos cruzar datos de dos herramientas analíticas diferentes.",
        "type": "numeric",
        "clue": "Localiza 'Suavizamiento exponencial doble' y 'MAPE'.",
        "task": "Suma los números de página donde aparecen estos dos conceptos.",
        "answer": "51",
        "hint": "Pág 25 + Pág 26 = 51.",
        "fact": "El MAPE es una de las métricas más usadas para medir la precisión de los pronósticos de ventas.",
        "img": "room2_pronosticos_1772051159434.png"
    },
    {
        "id": 3,
        "title": "Nivel 3: El Hub Geográfico",
        "story": "Los camiones están perdidos. Debemos recalcular el centro de mando para optimizar las rutas de transporte.",
        "type": "choice",
        "clue": "Revisa la sección de 'Centro de gravedad'.",
        "task": "¿Qué representa la variable 'w_i'?",
        "choices": ["peso de la unidad", "ponderación del indicador", "ancho de la vía", "valor del inventario"],
        "answer": "ponderación del indicador",
        "hint": "Mira la sección 'donde:' en la página 28.",
        "fact": "El método del centro de gravedad es ideal para ubicar una nueva planta o almacén minimizando costos de transporte.",
        "img": "room3_logistica_1772051224734.png"
    },
    {
        "id": 4,
        "title": "Nivel 4: Terminal de Despacho",
        "story": "Los clientes están llamando. La precisión de las entregas ha caído. Debemos reajustar el indicador de desempeño.",
        "type": "choice",
        "clue": "Encuentra la métrica '% Precisión de entrega'.",
        "task": "¿Cuál es el texto exacto del denominador en la fórmula?",
        "choices": [
            "Valor del producto que se envió al cliente",
            "Valor del producto ordenado",
            "Ventas netas totales",
            "Gastos de operación"
        ],
        "answer": "Valor del producto que se envió al cliente",
        "hint": "Revisa la página 28.",
        "fact": "Una alta precisión de entrega reduce las devoluciones y mejora la satisfacción del cliente.",
        "img": "room4_metricas_1772051319592.png"
    },
    {
        "id": 5,
        "title": "Nivel 5: Crisis de Inventario",
        "story": "¡Niveles críticos! Las máquinas necesitan saber exactamente cuánto pedir para no detener la producción.",
        "type": "numeric",
        "clue": "Usa la fórmula de Q* (EOQ).",
        "task": "Si D=2000, S=100 y H=10, ¿cuál es el lote económico (Q*)?",
        "answer": "200",
        "hint": "√(2*2000*100/10) = √40000. Pág 26.",
        "fact": "El modelo EOQ asume una demanda constante, lo cual es raro pero útil como base teórica.",
        "img": "room5_inventario_crisis_1772051533783.png"
    },
    {
        "id": 6,
        "title": "Nivel 6: El Radar de Seguimiento",
        "story": "Se ha detectado una anomalía en el flujo. La señal de rastreo está fuera de los límites permitidos.",
        "type": "text",
        "clue": "Busca 'Señal de rastreo'.",
        "task": "¿Qué sigla aparece en el denominador?",
        "answer": "DAM",
        "hint": "Página 25. Desviación Absoluta Media.",
        "fact": "La señal de rastreo indica si un modelo de pronóstico está sesgado hacia arriba o hacia abajo.",
        "img": "room6_radar_1772051661772.png"
    },
    {
        "id": 7,
        "title": "Nivel 7: Control de Calidad Total",
        "story": "No basta con entregar, hay que entregar bien. El RIANSC nos dirá si estamos cumpliendo el estándar.",
        "type": "choice",
        "clue": "Busca 'RIANSC'.",
        "task": "¿Qué significa exactamente esta sigla?",
        "choices": [
            "Rotación de inventario acumulada no solicitada",
            "Rendimiento inicial de activos no servidos",
            "Rotación del inventario ajustado al nivel del servicio del cliente",
            "Relación de inventario anual sobre costos"
        ],
        "answer": "Rotación del inventario ajustado al nivel del servicio del cliente",
        "hint": "Página 29.",
        "fact": "Este indicador vincula la eficiencia logística directamente con el nivel de servicio prometido.",
        "img": "room7_laser_scanner.png"
    },
    {
        "id": 8,
        "title": "Nivel 8: El Flujo Maestro",
        "story": "La línea de producción se está ralentizando. El cuello de botella es evidente. Calcula la capacidad máxima.",
        "type": "choice",
        "clue": "Localiza 'Planeación de recursos'.",
        "task": "¿Cuál es el denominador en la fórmula de 'Producción máxima'?",
        "choices": ["Tiempo de trabajo", "Tiempo promedio de llegada", "Tiempo del cuello de botella", "Demanda del cliente"],
        "answer": "Tiempo del cuello de botella",
        "hint": "Página 28.",
        "fact": "La teoría de restricciones dice que la producción total está limitada por el recurso más lento.",
        "img": "room8_mechanical_assembly.png"
    },
    {
        "id": 9,
        "title": "Nivel 9: El Cierre de Ventas",
        "story": "Estamos en la recta final. Evalúa la efectividad comercial antes de sellar el contrato global.",
        "type": "numeric",
        "clue": "Busca el Índice de Efectividad de Ventas (IEV).",
        "task": "¿Cuántos componentes se multiplican para obtener el IEV?",
        "answer": "3",
        "hint": "Página 30.",
        "fact": "El IEV combina utilización, flujo y calidad de ventas en un solo número estrella.",
        "img": "room9_coorporate_office.png"
    },
    {
        "id": 10,
        "title": "Nivel 10: La Bóveda Logística",
        "story": "Llegaste a la puerta final. Solo un verdadero ingeniero industrial puede descifrar la correlación absoluta para abrir la bóveda.",
        "type": "numeric",
        "clue": "Estudia el 'Coeficiente de correlación'.",
        "task": "Cuenta el número total de Σ en toda la expresión de 'r'.",
        "answer": "7",
        "hint": "Pág 25. Son 3 arriba y 4 abajo.",
        "fact": "Un coeficiente de 1 indica una relación perfecta, el sueño de cualquier planificador de demanda.",
        "img": "room10_vault.png"
    }
]

FINAL_KEYWORD = "LOGISTICA"

class GameLogic:
    def __init__(self, platform="colab"):
        self.current_room = 0
        self.platform = platform
        self.completed = False
        self.hints_used = 0
        self.room_hint_used = False
        self.show_fact = False

    def normalize(self, s):
        if not isinstance(s, str): s = str(s)
        import unicodedata
        s = s.lower().strip()
        return "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    def check_answer(self, user_answer):
        puzzle = PUZZLES[self.current_room]
        if self.normalize(user_answer) == self.normalize(puzzle['answer']):
            self.show_fact = True
            return True, f"✅ ¡LOGRADO! {puzzle['fact']}"
        else:
            return False, "❌ Acceso denegado. Revisa tus cálculos o el formulario."

    def next_level(self):
        self.current_room += 1
        self.room_hint_used = False
        self.show_fact = False
        if self.current_room >= len(PUZZLES):
            self.completed = True

    def use_hint(self):
        if not self.room_hint_used:
            self.hints_used += 1
            self.room_hint_used = True
        return PUZZLES[self.current_room]['hint']

    def get_progress(self):
        return (self.current_room / len(PUZZLES)) * 100

    def get_rank(self):
        if self.hints_used == 0: return "DIAMANTE: Maestro de Suministros 💎"
        if self.hints_used <= 2: return "ORO: Estratega Senior 🥇"
        if self.hints_used <= 5: return "PLATA: Analista de Procesos 🥈"
        return "BRONCE: Pasante en Práctica 🥉"

# Colab UI Implementation (v4)
class ColabGame:
    def __init__(self):
        self.logic = GameLogic(platform="colab")
        self.output = widgets.Output()
        
    def start(self):
        self.render()

    def render(self):
        with self.output:
            clear_output()
            if self.logic.completed:
                display(HTML(f"""
                    <div style="background-color: #d4edda; padding: 20px; border-radius: 10px; border: 1px solid #c3e6cb;">
                        <h2 style="color: #155724;">🎉 ¡MISIÓN CUMPLIDA! 🎉</h2>
                        <p>Has salvado la fábrica global. Rango: <b>{self.logic.get_rank()}</b></p>
                        <p style="font-size: 20px; font-weight: bold;">PALABRA CLAVE FINAL: <span style="color: #721c24;">{FINAL_KEYWORD}</span></p>
                    </div>
                """))
                return

            puzzle = PUZZLES[self.logic.current_room]
            
            # Progress bar
            progress = widgets.FloatProgress(
                value=self.logic.get_progress(), min=0, max=100,
                description='Prioridad:', bar_style='info'
            )
            
            display(HTML(f"<h2 style='color:#007bff;'>{puzzle['title']}</h2>"))
            display(HTML(f"<p style='font-style:italic; color:#555;'>{puzzle['story']}</p>"))
            
            if not self.logic.show_fact:
                display(HTML(f"<p><b>🔍 Contexto:</b> {puzzle['clue']}</p>"))
                display(HTML(f"<p><b>🎯 Tarea:</b> {puzzle['task']}</p>"))
                
                if puzzle['type'] == 'choice':
                    ans_input = widgets.Dropdown(options=["-- Selecciona --"] + puzzle['choices'])
                else:
                    ans_input = widgets.Text(placeholder='Respuesta...')
                    
                btn_valid = widgets.Button(description="Validar Sistema", button_style='success')
                btn_hint = widgets.Button(description="💡 Ver Pista", button_style='warning')
                feedback = widgets.Label(value="")

                def on_valid(b):
                    correct, msg = self.logic.check_answer(ans_input.value)
                    if correct:
                        self.render()
                    else:
                        feedback.value = msg

                def on_hint(b):
                    display(HTML(f"<p style='color:#856404;'><b>Pista:</b> {self.logic.use_hint()}</p>"))

                btn_valid.on_click(on_valid)
                btn_hint.on_click(on_hint)
                display(progress, ans_input, widgets.HBox([btn_valid, btn_hint]), feedback)
            else:
                display(HTML(f"""
                    <div style="background-color: #e7f3ff; padding: 15px; border-radius: 8px; border: 1px solid #b8daff;">
                        <p style="color: #004085;">✅ <b>¡LOGRADO!</b></p>
                        <p><i>{puzzle['fact']}</i></p>
                    </div>
                """))
                btn_next = widgets.Button(description="Siguiente Sala ➡️", button_style='primary')
                def on_next(b):
                    self.logic.next_level()
                    self.render()
                btn_next.on_click(on_next)
                display(btn_next)
            
        display(self.output)
