import os
import random
import re
import time
import json
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Academia Sargento Madrid", layout="wide")

# ==========================================
# 🔒 SISTEMA DE CONTRASEÑA
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "sargento2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("### 🔒 Acceso Privado - Academia Sargento")
        st.text_input("Por favor, introduce la contraseña:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("### 🔒 Acceso Privado - Academia Sargento")
        st.text_input("Por favor, introduce la contraseña:", type="password", on_change=password_entered, key="password")
        st.error("❌ Contraseña incorrecta.")
        return False
    return True

if not check_password():
    st.stop()
# ==========================================

# ==========================================
# 🧠 MEMORIA DEL USUARIO (JSON)
# ==========================================
def cargar_memoria():
    if os.path.exists("usuario.json"):
        try:
            with open("usuario.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"historial": [], "fallos": []}
    return {"historial": [], "fallos": []}

def guardar_memoria(datos):
    with open("usuario.json", "w", encoding="utf-8") as f:
        json.dump(datos, f)

if "user_data" not in st.session_state:
    st.session_state.user_data = cargar_memoria()
# ==========================================

def safe_md(text):
    if not text: return ""
    return text.replace("<", "&lt;").replace(">", "&gt;")

def get_supuesto_category(sup):
    bloques_texto = " ".join(sup['bloques']).lower() + " " + sup['titulo'].lower()
    if 'rasante' in bloques_texto: return 'rasante'
    if 'ega' in bloques_texto: return 'EGA'
    if 'incendio' in bloques_texto: return 'Incendios' 
    if 'tráfico' in bloques_texto or 'trafico' in bloques_texto or 'vital' in bloques_texto: return 'Tráfico'
    if 'altura' in bloques_texto or 'suicidio' in bloques_texto: return 'Altura+Suicidio'
    if 'rbq' in bloques_texto or 'nrbq' in bloques_texto: return 'RBQ'
    if 'arbolado' in bloques_texto: return 'Arbolado'
    return 'Otros'

@st.cache_data
def cargar_datos():
    with open("banco_unificado.txt", 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    
    soluciones = {}
    pat_tab = re.compile(r'\|\s*([A-Z0-9.-]+)\s*\|\s*\*\*?([A-C])\*\*?\s*\|([^|\n]+)')
    for m in pat_tab.finditer(text):
        soluciones[m.group(1).strip()] = {'respuesta': m.group(2).strip().upper(), 'justificacion': m.group(3).strip()}

    current_sol_id = None
    for l in text.split('\n'):
        l = l.strip()
        match_sol = re.match(r'^\*\*\s*([A-Z0-9.-]+)\s*[-–—]\s*([A-C])\s*\.?\*\*(.*)', l)
        if match_sol:
            current_sol_id = match_sol.group(1).strip()
            soluciones[current_sol_id] = {'respuesta': match_sol.group(2).strip().upper(), 'justificacion': match_sol.group(3).strip()}
        elif current_sol_id:
            stop_markers = [r'^#', r'^\*Páginas:', r'^\*\*Reparto', r'^Reparto', r'^De cálculo']
            if any(re.match(marker, l) for marker in stop_markers):
                current_sol_id = None
            elif l and not l.startswith('|'):
                soluciones[current_sol_id]['justificacion'] += "\n" + l

    chunks = re.split(r'\n(?=##+\s*[Ss]upuesto|\*\*?ID:\s*)', text)
    preguntas_teo = []
    supuestos_pra = []
    todas_planas = []
    current_sup = None
    sup_counter = 0

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk: continue

        if re.match(r'^##+\s*[Ss]upuesto', chunk):
            sup_counter += 1
            lines = chunk.split('\n')
            titulo = lines[0].strip()
            contexto = "\n\n".join([l.strip() for l in lines[1:] if l.strip()])
            current_sup = {'id': f"SUP_{sup_counter}", 'titulo': safe_md(titulo), 'contexto': safe_md(contexto), 'preguntas': [], 'bloques': set()}
            supuestos_pra.append(current_sup)
            
        elif re.match(r'^\*\*?ID:\s*', chunk):
            header_match = re.search(r'ID:\s*([^\s|*]+)\s*\|\s*Tipo:\s*([^|\n*]+)(?:\|\s*Bloque:\s*([^\n*]+))?', chunk)
            if not header_match: continue
            
            p_id = header_match.group(1).strip()
            tipo = header_match.group(2).strip().lower()
            bloque = (header_match.group(3) or "").strip()

            if p_id == "T08-015": continue
            bloques_excluidos = ["asistencias técnicas", "accesos forzados", "estructuras colapsadas", "rescate acuático", "ascensores"]
            if any(b in bloque.lower() for b in bloques_excluidos) and "EGA" not in bloque.upper():
                continue

            tema_match = re.search(r'T(\d+)', p_id)
            tema = int(tema_match.group(1)) if tema_match else None

            lines = [l.strip() for l in chunk.split('\n') if l.strip()]
            enunciado = []
            opciones = {'A': '', 'B': '', 'C': ''}
            current_option = None

            for l in lines[1:]:
                stop_markers = [r'^#', r'^\*Páginas:', r'^\*\*Reparto', r'^Reparto', r'^De cálculo', r'^\*\*\s*[A-Z0-9.-]+\s*[-–—]\s*[A-C]\s*\.?\*\*']
                if any(re.match(marker, l) for marker in stop_markers): break

                match_opcion = re.match(r'^(\*\*?[A-C]\*\*?[\.\)]|[A-C][\.\)])\s*(.*)', l)
                if match_opcion:
                    k = re.search(r'[A-C]', match_opcion.group(1)).group()
                    opciones[k] = match_opcion.group(2).strip()
                    current_option = k
                elif "SOLUCIONARIO" not in l and "---" not in l and not l.startswith('|'):
                    if current_option: opciones[current_option] += "\n" + l.strip()
                    else: enunciado.append(l)

            sol_data = soluciones.get(p_id, {'respuesta': 'A', 'justificacion': 'Justificación en el temario oficial.'})

            q_obj = {
                'id': p_id, 'tema': tema,
                'tipo': 'teorica' if 'teór' in tipo or 'teor' in tipo else 'practica',
                'bloque': bloque, 'enunciado': safe_md("\n\n".join(enunciado)),
                'opciones': {k: safe_md(v) for k,v in opciones.items()}, 
                'solucion': sol_data['respuesta'],
                'justificacion': safe_md(sol_data['justificacion'])
            }
            
            todas_planas.append(q_obj)

            if q_obj['tipo'] == 'teorica':
                preguntas_teo.append(q_obj)
                current_sup = None
            else:
                if current_sup is None:
                    sup_counter += 1
                    current_sup = {'id': f"SUP_{sup_counter}", 'titulo': f"SUPUESTO - {q_obj['bloque']}", 'contexto': "", 'preguntas': [], 'bloques': set()}
                    supuestos_pra.append(current_sup)
                current_sup['preguntas'].append(q_obj)
                current_sup['bloques'].add(bloque)

    return preguntas_teo, supuestos_pra, todas_planas

def generar_nuevo_examen(preguntas_teo, supuestos_pra, modo, temas_sel, num_preg, todas_planas, uso_acumulado):
    if modo == "Simulacro Oficial":
        CUPO_TEORICO = {1:1, 2:1, 3:2, 4:4, 5:4, 6:3, 7:3, 8:3, 9:2, 10:1, 11:2, 12:2, 13:3, 14:2, 15:3, 16:2, 17:2, 18:2, 19:6, 20:2}
        CATEGORIAS_PRA = ['Incendios', 'rasante', 'EGA', 'Tráfico', 'Altura+Suicidio', 'RBQ', 'Arbolado']
        
        seleccion_teo = []
        for tema, cant in CUPO_TEORICO.items():
            cands = [p for p in preguntas_teo if p['tema'] == tema]
            if cands:
                min_uso = min(uso_acumulado.get(p['id'], 0) for p in cands)
                mejores = [p for p in cands if uso_acumulado.get(p['id'], 0) == min_uso]
                random.shuffle(mejores)
                
                if len(mejores) >= cant:
                    elegidas = mejores[:cant]
                else:
                    elegidas = mejores
                    faltan = cant - len(elegidas)
                    resto = [p for p in cands if p not in elegidas]
                    random.shuffle(resto)
                    elegidas.extend(resto[:faltan])
                seleccion_teo.extend(elegidas)
        random.shuffle(seleccion_teo)
        
        seleccion_pra = []
        for _ in range(300):
            temp_pra = []
            total_qs = 0
            for cat in CATEGORIAS_PRA:
                cands = [s for s in supuestos_pra if get_supuesto_category(s) == cat]
                if cands:
                    min_uso = min(uso_acumulado.get(s['id'], 0) for s in cands)
                    mejores = [s for s in cands if uso_acumulado.get(s['id'], 0) == min_uso]
                    elegido = random.choice(mejores)
                    temp_pra.append(elegido)
                    total_qs += len(elegido['preguntas'])
            
            if total_qs == 16:
                seleccion_pra = temp_pra
                break
            elif total_qs < 16:
                disp = [s for s in supuestos_pra if s not in temp_pra]
                random.shuffle(disp)
                for s in disp:
                    if total_qs + len(s['preguntas']) <= 16:
                        temp_pra.append(s)
                        total_qs += len(s['preguntas'])
                if total_qs == 16:
                    seleccion_pra = temp_pra
                    break
                    
        if not seleccion_pra: seleccion_pra = temp_pra 
        
        for p in seleccion_teo: uso_acumulado[p['id']] = uso_acumulado.get(p['id'], 0) + 1
        for s in seleccion_pra: uso_acumulado[s['id']] = uso_acumulado.get(s['id'], 0) + 1
            
        return seleccion_teo, seleccion_pra
        
    elif modo == "Repaso de Fallos":
        fallos_ids = st.session_state.user_data.get('fallos', [])
        cands = [p for p in todas_planas if p['id'] in fallos_ids]
        random.shuffle(cands)
        return cands[:num_preg], []
        
    else:
        cands = [p for p in todas_planas if p['tema'] in temas_sel]
        random.shuffle(cands)
        return cands[:num_preg], []

st.title("🚒 Academia Sargento Madrid")

try:
    preguntas_teo, supuestos_pra, todas_planas = cargar_datos()
except Exception as e:
    st.error("No se encuentra el archivo 'banco_unificado.txt'.")
    st.stop()

if "uso_acumulado" not in st.session_state:
    st.session_state.uso_acumulado = {}
if "examen" not in st.session_state:
    st.session_state.examen = None
    st.session_state.corregido = False
    st.session_state.modo_actual = None

with st.sidebar:
    st.header("⚙️ Configuración")
    modo = st.radio("Modo de estudio:", ["Simulacro Oficial", "Test por Temas", "Repaso de Fallos"])
    
    if modo == "Test por Temas":
        temas_disponibles = sorted(list(set(p['tema'] for p in todas_planas if p['tema'] is not None)))
        temas_sel = st.multiselect("Elige los temas:", temas_disponibles, default=temas_disponibles[:1])
        num_preg = st.number_input("Cantidad de preguntas:", min_value=1, max_value=200, value=20)
    elif modo == "Repaso de Fallos":
        num_fallos = len(st.session_state.user_data.get('fallos', []))
        st.info(f"Tienes **{num_fallos}** preguntas falladas en la recámara.")
        if num_fallos > 0:
            num_preg = st.number_input("Cantidad a repasar:", min_value=1, max_value=num_fallos, value=min(20, num_fallos))
        else:
            num_preg = 0
        temas_sel = []
    else:
        temas_sel = []
        num_preg = 0
        
    if st.button("Generar Examen", type="primary"):
        if modo == "Repaso de Fallos" and num_preg == 0:
            st.error("¡No tienes preguntas falladas! Enhorabuena.")
        else:
            teo, pra = generar_nuevo_examen(preguntas_teo, supuestos_pra, modo, temas_sel, num_preg, todas_planas, st.session_state.uso_acumulado)
            if not teo and not pra:
                st.error("No hay preguntas para los parámetros seleccionados.")
            else:
                st.session_state.examen = {'teo': teo, 'pra': pra}
                st.session_state.corregido = False
                st.session_state.modo_actual = modo
                st.session_state.start_time = time.time()
                for key in list(st.session_state.keys()):
                    if key.startswith("resp_"): del st.session_state[key]
                st.rerun()

    # --- HISTÓRICO DE NOTAS ---
    st.write("---")
    if st.session_state.user_data.get('historial'):
        with st.expander("📈 Tu Histórico de Notas"):
            for h in reversed(st.session_state.user_data['historial'][-10:]):
                st.markdown(f"**{h['fecha']}**\n\n{h['modo']} - **Nota: {h['nota']}**")

if st.session_state.examen is None:
    st.info("👈 Selecciona tus preferencias en el menú y haz clic en 'Generar Examen' para empezar.")
    st.stop()

# --- RELOJ CUENTA ATRÁS FLOTANTE ---
if not st.session_state.corregido:
    minutos_totales = 105 if st.session_state.modo_actual == "Simulacro Oficial" else int(len(st.session_state.examen['teo']) * 1.5)
    
    timer_html = f"""
    <div style="font-family: sans-serif; background-color: #262730; color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #ff4b4b; text-align: center; margin-bottom: 20px;">
        <h2 style="margin:0; color: #ff4b4b;" id="clock">⏳ Calculando tiempo...</h2>
    </div>
    <script>
        var minutos = {minutos_totales};
        var countDownDate = new Date().getTime() + (minutos * 60000);
        var x = setInterval(function() {{
            var now = new Date().getTime();
            var distance = countDownDate - now;
            var m = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            var s = Math.floor((distance % (1000 * 60)) / 1000);
            document.getElementById("clock").innerHTML = "⏳ Tiempo restante: " + m + "m " + s + "s";
            if (distance < 0) {{
                clearInterval(x);
                document.getElementById("clock").innerHTML = "🚨 ¡TIEMPO AGOTADO!";
            }}
        }}, 1000);
    </script>
    """
    components.html(timer_html, height=80)

if not st.session_state.corregido:
    with st.form("examen_form"):
        if st.session_state.modo_actual == "Simulacro Oficial":
            st.header("PARTE 1: TEÓRICA (50 PREGUNTAS)")
        elif st.session_state.modo_actual == "Repaso de Fallos":
            st.header("REPASO DE FALLOS")
        else:
            st.header("TEST PERSONALIZADO")
            
        for i, p in enumerate(st.session_state.examen['teo'], 1):
            st.markdown(f"**{i}. {p['enunciado']}**")
            st.radio("Opciones", options=["- (En blanco)", f"A) {p['opciones'].get('A','')}", f"B) {p['opciones'].get('B','')}", f"C) {p['opciones'].get('C','')}"], key=f"resp_{p['id']}", label_visibility="collapsed")
            st.divider()

        if st.session_state.examen['pra']:
            total_preguntas_pra = sum(len(s['preguntas']) for s in st.session_state.examen['pra'])
            st.header(f"PARTE 2: PRÁCTICA ({total_preguntas_pra} PREGUNTAS)")
            q_idx = 1
            for sup in st.session_state.examen['pra']:
                st.markdown(f"### {sup['titulo']}")
                if sup['contexto']: st.info(sup['contexto'])
                for p in sup['preguntas']:
                    st.markdown(f"**P{q_idx}. {p['enunciado']}**")
                    st.radio("Opciones", options=["- (En blanco)", f"A) {p['opciones'].get('A','')}", f"B) {p['opciones'].get('B','')}", f"C) {p['opciones'].get('C','')}"], key=f"resp_{p['id']}", label_visibility="collapsed")
                    q_idx += 1
                    st.write("")
                st.divider()

        if st.form_submit_button("Corregir Examen", type="primary"):
            st.session_state.tiempo_empleado = time.time() - st.session_state.start_time
            
            # --- LOGICA DE CORRECCIÓN Y GUARDADO DE FALLOS ---
            aciertos_t = 0; errores_t = 0
            for p in st.session_state.examen['teo']:
                resp = st.session_state.get(f"resp_{p['id']}", "-")[0]
                if resp == p['solucion']:
                    aciertos_t += 1
                    if p['id'] in st.session_state.user_data['fallos']:
                        st.session_state.user_data['fallos'].remove(p['id'])
                elif resp != "-":
                    errores_t += 1
                    if p['id'] not in st.session_state.user_data['fallos']:
                        st.session_state.user_data['fallos'].append(p['id'])

            aciertos_p = 0; errores_p = 0
            if st.session_state.examen['pra']:
                for sup in st.session_state.examen['pra']:
                    for p in sup['preguntas']:
                        resp = st.session_state.get(f"resp_{p['id']}", "-")[0]
                        if resp == p['solucion']:
                            aciertos_p += 1
                            if p['id'] in st.session_state.user_data['fallos']:
                                st.session_state.user_data['fallos'].remove(p['id'])
                        elif resp != "-":
                            errores_p += 1
                            if p['id'] not in st.session_state.user_data['fallos']:
                                st.session_state.user_data['fallos'].append(p['id'])

            total_t = len(st.session_state.examen['teo'])
            total_p = sum(len(s['preguntas']) for s in st.session_state.examen['pra']) if st.session_state.examen['pra'] else 0
            
            nota_t = ((aciertos_t * 1) - (errores_t * 0.20)) / total_t * 10 if total_t > 0 else 0
            nota_p = ((aciertos_p * 1) - (errores_p * 0.20)) / total_p * 10 if total_p > 0 else 0
            
            nota_final = (nota_t + nota_p) / 2 if st.session_state.modo_actual == "Simulacro Oficial" else nota_t
            
            st.session_state.user_data['historial'].append({
                "fecha": datetime.now().strftime("%d/%m %H:%M"),
                "modo": st.session_state.modo_actual,
                "nota": round(nota_final, 2)
            })
            
            guardar_memoria(st.session_state.user_data)
            
            st.session_state.corregido = True
            st.rerun()

else:
    st.header("RESULTADOS")
    
    for i, p in enumerate(st.session_state.examen['teo'], 1):
        st.markdown(f"**{i}. {p['enunciado']}**")
        if p['opciones'].get('A'): st.markdown(f"A) {p['opciones']['A']}")
        if p['opciones'].get('B'): st.markdown(f"B) {p['opciones']['B']}")
        if p['opciones'].get('C'): st.markdown(f"C) {p['opciones']['C']}")
        
        respuesta_dada = st.session_state.get(f"resp_{p['id']}", "-")[0]
        correcta = p['solucion']
        
        if respuesta_dada == "-":
            st.warning(f"No contestada. La correcta era la **{correcta}**.")
        elif respuesta_dada == correcta:
            st.success(f"¡Correcto! Tu respuesta: **{respuesta_dada}**")
        else:
            st.error(f"Incorrecto. Marcaste **{respuesta_dada}** y la correcta es **{correcta}**.")
        
        st.info(f"**Justificación:**\n{p['justificacion']}")
        st.divider()

    if st.session_state.examen['pra']:
        st.header("RESULTADOS - PRÁCTICA")
        q_idx = 1
        for sup in st.session_state.examen['pra']:
            st.markdown(f"### {sup['titulo']}")
            if sup['contexto']: st.info(sup['contexto'])
            for p in sup['preguntas']:
                st.markdown(f"**P{q_idx}. {p['enunciado']}**")
                
                if p['opciones'].get('A'): st.markdown(f"A) {p['opciones']['A']}")
                if p['opciones'].get('B'): st.markdown(f"B) {p['opciones']['B']}")
                if p['opciones'].get('C'): st.markdown(f"C) {p['opciones']['C']}")
                
                respuesta_dada = st.session_state.get(f"resp_{p['id']}", "-")[0]
                correcta = p['solucion']
                
                if respuesta_dada == "-":
                    st.warning(f"No contestada. La correcta era la **{correcta}**.")
                elif respuesta_dada == correcta:
                    st.success(f"¡Correcto! Tu respuesta: **{respuesta_dada}**")
                else:
                    st.error(f"Incorrecto. Marcaste **{respuesta_dada}** y la correcta es **{correcta}**.")
                
                st.info(f"**Justificación:**\n{p['justificacion']}")
                q_idx += 1
            st.divider()

    st.sidebar.header("📊 Resumen del Examen")
    m_emp = int(st.session_state.tiempo_empleado // 60)
    s_emp = int(st.session_state.tiempo_empleado % 60)
    st.sidebar.write(f"⏱️ **Tiempo empleado:** {m_emp}m {s_emp}s")
    st.sidebar.write("---")
    
    # Mostrar la última nota guardada en el historial
    ultima_nota = st.session_state.user_data['historial'][-1]
    
    if st.session_state.modo_actual == "Simulacro Oficial":
        st.sidebar.subheader(f"🏆 NOTA FINAL: {ultima_nota['nota']} / 10")
        st.sidebar.write("*(Revisa tu histórico para ver el registro completo)*")
    else:
        st.sidebar.subheader(f"🏆 NOTA FINAL: {ultima_nota['nota']} / 10")
    
    st.sidebar.write("---")
    if st.sidebar.button("Hacer otro examen"):
        st.session_state.corregido = False
        st.rerun()