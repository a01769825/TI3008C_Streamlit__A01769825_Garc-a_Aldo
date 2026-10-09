import io

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Explorador de operación",
    page_icon="📊",
    layout="wide",
)

# Columnas que el código necesita para filtrar, agrupar y graficar.
COLUMNAS_REQUERIDAS = ["Fecha", "Área", "Casos"]


def leer_csv(contenido: bytes) -> pd.DataFrame:
    """Lee un CSV desde bytes. Prueba UTF-8 y, si falla, Latin-1."""
    try:
        return pd.read_csv(io.BytesIO(contenido), encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(contenido), encoding="latin-1")


def validar_y_preparar(datos: pd.DataFrame) -> tuple[pd.DataFrame | None, str | None]:
    """Valida el DataFrame. Devuelve (datos_listos, None) o (None, mensaje_de_error)."""
    if datos.empty:
        return None, "El archivo no contiene filas."

    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in datos.columns]
    if faltantes:
        return None, (
            f"Faltan columnas obligatorias: {', '.join(faltantes)}. "
            f"El archivo trae: {', '.join(map(str, datos.columns))}."
        )

    datos = datos.copy()

    datos["Fecha"] = pd.to_datetime(datos["Fecha"], errors="coerce")
    fechas_invalidas = int(datos["Fecha"].isna().sum())
    if fechas_invalidas:
        return None, f"La columna Fecha tiene {fechas_invalidas} valores que no son fechas válidas."

    datos["Casos"] = pd.to_numeric(datos["Casos"], errors="coerce")
    casos_invalidos = int(datos["Casos"].isna().sum())
    if casos_invalidos:
        return None, f"La columna Casos tiene {casos_invalidos} valores que no son números."

    return datos, None


@st.cache_data
def cargar_datos_ejemplo() -> pd.DataFrame:
    """Carga los datos de ejemplo que se usan si el usuario no sube un archivo."""
    datos = pd.read_csv("datos_ejemplo.csv")
    datos["Fecha"] = pd.to_datetime(datos["Fecha"])
    return datos


st.title("Explorador de operación")
st.caption("Explora resultados por área con tus propios datos en CSV.")

# TODO OBLIGATORIO: escribe tu nombre completo.
st.write("**Desarrollado por:** Adrian Leverkühn")

# ----------------------------------------------------------------
# Barra lateral: carga del archivo y filtros
# ----------------------------------------------------------------
st.sidebar.header("Datos")
archivo = st.sidebar.file_uploader(
    "Cargar un archivo CSV",
    type="csv",
    help=f"Debe tener las columnas: {', '.join(COLUMNAS_REQUERIDAS)}.",
)

# Plantilla para que el usuario sepa qué columnas necesita su archivo
plantilla = pd.DataFrame({"Fecha": ["2024-01-01"], "Área": ["Ejemplo"], "Casos": [10]})
st.sidebar.download_button(
    "Descargar plantilla CSV",
    data=plantilla.to_csv(index=False).encode("utf-8-sig"),
    file_name="plantilla.csv",
    mime="text/csv",
)

if archivo is None:
    df = cargar_datos_ejemplo()
    st.sidebar.caption("Mostrando los datos de ejemplo. Sube un CSV para usar los tuyos.")
    origen = "datos_ejemplo.csv"
else:
    try:
        crudo = leer_csv(archivo.getvalue())
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        st.error(f"No se pudo leer el archivo como CSV: {error}")
        st.stop()

    df, mensaje_error = validar_y_preparar(crudo)
    if mensaje_error:
        st.error(f"Archivo no válido. {mensaje_error}")
        st.stop()

    st.sidebar.success(f"Archivo cargado: {archivo.name}")
    origen = archivo.name

st.sidebar.header("Filtros")

areas_disponibles = sorted(df["Área"].dropna().unique())
areas_seleccionadas = st.sidebar.multiselect(
    "Área",
    options=areas_disponibles,
    default=areas_disponibles,
)

fecha_min = df["Fecha"].min().date()
fecha_max = df["Fecha"].max().date()
rango = st.sidebar.date_input(
    "Rango de fechas",
    value=(fecha_min, fecha_max),
    min_value=fecha_min,
    max_value=fecha_max,
)

# Mientras el usuario elige, el rango puede traer solo una fecha
if isinstance(rango, tuple) and len(rango) == 2:
    inicio, fin = rango
else:
    inicio, fin = fecha_min, fecha_max

df_filtrado = df[
    df["Área"].isin(areas_seleccionadas)
    & df["Fecha"].between(pd.Timestamp(inicio), pd.Timestamp(fin))
].copy()

# ----------------------------------------------------------------
# Resultados
# ----------------------------------------------------------------
if df_filtrado.empty:
    st.warning("No hay datos con los filtros actuales. Revisa el área y el rango de fechas.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Total de casos", f"{df_filtrado['Casos'].sum():,.0f}")
col2.metric("Filas filtradas", len(df_filtrado))
col3.metric("Promedio de casos por fila", f"{df_filtrado['Casos'].mean():,.1f}")

st.subheader("Datos disponibles")
st.caption(f"Fuente: {origen} · {len(df_filtrado)} de {len(df)} filas con los filtros actuales.")
st.dataframe(df_filtrado, width="stretch", hide_index=True)

csv_filtrado = df_filtrado.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8-sig")
st.download_button(
    label="Descargar datos filtrados (CSV)",
    data=csv_filtrado,
    file_name="datos_filtrados.csv",
    mime="text/csv",
)

casos_por_fecha = (
    df_filtrado.groupby("Fecha", as_index=False)["Casos"]
    .sum()
    .sort_values("Fecha")
)

fig = px.line(
    casos_por_fecha,
    x="Fecha",
    y="Casos",
    markers=True,
    title="Casos por fecha",
)
st.plotly_chart(fig, width="stretch")
