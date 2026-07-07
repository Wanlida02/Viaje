
import streamlit as st
import requests
import pandas as pd
import folium
import json
import os
from streamlit_folium import st_folium
from streamlit_sortables import sort_items

st.set_page_config(page_title="Ruta Aerodromos Granada", layout="wide")

HOTEL = {"nombre": "B&B HOTEL Granada (Pulianas)", "lat": 37.2120987, "lon": -3.618852}

ORIGINAL_POINTS = [
    {"nombre": "Aeródromo de Atarfe", "lat": 37.2953081, "lon": -3.7140441, "dia": 1},
    {"nombre": "Aeropuerto Federico García Lorca Granada-Jaén", "lat": 37.1887, "lon": -3.7776, "dia": 1},
    {"nombre": "Aeródromo de Loja", "lat": 37.1377283, "lon": -4.2698833, "dia": 1},
    {"nombre": "Aeródromo Juan Espadafor", "lat": 37.08950, "lon": -3.78830, "dia": 2},
    {"nombre": "Helipuerto de Sierra Nevada", "lat": 37.0921041, "lon": -3.4003453, "dia": 2},
    {"nombre": "Helipuerto del CEDEFO La Resinera", "lat": 36.9352179, "lon": -3.8612064, "dia": 2},
    {"nombre": "Helipuerto del CEDEFO Puerto Lobo", "lat": 37.238648, "lon": -3.535132, "dia": 3},
    {"nombre": "Helipuerto Los Moralillos (Jerez del Marquesado)", "lat": 37.1848578, "lon": -3.1734565, "dia": 3},
    {"nombre": "Helipuerto de Baza", "lat": 37.4991954, "lon": -2.7527541, "dia": 3},
]

CONFIG_FILE = "config_guardada.json"

def points_to_state(points):
    puntos = {p["nombre"]: dict(p) for p in points}
    orden = {1: [], 2: [], 3: []}
    for p in points:
        orden[p["dia"]].append(p["nombre"])
    activos = {p["nombre"]: True for p in points}
    return puntos, orden, activos

def load_saved_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data["puntos"], {int(k): v for k, v in data["orden"].items()}, data["activos"]
        except Exception:
            return None
    return None

def save_current_config():
    data = {
        "puntos": st.session_state.puntos,
        "orden": st.session_state.orden,
        "activos": st.session_state.activos,
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_state():
    saved = load_saved_config()
    if saved:
        st.session_state.puntos, st.session_state.orden, st.session_state.activos = saved
    else:
        st.session_state.puntos, st.session_state.orden, st.session_state.activos = points_to_state(ORIGINAL_POINTS)
    st.session_state.version = st.session_state.get("version", 0) + 1

def reset_to_original():
    st.session_state.puntos, st.session_state.orden, st.session_state.activos = points_to_state(ORIGINAL_POINTS)
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    st.session_state.version = st.session_state.get("version", 0) + 1

def reset_to_saved():
    saved = load_saved_config()
    if saved:
        st.session_state.puntos, st.session_state.orden, st.session_state.activos = saved
        st.session_state.version = st.session_state.get("version", 0) + 1

if "puntos" not in st.session_state:
    init_state()

if "dia_activo" not in st.session_state:
    st.session_state.dia_activo = 1
if "pending_dia_activo" in st.session_state:
    st.session_state.dia_activo = st.session_state.pop("pending_dia_activo")

@st.cache_data(show_spinner=False)
def osrm_route(coords):
    coord_str = ";".join([f"{lon},{lat}" for lat, lon in coords])
    url = f"https://router.project-osrm.org/route/v1/driving/{coord_str}"
    params = {"overview": "full", "geometries": "geojson"}
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        route = data["routes"][0]
        return route["duration"], route["distance"], route["geometry"]["coordinates"]
    except Exception:
        return None, None, None

def gmaps_link(dia_puntos):
    puntos_coords = [f"{HOTEL['lat']},{HOTEL['lon']}"]
    for n in dia_puntos:
        p = st.session_state.puntos[n]
        puntos_coords.append(f"{p['lat']},{p['lon']}")
    puntos_coords.append(f"{HOTEL['lat']},{HOTEL['lon']}")
    return "https://www.google.com/maps/dir/" + "/".join(puntos_coords)

st.title("🗺️ Ruta dinámica: Aeródromos y Helipuertos de Granada")
st.caption("Planificación en 3 días partiendo y volviendo cada día al B&B HOTEL Granada (Pulianas). Arrastra los destinos para reordenarlos.")

with st.sidebar:
    st.header("⚙️ Configuración")

    saved_exists = os.path.exists(CONFIG_FILE)

    if st.button("💾 Guardar configuración actual como nueva por defecto", use_container_width=True, type="primary"):
        save_current_config()
        st.success("Configuración guardada. Ahora es la nueva configuración por defecto.")

    if saved_exists:
        if st.button("↩️ Restaurar última configuración guardada", use_container_width=True):
            reset_to_saved()
            st.rerun()

    if st.button("🔄 Restaurar configuración original (de fábrica)", use_container_width=True):
        reset_to_original()
        st.rerun()

    st.divider()
    st.subheader("Activar / desactivar destinos")
    for nombre in list(st.session_state.puntos.keys()):
        nuevo_val = st.checkbox(
            nombre, value=st.session_state.activos.get(nombre, True), key=f"chk_{nombre}"
        )
        if nuevo_val != st.session_state.activos.get(nombre, True):
            st.session_state.activos[nombre] = nuevo_val
            st.rerun()

todos_los_nombres = list(st.session_state.puntos.keys())
for d in [1, 2, 3]:
    st.session_state.orden[d] = [n for n in st.session_state.orden[d] if n in todos_los_nombres]
asignados = set()
for d in [1, 2, 3]:
    asignados.update(st.session_state.orden[d])
for n in todos_los_nombres:
    if n not in asignados:
        st.session_state.orden[1].append(n)

st.radio(
    "Selecciona el día a editar",
    options=[1, 2, 3],
    format_func=lambda x: f"📅 Día {x}",
    horizontal=True,
    key="dia_activo",
)

st.divider()

i = st.session_state.dia_activo
st.subheader(f"Día {i}")

activos_dia = [n for n in st.session_state.orden[i] if st.session_state.activos.get(n, True)]

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown("**Arrastra para reordenar la ruta del día**")
    if activos_dia:
        sort_key = f"sort_{i}_{st.session_state.version}_{len(activos_dia)}"
        sorted_items = sort_items(activos_dia, key=sort_key)
        if sorted_items and set(sorted_items) == set(activos_dia) and sorted_items != activos_dia:
            inactivos = [n for n in st.session_state.orden[i] if n not in activos_dia]
            st.session_state.orden[i] = sorted_items + inactivos
            dia_puntos = sorted_items
        else:
            dia_puntos = sorted_items if sorted_items else activos_dia
    else:
        dia_puntos = []
        st.info("No hay destinos activos este día.")

    st.markdown("**Mover un destino a otro día**")
    mc1, mc2, mc3 = st.columns([2, 1, 1])
    with mc1:
        mover_a_otro_dia = st.selectbox(
            "Destino a mover",
            options=["-- selecciona --"] + dia_puntos,
            key=f"mover_sel_{i}",
            label_visibility="collapsed",
        )
    with mc2:
        destino_dia = st.selectbox(
            "Día destino",
            options=[d for d in [1, 2, 3] if d != i],
            key=f"destino_dia_{i}",
            label_visibility="collapsed",
        )
    with mc3:
        mover_click = st.button("Mover ➡️", key=f"btn_mover_{i}", use_container_width=True)

    if mover_click and mover_a_otro_dia != "-- selecciona --":
        if mover_a_otro_dia in st.session_state.orden[i]:
            st.session_state.orden[i].remove(mover_a_otro_dia)
        if mover_a_otro_dia not in st.session_state.orden[destino_dia]:
            st.session_state.orden[destino_dia].append(mover_a_otro_dia)
        st.session_state.puntos[mover_a_otro_dia]["dia"] = destino_dia
        st.session_state.version += 1
        st.session_state.pending_dia_activo = destino_dia
        st.rerun()

if dia_puntos:
    coords = [(HOTEL["lat"], HOTEL["lon"])]
    for n in dia_puntos:
        p = st.session_state.puntos[n]
        coords.append((p["lat"], p["lon"]))
    coords.append((HOTEL["lat"], HOTEL["lon"]))

    duration, distance, geometry = osrm_route(coords)

    with col2:
        st.markdown("**Tiempo y distancia estimados**")
        if duration:
            st.metric("⏱️ Tiempo total conduciendo", f"{duration/3600:.1f} h")
            st.metric("📏 Distancia total", f"{distance/1000:.0f} km")
        else:
            st.warning("No se pudo calcular la ruta (servicio OSRM no disponible en este momento).")
        st.link_button("📍 Abrir esta ruta en Google Maps", gmaps_link(dia_puntos), use_container_width=True)

    m = folium.Map(location=[HOTEL["lat"], HOTEL["lon"]], zoom_start=9)
    folium.Marker([HOTEL["lat"], HOTEL["lon"]], popup="Hotel (inicio/fin)",
                  icon=folium.Icon(color="green", icon="home")).add_to(m)
    for idx, n in enumerate(dia_puntos, start=1):
        p = st.session_state.puntos[n]
        folium.Marker([p["lat"], p["lon"]], popup=f"{idx}. {n}",
                      icon=folium.DivIcon(html=f'<div style="background:#1f77b4;color:white;border-radius:50%;width:24px;height:24px;text-align:center;font-size:12px;">{idx}</div>')).add_to(m)
    if geometry:
        folium.PolyLine([(c[1], c[0]) for c in geometry], color="blue", weight=4, opacity=0.7).add_to(m)
    st_folium(m, height=450, width=None, key=f"map_{i}_{st.session_state.version}")

st.divider()
st.subheader("📊 Resumen del viaje completo")
rows = []
gtotal_dur = 0
gtotal_dist = 0
for d in [1, 2, 3]:
    dia_puntos_d = [n for n in st.session_state.orden[d] if st.session_state.activos.get(n, True)]
    if not dia_puntos_d:
        continue
    coords_d = [(HOTEL["lat"], HOTEL["lon"])] + [
        (st.session_state.puntos[n]["lat"], st.session_state.puntos[n]["lon"]) for n in dia_puntos_d
    ] + [(HOTEL["lat"], HOTEL["lon"])]
    duration_d, distance_d, _ = osrm_route(coords_d)
    if duration_d:
        gtotal_dur += duration_d
        gtotal_dist += distance_d
        rows.append({
            "Día": d,
            "Destinos": " → ".join(dia_puntos_d),
            "Tiempo (h)": round(duration_d / 3600, 1),
            "Distancia (km)": round(distance_d / 1000, 0),
            "Google Maps": gmaps_link(dia_puntos_d),
        })
if rows:
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={"Google Maps": st.column_config.LinkColumn("Google Maps", display_text="Abrir ruta")},
    )
    c1, c2 = st.columns(2)
    c1.metric("⏱️ Tiempo total viaje", f"{gtotal_dur/3600:.1f} h")
    c2.metric("📏 Distancia total viaje", f"{gtotal_dist/1000:.0f} km")
else:
    st.info("Activa destinos en los días para ver el resumen.")

st.caption("Coordenadas verificadas manualmente por el usuario en Google Maps. Tiempos estimados con OSRM (sin tráfico en tiempo real). Verifica horarios de apertura antes de viajar.")
