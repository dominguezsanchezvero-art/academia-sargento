import os
import random
import re
import time
import json
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

st.set_page_config(page_title="Academia Sargento Madrid", layout="wide", page_icon="🚒")

# ==========================================
# 📖 DICCIONARIO OFICIAL DE TEMAS (NOMBRE COMPLETO)
# ==========================================
NOMBRES_TEMAS = {
    1: "Tema 01 - Prevención de Riesgos Laborales y EPIs",
    2: "Tema 02 - Igualdad de Género y Colectivo LGTBI",
    3: "Tema 03 - Hidráulica y Bombas contra Incendios",
    4: "Tema 04 - Incendios Estructurales (GTV)",
    5: "Tema 05 - Incendios Bajo Rasante y Edificios de Gran Altura (EGA / CTE)",
    6: "Tema 06 - Patología de la Edificación",
    7: "Tema 07 - Rescate en Accidentes de Tráfico",
    8: "Tema 08 - Riesgo RBQ, MMPP y Funciones en Arbolado",
    9: "Tema 09 - Maniobras: Hidráulicas, Orientación y MAYDAY",
    10: "Tema 10 - Maniobras: ERA y Rescate en Altura",
    11: "Tema 11 - Maniobras: Arbolado, RBQ y Asistencia Sanitaria",
    12: "Tema 12 - P.O.: Seguridad Operativa, Estructura y Radiocomunicaciones",
    13: "Tema 13 - P.O.: NRBQ (Equipamiento, Zonificación y Descontaminación)",
    14: "Tema 14 - P.O.: Suicidio, Accesos Forzados y Colapsadas",
    15: "Tema 15 - P.O.: EBIIE, Control ERA, Rescate de Bomberos y Espumas",
    16: "Tema 16 - Planes de Intervención: Mando, Sobre Rasante y Tráfico",
    17: "Tema 17 - Planes de Intervención: Sustancias Peligrosas y Ascensores",
    18: "Tema 18 - Procedimientos Conjuntos (CAM, SAMUR y Código PIC)",
    19: "Tema 19 - Soporte Vital Básico y Procedimientos Sanitarios",
    20: "Tema 20 - Vehículos del SEI y Dotaciones de Material"
}

def formatear_tema(num_tema):
    return NOMBRES_TEMAS.get(num_tema, f"Tema {num_tema:02d}")

# ==========================================
# 👥 1. ACCESO Y CONTROL DE USUARIOS
# ==========================================
USUARIOS_VALIDOS = ["Dani", "Emilio", "Iñaki"]
PASSWORD_MAESTRA = "sargento2026"

def check_auth():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
        st.session_state["usuario_activo"] = None

    if not st.session_state["autenticado"]:
        st.markdown("<h2 style='text-align: center; color: #ff4b4b;'>🚒 Oposición Sargento Bomberos Madrid</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.1em;'>Acceso exclusivo a la plataforma de test y simulacros oficiales</p>", unsafe_allow_html=True)
        st.write("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info("Introduce tus credenciales para acceder a tu perfil personalizado:")
            user_sel = st.selectbox("👤 Selecciona tu usuario:", USUARIOS_VALIDOS, key="sel_user")
            pass_input = st.text_input("🔑 Contraseña:", type="password", key="pwd_input")
            
            if st.button("Entrar a la Academia", type="primary", use_container_width=True):
                if pass_input == PASSWORD_MAESTRA:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_activo"] = user_sel
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta.")
        st.stop()

check_auth()
usuario_actual = st.session_state["usuario_activo"]

# ==========================================
# ☁️ 2. GESTIÓN DE MEMORIA (GOOGLE SHEETS CON FALLBACK LOCAL)
# ==========================================
USAR_GSHEETS = False
conn = None
try:
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
    USAR_GSHEETS = True
except Exception:
    USAR_GSHEETS = False

def cargar_memoria_usuario(user):
    nombre_fichero_seguro = user.lower().replace("ñ", "n").replace("á", "a").replace("í", "i")
    fallos_file = f"fallos_{nombre_fichero_seguro}.json"
    
    fallos_locales = []
    if os.path.exists(fallos_file):
        try:
            with open(fallos_file, "r", encoding="utf-8") as f:
                fallos_locales = json.load(f)
        except:
            fallos_locales = []

    historial_usuario = []
    stats_temas = {}

    if USAR_GSHEETS and conn is not None:
        try:
            df = conn.read(ttl=5)
            if df is not None and not df.empty and "Usuario" in df.columns:
                df_user = df[df["Usuario"] == user]
                for _, row in df_user.iterrows():
                    historial_usuario.append({
                        "fecha": str(row.get("Fecha", "")),
                        "modo": str(row.get("Modo", "")),
                        "detalles": str(row.get("Detalles", "")),
                        "nota": float(row.get("Nota_Final", 0.0)),
                        "nota_t": float(row.get("Nota_Teorica", 0.0)),
                        "nota_p": float(row.get("Nota_Practica", 0.0))
                    })
                if "Stats_JSON" in df_user.columns:
                    for s_raw in df_user["Stats_JSON"].dropna():
                        try:
                            s_dict = json.loads(s_raw)
                            for t_k, t_v in s_dict.items():
                                if t_k not in stats_temas:
                                    stats_temas[t_k] = {"aciertos": 0, "errores": 0}
                                stats_temas[t_k]["aciertos"] += t_v.get("aciertos", 0)
                                stats_temas[t_k]["errores"] += t_v.get("errores", 0)
                        except:
                            pass
        except Exception:
            pass

    local_hist_file = f"historial_{nombre_fichero_seguro}.json"
    if not historial_usuario and os.path.exists(local_hist_file):
        try:
            with open(local_hist_file, "r", encoding="utf-8") as f:
                data_local = json.load(f)
                historial_usuario = data_local.get("historial", [])
                stats_temas = data_local.get("estadisticas_temas", {})
        except:
            pass

    return {
        "historial": historial_usuario,
        "fallos": fallos_locales,
        "estadisticas_temas": stats_temas
    }

def guardar_resultado_examen(user, reg_hist, nuevos_stats_examen, lista_fallos):
    nombre_fichero_seguro = user.lower().replace("ñ", "n").replace("á", "a").replace("í", "i")
    
    fallos_file = f"fallos_{nombre_fichero_seguro}.json"
    with open(fallos_file, "w", encoding="utf-8") as f:
        json.dump(lista_fallos, f, ensure_ascii=False, indent=2)

    if USAR_GSHEETS and conn is not None:
        try:
            df_existente = conn.read(ttl=0)
            nueva_fila = pd.DataFrame([{
                "Fecha": reg_hist["fecha"],
                "Usuario": user,
                "Modo": reg_hist["modo"],
                "Detalles": reg_hist.get("detalles", ""),
                "Nota_Final": reg_hist["nota"],
                "Nota_Teorica": reg_hist.get("nota_t", 0.0),
                "Nota_Practica": reg_hist.get("nota_p", 0.0),
                "Stats_JSON": json.dumps(nuevos_stats_examen)
            }])
            if df_existente is not None and not df_existente.empty:
                df_total = pd.concat([df_existente, nueva_fila], ignore_index=True)
            else:
                df_total = nueva_fila
            conn.update(data=df_total)
        except Exception:
            pass

    local_hist_file = f"historial_{nombre_fichero_seguro}.json"
    data_local = {"historial": st.session_state.user_data["historial"], "estadisticas_temas": st.session_state.user_data["estadisticas_temas"]}
    with open(local_hist_file, "w", encoding="utf-8") as f:
        json.dump(data_local, f, ensure_ascii=False, indent=2)

if "user_data" not in st.session_state or st.session_state.get("current_loaded_user") != usuario_actual:
    st.session_state.user_data = cargar_memoria_usuario(usuario_actual)
    st.session_state.current_loaded_user = usuario_actual

# ==========================================
# 📂 3. CARGA Y PARSEO DE ARCHIVOS (CLAUDE / GEMINI)
# ==========================================
def safe_md(text):
    if not text: return ""
    return text.replace("<", "&lt;").replace(">", "&gt;")

def parsear_archivo(ruta_archivo, origen_nombre):
    if not os.path.exists(ruta_archivo):
        return [], [], []

    with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
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
            current_sup = {'id': f"SUP_{origen_nombre}_{sup_counter}", 'titulo': safe_md(titulo), 'contexto': safe_md(contexto), 'preguntas': [], 'bloques': set(), 'origen': origen_nombre}
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
                'justificacion': safe_md(sol_data['justificacion']),
                'origen': origen_nombre
            }
            
            todas_planas.append(q_obj)

            if q_obj['tipo'] == 'teorica':
                preguntas_teo.append(q_obj)
                current_sup = None
            else:
                if current_sup is None:
                    sup_counter += 1
                    current_sup = {'id': f"SUP_{origen_nombre}_{sup_counter}", 'titulo': f"SUPUESTO - {q_obj['bloque']}", 'contexto': "", 'preguntas': [], 'bloques': set(), 'origen': origen_nombre}
                    supuestos_pra.append(current_sup)
                current_sup['preguntas'].append(q_obj)
                current_sup['bloques'].add(bloque)

    return preguntas_teo, supuestos_pra, todas_planas

@st.cache_data
def cargar_todos_los_datos():
    f_claude = "banco_unificado.txt" if os.path.exists("banco_unificado.txt") else ("banco_claude.txt" if os.path.exists("banco_claude.txt") else None)
    f_gemini = "banco_gemini.txt" if os.path.exists("banco_gemini.txt") else None

    teo_c, pra_c, tod_c = parsear_archivo(f_claude, "Claude") if f_claude else ([], [], [])
    teo_g, pra_g, tod_g = parsear_archivo(f_gemini, "Gemini") if f_gemini else ([], [], [])

    return {
        "claude": {"teo": teo_c, "pra": pra_c, "todas": tod_c},
        "gemini": {"teo": teo_g, "pra": pra_g, "todas": tod_g},
        "tiene_claude": len(teo_c) > 0,
        "tiene_gemini": len(teo_g) > 0
    }

def get_supuesto_category(sup):
    bloques_texto = " ".join(sup['bloques']).lower() + " " + sup['titulo'].lower()
    if 'rasante' in bloques_texto: return 'rasante'
    if 'ega' in bloques_texto: return 'EGA'
    if 'tráfico' in bloques_texto or 'trafico' in bloques_texto: return 'Tráfico'
    if 'altura' in bloques_texto or 'suicidio' in bloques_texto: return 'Altura+Suicidio'
    if 'rbq' in bloques_texto or 'nrbq' in bloques_texto: return 'RBQ'
    if 'arbolado' in bloques_texto: return 'Arbolado'
    if 'sanitari' in bloques_texto or 'vital' in bloques_texto or 'svb' in bloques_texto: return 'Sanitario'
    if 'incendio' in bloques_texto: return 'Incendios' 
    return 'Otros'

datos_cargados = cargar_todos_los_datos()
banco_claude = datos_cargados["claude"]
banco_gemini = datos_cargados["gemini"]

# ==========================================
# 🎯 4. LÓGICA DE EXAMEN Y SIMULACRO REGLADO
# ==========================================
CUPO_TEORICO = {1:1, 2:1, 3:2, 4:4, 5:4, 6:3, 7:3, 8:3, 9:2, 10:1, 11:2, 12:2, 13:3, 14:2, 15:3, 16:2, 17:2, 18:2, 19:6, 20:2}
CATEGORIAS_PRA = ['Incendios', 'rasante', 'EGA', 'Tráfico', 'Altura+Suicidio', 'RBQ', 'Arbolado']

def generar_examen(modo, origen_teo, temas_sel, bloque_pra_sel, num_preg, uso_acumulado):
    if origen_teo == "Claude":
        banco_t = banco_claude["teo"]
    elif origen_teo == "Gemini":
        banco_t = banco_gemini["teo"]
    else:
        banco_t = banco_claude["teo"] + banco_gemini["teo"]

    banco_p = banco_claude["pra"]
    todas_p = banco_claude["todas"] + banco_gemini["todas"]

    if modo == "Simulacro Oficial":
        seleccion_teo = []
        for tema, cant in CUPO_TEORICO.items():
            cands = [p for p in banco_t if p['tema'] == tema]
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
                cands = [s for s in banco_p if get_supuesto_category(s) == cat]
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
                disp = [s for s in banco_p if s not in temp_pra]
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

    elif modo == "Test Teórico por Temas":
        cands = [p for p in banco_t if p['tema'] in temas_sel]
        random.shuffle(cands)
        return cands[:num_preg], []

    elif modo == "Test Práctico por Bloques":
        supuestos_filtrados = []
        for s in banco_p:
            if bloque_pra_sel == "Todos" or get_supuesto_category(s).lower() == bloque_pra_sel.lower():
                supuestos_filtrados.append(s)
        random.shuffle(supuestos_filtrados)
        return [], supuestos_filtrados[:num_preg]

    elif modo == "Repaso de Fallos":
        fallos_ids = st.session_state.user_data.get('fallos', [])
        cands = [p for p in todas_p if p['id'] in fallos_ids]
        random.shuffle(cands)
        return cands[:num_preg], []

    return [], []

# ==========================================
# 🖥️ 5. INTERFAZ Y NAVEGACIÓN
# ==========================================
if "uso_acumulado" not in st.session_state:
    st.session_state.uso_acumulado = {}
if "examen" not in st.session_state:
    st.session_state.examen = None
    st.session_state.corregido = False
    st.session_state.modo_actual = None
    st.session_state.origen_actual = None
    st.session_state.temas_activos = []

with st.sidebar:
    st.markdown(f"### 👤 Conectado: **{usuario_actual}**")
    if USAR_GSHEETS:
        st.caption("🟢 Conectado a base de datos en nube (Google Sheets)")
    else:
        st.caption("🟡 Almacenamiento local temporal")

    if st.button("Cerrar Sesión", type="secondary"):
        st.session_state["autenticado"] = False
        st.session_state["usuario_activo"] = None
        st.rerun()
    st.write("---")

    st.header("⚙️ Configuración del Test")
    modo = st.radio("Modo de estudio:", [
        "Simulacro Oficial", 
        "Test Teórico por Temas", 
        "Test Práctico por Bloques", 
        "Repaso de Fallos"
    ])

    origen_teo = "Claude"
    temas_sel = []
    bloque_pra_sel = "Todos"
    num_preg = 20

    if modo == "Simulacro Oficial":
        opciones_banco = ["Simulacro Oficial (Teórico Claude + Práctica)"]
        if datos_cargados["tiene_gemini"]:
            opciones_banco.append("Simulacro Oficial (Teórico Gemini + Práctica)")
        tipo_sim_sel = st.selectbox("Selecciona origen teórico del simulacro:", opciones_banco)
        origen_teo = "Gemini" if "Gemini" in tipo_sim_sel else "Claude"
        st.info("📋 **Estructura oficial:** 50 teóricas con distribución reglada + 16 prácticas en 105 minutos.")

    elif modo == "Test Teórico por Temas":
        opciones_fuente = ["Claude"]
        if datos_cargados["tiene_gemini"]:
            opciones_fuente.extend(["Gemini", "Mixto (Claude + Gemini)"])
        else:
            st.caption("ℹ️ Para activar Gemini, sube `banco_gemini.txt` a GitHub.")
        origen_teo = st.selectbox("Origen de preguntas teóricas:", opciones_fuente)
        
        banco_ref = banco_claude["teo"] if origen_teo == "Claude" else (banco_gemini["teo"] if origen_teo == "Gemini" else banco_claude["teo"] + banco_gemini["teo"])
        temas_disponibles = sorted(list(set(p['tema'] for p in banco_ref if p['tema'] is not None)))
        
        opciones_temas_map = {formatear_tema(t): t for t in temas_disponibles}
        nombres_sel = st.multiselect("Elige los temas:", list(opciones_temas_map.keys()), default=[list(opciones_temas_map.keys())[0]] if opciones_temas_map else [])
        temas_sel = [opciones_temas_map[n] for n in nombres_sel]
        num_preg = st.number_input("Número de preguntas:", min_value=5, max_value=100, value=20, step=5)

    elif modo == "Test Práctico por Bloques":
        st.caption("Práctica generada a partir de los supuestos oficiales (Claude).")
        categorias_disp = ["Todos", "Incendios", "rasante", "EGA", "Tráfico", "Altura+Suicidio", "RBQ", "Arbolado"]
        bloque_pra_sel = st.selectbox("Selecciona Bloque Práctico:", categorias_disp)
        num_preg = st.number_input("Cantidad de Supuestos:", min_value=1, max_value=10, value=2)

    elif modo == "Repaso de Fallos":
        num_fallos = len(st.session_state.user_data.get('fallos', []))
        st.info(f"Tienes **{num_fallos}** preguntas en tu lista de fallos personal.")
        if num_fallos > 0:
            num_preg = st.number_input("Preguntas a repasar:", min_value=1, max_value=num_fallos, value=min(20, num_fallos))
        else:
            num_preg = 0

    if st.button("Comenzar Examen", type="primary", use_container_width=True):
        if modo == "Repaso de Fallos" and num_preg == 0:
            st.error("¡No tienes preguntas falladas guardadas! Enhorabuena.")
        else:
            teo, pra = generar_examen(modo, origen_teo, temas_sel, bloque_pra_sel, num_preg, st.session_state.uso_acumulado)
            if not teo and not pra:
                st.error("No se han encontrado preguntas con los filtros seleccionados.")
            else:
                st.session_state.examen = {'teo': teo, 'pra': pra}
                st.session_state.corregido = False
                st.session_state.modo_actual = modo
                st.session_state.origen_actual = origen_teo
                st.session_state.temas_activos = temas_sel
                st.session_state.start_time = time.time()
                for k in list(st.session_state.keys()):
                    if k.startswith("resp_"): del st.session_state[k]
                st.rerun()

    # --- HISTORIAL PERSONAL CON DETALLES ---
    st.write("---")
    if st.session_state.user_data.get('historial'):
        with st.expander(f"📈 Notas de {usuario_actual}"):
            for h in reversed(st.session_state.user_data['historial'][-8:]):
                detalle = f" — *{h.get('detalles', '')}*" if h.get('detalles') else ""
                st.markdown(f"**{h['fecha']}** — {h['modo']}{detalle}\n\nNota: **{h['nota']} / 10**")

    # --- RADAR DE TEMAS (DÓNDE VAS MEJOR / PEOR) ---
    if st.session_state.user_data.get('estadisticas_temas'):
        with st.expander("📊 Rendimiento por Temas"):
            stats = st.session_state.user_data['estadisticas_temas']
            for t_num in sorted([int(k) for k in stats.keys() if k.isdigit()]):
                s_t = stats[str(t_num)]
                tot = s_t.get('aciertos', 0) + s_t.get('errores', 0)
                if tot > 0:
                    pct = int((s_t.get('aciertos', 0) / tot) * 100)
                    color = "🟢" if pct >= 75 else ("🟡" if pct >= 50 else "🔴")
                    st.write(f"{color} **T{t_num:02d}**: {pct}% aciertos ({s_t['aciertos']}/{tot})")

# ==========================================
# 📝 6. ÁREA DE REALIZACIÓN DEL EXAMEN
# ==========================================
if st.session_state.examen is None:
    st.markdown(f"## 🚒 Bienvenido al panel de estudio, **{usuario_actual}**")
    st.markdown("""
    Configura tu sesión en el panel lateral:
    - **Simulacro Oficial**: 50 preguntas teóricas con cupo exacto por temas + 16 preguntas prácticas.
    - **Test Teórico por Temas**: Selecciona los temas por su nombre y elige entre banco Claude o Gemini.
    - **Test Práctico por Bloques**: Entrena supuestos de Incendios, Bajo Rasante, EGA, Tráfico o RBQ.
    - **Repaso de Fallos**: Repasa tus preguntas falladas de forma independiente a tus compañeros.
    - **Rendimiento por Temas**: Consulta en el panel lateral tu % de acierto por tema para atacar donde vas más flojo.
    """)
    st.stop()

# Temporizador
if not st.session_state.corregido:
    minutos_totales = 105 if st.session_state.modo_actual == "Simulacro Oficial" else (int(len(st.session_state.examen['teo']) * 1.5) if st.session_state.examen['teo'] else 30)
    timer_html = f"""
    <div style="font-family: sans-serif; background-color: #262730; color: white; padding: 12px; border-radius: 8px; border-left: 5px solid #ff4b4b; text-align: center; margin-bottom: 20px;">
        <h3 style="margin:0; color: #ff4b4b;" id="clock">⏳ Calculando tiempo restante...</h3>
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
    components.html(timer_html, height=70)

# Formulario
if not st.session_state.corregido:
    with st.form("form_examen"):
        if st.session_state.examen['teo']:
            st.header(f"PARTE TEÓRICA ({len(st.session_state.examen['teo'])} Preguntas)")
            for i, p in enumerate(st.session_state.examen['teo'], 1):
                tema_lbl = f"[{formatear_tema(p['tema'])}]" if p.get('tema') else ""
                st.markdown(f"**{i}. {tema_lbl} {p['enunciado']}**")
                st.radio("Opciones", [
                    "- (En blanco)", 
                    f"A) {p['opciones'].get('A','')}", 
                    f"B) {p['opciones'].get('B','')}", 
                    f"C) {p['opciones'].get('C','')}"
                ], key=f"resp_{p['id']}", label_visibility="collapsed")
                st.divider()

        if st.session_state.examen['pra']:
            total_p = sum(len(s['preguntas']) for s in st.session_state.examen['pra'])
            st.header(f"PARTE PRÁCTICA ({total_p} Preguntas)")
            p_idx = 1
            for sup in st.session_state.examen['pra']:
                st.markdown(f"### 📋 {sup['titulo']}")
                if sup['contexto']: st.info(sup['contexto'])
                for p in sup['preguntas']:
                    st.markdown(f"**P{p_idx}. {p['enunciado']}**")
                    st.radio("Opciones", [
                        "- (En blanco)", 
                        f"A) {p['opciones'].get('A','')}", 
                        f"B) {p['opciones'].get('B','')}", 
                        f"C) {p['opciones'].get('C','')}"
                    ], key=f"resp_{p['id']}", label_visibility="collapsed")
                    p_idx += 1
                st.divider()

        if st.form_submit_button("Finalizar y Corregir Examen", type="primary"):
            st.session_state.tiempo_empleado = time.time() - st.session_state.start_time
            
            if 'estadisticas_temas' not in st.session_state.user_data:
                st.session_state.user_data['estadisticas_temas'] = {}

            aciertos_t, errores_t = 0, 0
            stats_este_examen = {}
            for p in st.session_state.examen['teo']:
                resp = st.session_state.get(f"resp_{p['id']}", "-")[0]
                t_str = str(p['tema']) if p.get('tema') else "otros"
                if t_str not in st.session_state.user_data['estadisticas_temas']:
                    st.session_state.user_data['estadisticas_temas'][t_str] = {'aciertos': 0, 'errores': 0}
                if t_str not in stats_este_examen:
                    stats_este_examen[t_str] = {'aciertos': 0, 'errores': 0}

                if resp == p['solucion']:
                    aciertos_t += 1
                    st.session_state.user_data['estadisticas_temas'][t_str]['aciertos'] += 1
                    stats_este_examen[t_str]['aciertos'] += 1
                    if p['id'] in st.session_state.user_data['fallos']:
                        st.session_state.user_data['fallos'].remove(p['id'])
                elif resp != "-":
                    errores_t += 1
                    st.session_state.user_data['estadisticas_temas'][t_str]['errores'] += 1
                    stats_este_examen[t_str]['errores'] += 1
                    if p['id'] not in st.session_state.user_data['fallos']:
                        st.session_state.user_data['fallos'].append(p['id'])

            aciertos_p, errores_p = 0, 0
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
            total_p = sum(len(s['preguntas']) for s in st.session_state.examen['pra'])

            nota_t = max(0.0, ((aciertos_t * 1) - (errores_t * 0.20)) / total_t * 10) if total_t > 0 else 0.0
            nota_p = max(0.0, ((aciertos_p * 1) - (errores_p * 0.20)) / total_p * 10) if total_p > 0 else 0.0

            if st.session_state.modo_actual == "Simulacro Oficial":
                nota_final = round((nota_t + nota_p) / 2, 2)
                detalles_txt = f"Simulacro {st.session_state.origen_actual}"
            elif total_t > 0:
                nota_final = round(nota_t, 2)
                if st.session_state.temas_activos:
                    t_nombres = ", ".join([f"T{t:02d}" for t in st.session_state.temas_activos])
                    detalles_txt = f"{st.session_state.origen_actual} [{t_nombres}]"
                else:
                    detalles_txt = f"{st.session_state.origen_actual}"
            else:
                nota_final = round(nota_p, 2)
                detalles_txt = "Parte Práctica"

            nuevo_registro = {
                "fecha": datetime.now().strftime("%d/%m %H:%M"),
                "modo": st.session_state.modo_actual,
                "detalles": detalles_txt,
                "nota": nota_final,
                "nota_t": round(nota_t, 2),
                "nota_p": round(nota_p, 2)
            }
            st.session_state.user_data['historial'].append(nuevo_registro)
            
            guardar_resultado_examen(usuario_actual, nuevo_registro, stats_este_examen, st.session_state.user_data['fallos'])

            st.session_state.corregido = True
            st.rerun()

# ==========================================
# 📊 7. RESULTADOS Y RETROALIMENTACIÓN
# ==========================================
else:
    st.header("📊 Solucionario y Corrección Detallada")
    hist_rec = st.session_state.user_data['historial'][-1]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nota Teórica", f"{hist_rec['nota_t']} / 10", delta="Mínimo 5.0" if hist_rec['nota_t'] >= 5 else "Suspenso", delta_color="normal" if hist_rec['nota_t'] >= 5 else "inverse")
    with col2:
        st.metric("Nota Práctica", f"{hist_rec['nota_p']} / 10", delta="Mínimo 5.0" if hist_rec['nota_p'] >= 5 else "Suspenso", delta_color="normal" if hist_rec['nota_p'] >= 5 else "inverse")
    with col3:
        st.metric("Nota Final Ponderada", f"{hist_rec['nota']} / 10")

    if st.session_state.modo_actual == "Simulacro Oficial":
        if hist_rec['nota_t'] >= 5.0 and hist_rec['nota_p'] >= 5.0:
            st.success("🎉 ¡APTO! Has superado el corte del 5,0 tanto en la parte teórica como en la práctica.")
        else:
            st.error("⚠️ NO APTO. Recuerda que las bases exigen un mínimo de 5,0 en la teórica Y un mínimo de 5,0 en la práctica de forma independiente.")

    st.write("---")

    if st.session_state.examen['teo']:
        st.subheader("Revisión Teórica")
        for i, p in enumerate(st.session_state.examen['teo'], 1):
            tema_lbl = f"[{formatear_tema(p['tema'])}]" if p.get('tema') else ""
            st.markdown(f"**{i}. {tema_lbl} {p['enunciado']}**")
            for letra in ['A', 'B', 'C']:
                if p['opciones'].get(letra): st.markdown(f"*{letra})* {p['opciones'][letra]}")
            
            resp_dada = st.session_state.get(f"resp_{p['id']}", "-")[0]
            corr = p['solucion']
            if resp_dada == "-":
                st.warning(f"⚪ No contestada. La correcta era la **{corr}**.")
            elif resp_dada == corr:
                st.success(f"✅ ¡Correcto! Marcaste **{resp_dada}**.")
            else:
                st.error(f"❌ Incorrecto. Marcaste **{resp_dada}** y la correcta es **{corr}**.")
            st.info(f"**Justificación:** {p['justificacion']}")
            st.divider()

    if st.session_state.examen['pra']:
        st.subheader("Revisión Práctica")
        p_idx = 1
        for sup in st.session_state.examen['pra']:
            st.markdown(f"### {sup['titulo']}")
            if sup['contexto']: st.info(sup['contexto'])
            for p in sup['preguntas']:
                st.markdown(f"**P{p_idx}. {p['enunciado']}**")
                for letra in ['A', 'B', 'C']:
                    if p['opciones'].get(letra): st.markdown(f"*{letra})* {p['opciones'][letra]}")
                
                resp_dada = st.session_state.get(f"resp_{p['id']}", "-")[0]
                corr = p['solucion']
                if resp_dada == "-":
                    st.warning(f"⚪ No contestada. La correcta era la **{corr}**.")
                elif resp_dada == corr:
                    st.success(f"✅ ¡Correcto! Marcaste **{resp_dada}**.")
                else:
                    st.error(f"❌ Incorrecto. Marcaste **{resp_dada}** y la correcta es **{corr}**.")
                st.info(f"**Justificación:** {p['justificacion']}")
                p_idx += 1
            st.divider()

    if st.button("Hacer otro examen", type="primary"):
        st.session_state.corregido = False
        st.session_state.examen = None
        st.rerun()
