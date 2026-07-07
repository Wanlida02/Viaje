
import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ruta Aerodromos Granada", layout="wide")

HOTEL = {"nombre": "B&B HOTEL Granada (Pulianas)", "lat": 37.2264, "lon": -3.6089}

DEFAULT_POINTS = [
    {"nombre": "Aeródromo Juan Espadafor", "lat": 37.0895, "lon": -3.7883, "dia": 3},
    {"nombre": "Aeropuerto Federico García Lorca Granada-Jaén", "lat": 37.1887, "lon": -3.7776, "dia": 1},
    {"nombre": "Aeródromo de Atarfe", "lat": 37.2270, "lon": -3.6883, "dia": 1},
    {"nombre": "Aeródromo de Loja", "lat": 37.1710, "lon": -4.1490, "dia": 1},
    {"nombre": "Helipuerto de Baza", "lat": 37.4930, "lon": -2.7660, "dia": 2},
    {"nombre": "Helipuerto Los Moralillos (Jerez del Marquesado)", "lat": 37.2280, "lon": -3.2560, "dia": 2},
    {"nombre": "Helipuerto del CEDEFO La Resinera", "lat": 37.1180, "lon": -3.4300, "dia": 3},
    {"nombre": "Helipuerto del CEDEFO Puerto Lobo", "lat": 37.0900, "lon": -3.3700, "dia": 3},
    {"nombre": "Helipuerto de Sierra Nevada", "lat": 37.0960, "lon": -3.3980, "dia": 3},
]

if "puntos" not in st.session_state:
    st.session_state.puntos = {p["nombre"]: dict(p) for p in DEFAULT_POINTS}
if "orden" not in st.session_state:
    st.session_state.orden = {1: [], 2: [], 3: []}
    for p in DEFAULT_POINTS:
        st.session_state.orden[p["dia"]].append(p["nombre"])
if "activos" not in st.session_state:
    st.session_state.activos = {p["nombre"]: True for p in DEFAULT_POINTS}

def reset_defaults():
    st.session_state.puntos = {p["nombre"]: dict(p) for p in DEFAULT_POINTS}
    st.session_state.orden = {1: [], 2: [], 3: []}
    for p in DEFAULT_POINTS:
        st.session_state.orden[p["dia"]].append(p["nombre"])
    st.session_state.activos = {p["nombre"]: True for p in DEFAULT_POINTS}

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

st.title("🗺️ Ruta dinámica: Aeródromos y Helipuertos de Granada")
st.caption("Planificación en 3 días partiendo y volviendo cada día al B&B HOTEL Granada (Pulianas)")

with st.sidebar:
    st.header("⚙️ Configuración")
    if st.button("🔄 Restaurar configuración por defecto", use_container_width=True):
        reset_defaults()
        st.rerun()
    st.divider()
    st.subheader("Activar / desactivar destinos")
    for nombre in list(st.session_state.puntos.keys()):
        st.session_state.activos[nombre] = st.checkbox(
            nombre, value=st.session_state.activos.get(nombre, True), key=f"chk_{nombre}"
        )

tabs = st.tabs(["📅 Día 1", "📅 Día 2", "📅 Día 3", "📊 Resumen 3 días"])

total_dur_all = 0
total_dist_all = 0

for i, tab in enumerate(tabs[:3], start=1):
    with tab:
        st.subheader(f"Día {i}")
        dia_puntos = [n for n in st.session_state.orden[i] if st.session_state.activos.get(n, True)]

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**Orden de visita (arrastra en la lista para reordenar)**")
            nuevo_orden = st.multiselect(
                f"Orden día {i}",
                options=st.session_state.orden[i],
                default=dia_puntos,
                key=f"orden_ms_{i}",
                help="Elimina, añade o cambia el orden clicando; el orden de selección define la ruta.",
            )
            if nuevo_orden:
                dia_puntos = nuevo_orden

            mover_a_otro_dia = st.selectbox(
                "Mover un destino a otro día",
                options=["-- selecciona --"] + dia_puntos,
                key=f"mover_{i}",
            )
            destino_dia = st.selectbox("Nuevo día", options=[1, 2, 3], key=f"destino_dia_{i}")
            if mover_a_otro_dia != "-- selecciona --" and st.button("Mover", key=f"btn_mover_{i}"):
                st.session_state.orden[i].remove(mover_a_otro_dia)
                st.session_state.orden[destino_dia].append(mover_a_otro_dia)
                st.session_state.puntos[mover_a_otro_dia]["dia"] = destino_dia
                st.rerun()

        if not dia_puntos:
            st.info("No hay destinos activos este día.")
            continue

        coords = [(HOTEL["lat"], HOTEL["lon"])]
        for n in dia_puntos:
            p = st.session_state.puntos[n]
            coords.append((p["lat"], p["lon"]))
        coords.append((HOTEL["lat"], HOTEL["lon"]))

        duration, distance, geometry = osrm_route(coords)

        with col2:
            st.markdown("**Tiempo y distancia estimados**")
            if duration:
                horas = duration / 3600
                km = distance / 1000
                st.metric("⏱️ Tiempo total conduciendo", f"{horas:.1f} h")
                st.metric("📏 Distancia total", f"{km:.0f} km")
                total_dur_all += duration
                total_dist_all += distance
            else:
                st.warning("No se pudo calcular la ruta (servicio OSRM no disponible en este momento).")

        m = folium.Map(location=[HOTEL["lat"], HOTEL["lon"]], zoom_start=9)
        folium.Marker([HOTEL["lat"], HOTEL["lon"]], popup="Hotel (inicio/fin)",
                      icon=folium.Icon(color="green", icon="home")).add_to(m)
        for idx, n in enumerate(dia_puntos, start=1):
            p = st.session_state.puntos[n]
            folium.Marker([p["lat"], p["lon"]], popup=f"{idx}. {n}",
                          icon=folium.DivIcon(html=f'<div style="background:#1f77b4;color:white;border-radius:50%;width:24px;height:24px;text-align:center;font-size:12px;">{idx}</div>')).add_to(m)
        if geometry:
            folium.PolyLine([(c[1], c[0]) for c in geometry], color="blue", weight=4, opacity=0.7).add_to(m)
        st_folium(m, height=450, width=None, key=f"map_{i}")

        gmaps_url = "https://www.google.com/maps/dir/" + "/".join(
            [f"{HOTEL['lat']},{HOTEL['lon']}"] +
            [f"{st.session_state.puntos[n]['lat']},{st.session_state.puntos[n]['lon']}" for n in dia_puntos] +
            [f"{HOTEL['lat']},{HOTEL['lon']}"]
        )
        st.link_button("📍 Abrir esta ruta en Google Maps", gmaps_url, use_container_width=True)

with tabs[3]:
    st.subheader("Resumen del viaje completo")
    rows = []
    gtotal_dur = 0
    gtotal_dist = 0
    for d in [1, 2, 3]:
        dia_puntos = [n for n in st.session_state.orden[d] if st.session_state.activos.get(n, True)]
        if not dia_puntos:
            continue
        coords = [(HOTEL["lat"], HOTEL["lon"])] + [
            (st.session_state.puntos[n]["lat"], st.session_state.puntos[n]["lon"]) for n in dia_puntos
        ] + [(HOTEL["lat"], HOTEL["lon"])]
        duration, distance, _ = osrm_route(coords)
        if duration:
            gtotal_dur += duration
            gtotal_dist += distance
            rows.append({
                "Día": d,
                "Destinos": " → ".join(dia_puntos),
                "Tiempo (h)": round(duration / 3600, 1),
                "Distancia (km)": round(distance / 1000, 0),
            })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        c1, c2 = st.columns(2)
        c1.metric("⏱️ Tiempo total viaje", f"{gtotal_dur/3600:.1f} h")
        c2.metric("📏 Distancia total viaje", f"{gtotal_dist/1000:.0f} km")
    else:
        st.info("Activa destinos en los días para ver el resumen.")

st.divider()
st.caption("Los tiempos son estimaciones de conducción (OSRM, red pública, sin tráfico en tiempo real). Verifica horarios de apertura de cada aeródromo/helipuerto antes de viajar.")
