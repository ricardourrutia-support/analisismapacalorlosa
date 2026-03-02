import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
from datetime import timedelta

st.set_page_config(page_title="Dashboard de Operaciones Aeropuerto", layout="wide")

st.title("Análisis Operativo: Aeropuerto ✈️")
st.markdown("Selecciona el tipo de estudio que deseas realizar y luego carga el archivo CSV correspondiente.")

# 1. Selector del tipo de análisis
tipo_analisis = st.radio(
    "¿Qué quieres estudiar hoy?",
    ("Distribución espera en losa (+30 min)", "Distribución de la impuntualidad (Off Time)")
)

# Diccionario para traducir meses
MESES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto', 
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

# Color morado estilo Cabify
CABIFY_PURPLE = "#7142FF"
cabify_cmap = sns.light_palette(CABIFY_PURPLE, as_cmap=True)

uploaded_file = st.file_uploader("Carga tu archivo CSV aquí", type=['csv'])

if uploaded_file is not None:
    try:
        # Lectura base
        df = pd.read_csv(uploaded_file, sep=';')
        df['tm_start_local_at'] = pd.to_datetime(df['tm_start_local_at'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df = df.dropna(subset=['tm_start_local_at'])
        
        # 2. Lógica y filtrado dinámico según la selección del usuario
        if tipo_analisis == "Distribución espera en losa (+30 min)":
            # Validación de seguridad
            if 'Segmento Tiempo en Losa' not in df.columns:
                st.error("⚠️ El archivo cargado no parece ser el de 'Espera en Losa' (falta la columna requerida). Verifica el archivo o cambia el tipo de análisis arriba.")
                st.stop()
            
            categorias_espera = ['03. 30 - 45 min', '04. 45+']
            filtered_df = df[df['Segmento Tiempo en Losa'].isin(categorias_espera)].copy()
            
            # Variables de texto dinámico para este análisis
            titulo_metrica = "Pasajeros Afectados (+30 min)"
            texto_resumen = "experimentaron esperas superiores a 30 minutos en losa."
            nombre_archivo_excel = "reporte_espera_losa_cabify.xlsx"
            
        else: # Distribución de la impuntualidad (Off Time)
            # Validación de seguridad
            if 'Segment Arrived to Airport vs Requested' not in df.columns:
                st.error("⚠️ El archivo cargado no parece ser el de 'On Time' (falta la columna requerida). Verifica el archivo o cambia el tipo de análisis arriba.")
                st.stop()
                
            filtered_df = df[df['Segment Arrived to Airport vs Requested'] != '02. A tiempo (0-20 min antes)'].copy()
            
            # Variables de texto dinámico para este análisis
            titulo_metrica = "Pasajeros Impuntuales (Off Time)"
            texto_resumen = "llegaron al aeropuerto con un desfase importante respecto a su solicitud inicial (muy antes o muy tarde)."
            nombre_archivo_excel = "reporte_impuntualidad_cabify.xlsx"

        if filtered_df.empty:
            st.warning("No se encontraron registros que cumplan con los criterios para este análisis en el archivo subido.")
        else:
            # Extraer variables temporales
            filtered_df['hour'] = filtered_df['tm_start_local_at'].dt.hour
            filtered_df['day_of_week_num'] = filtered_df['tm_start_local_at'].dt.dayofweek
            dias_espanol = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
            filtered_df['day_of_week'] = filtered_df['day_of_week_num'].map(dias_espanol)
            filtered_df['week'] = filtered_df['tm_start_local_at'].dt.isocalendar().week

            # --- Resumen Ejecutivo Automático ---
            st.header("📝 Resumen Ejecutivo")
            total_afectados = filtered_df['# Riders'].sum()
            
            pico_global = filtered_df.groupby(['day_of_week', 'hour'])['# Riders'].sum().idxmax()
            pico_global_valor = filtered_df.groupby(['day_of_week', 'hour'])['# Riders'].sum().max()
            
            peor_semana_datos = filtered_df.groupby('week')['# Riders'].sum()
            peor_semana = peor_semana_datos.idxmax()
            peor_semana_valor = peor_semana_datos.max()
            
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric(f"Total {titulo_metrica}", f"{total_afectados:,}")
            col_res2.metric("Pico Crítico (Global)", f"{pico_global[0]} a las {pico_global[1]}:00", f"{pico_global_valor} casos")
            col_res3.metric("Semana más crítica", f"Semana {peor_semana}", f"{peor_semana_valor} casos")
            
            st.markdown(f"> **Análisis rápido:** Durante el periodo evaluado, un total de **{total_afectados} pasajeros** {texto_resumen} El momento de mayor tensión operativa a nivel general ocurrió los días **{pico_global[0]} a las {pico_global[1]}:00 horas**, acumulando un total de {pico_global_valor} casos. La semana que presentó mayores desafíos fue la **Semana {peor_semana}**.")
            st.divider()

            # --- Preparar Excel en memoria ---
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            workbook = writer.book
            pct_format = workbook.add_format({'num_format': '0.00%'})
            
            filtered_df.to_excel(writer, sheet_name='Detalle_Completo', index=False)

            # --- Generar Mapas de Calor por Semana ---
            semanas = sorted(filtered_df['week'].unique())
            days_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

            for week in semanas:
                week_df = filtered_df[filtered_df['week'] == week]
                
                # Calcular rango de fechas
                una_fecha = week_df['tm_start_local_at'].iloc[0]
                lunes = una_fecha - timedelta(days=una_fecha.weekday())
                domingo = lunes + timedelta(days=6)
                mes_lunes = MESES[lunes.month]
                mes_domingo = MESES[domingo.month]
                
                if lunes.month == domingo.month:
                    titulo_semana = f"Semana {week}: {lunes.day} al {domingo.day} de {mes_lunes} de {lunes.year}"
                else:
                    titulo_semana = f"Semana {week}: {lunes.day} de {mes_lunes} al {domingo.day} de {mes_domingo} de {domingo.year}"
                
                st.subheader(titulo_semana)

                # Tablas dinámicas
                pivot_abs = week_df.pivot_table(index='day_of_week', columns='hour', values='# Riders', aggfunc='sum').reindex(days_order)
                for h in range(24):
                    if h not in pivot_abs.columns:
                        pivot_abs[h] = 0
                pivot_abs = pivot_abs[range(24)].fillna(0)
                
                total_pasajeros_semana = pivot_abs.values.sum()
                pivot_pct_web = (pivot_abs / total_pasajeros_semana) * 100 if total_pasajeros_semana > 0 else pivot_abs
                pivot_pct_excel = (pivot_abs / total_pasajeros_semana) if total_pasajeros_semana > 0 else pivot_abs

                # Guardar en Excel con color
                pivot_abs.to_excel(writer, sheet_name=f'S{week}_Absoluto')
                pivot_pct_excel.to_excel(writer, sheet_name=f'S{week}_Porcentaje')
                
                filas_excel = len(pivot_abs)
                cols_excel = len(pivot_abs.columns)
                
                ws_abs = writer.sheets[f'S{week}_Absoluto']
                ws_abs.conditional_format(1, 1, filas_excel, cols_excel, 
                                          {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': CABIFY_PURPLE})
                
                ws_pct = writer.sheets[f'S{week}_Porcentaje']
                ws_pct.set_column(1, cols_excel, None, pct_format)
                ws_pct.conditional_format(1, 1, filas_excel, cols_excel, 
                                          {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': CABIFY_PURPLE})

                # Visualización en la web
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Volumen Absoluto - {titulo_metrica}**")
                    fig1, ax1 = plt.subplots(figsize=(10, 5))
                    sns.heatmap(pivot_abs, ax=ax1, cmap=cabify_cmap, annot=True, fmt='g', linewidths=.5)
                    ax1.set_xlabel('Hora del Día')
                    ax1.set_ylabel('Día de la Semana')
                    st.pyplot(fig1)
                    
                with col2:
                    st.markdown("**Distribución Relativa (%)**")
                    fig2, ax2 = plt.subplots(figsize=(10, 5))
                    sns.heatmap(pivot_pct_web, ax=ax2, cmap=cabify_cmap, annot=True, fmt='.2f', linewidths=.5)
                    for t in ax2.texts:
                        texto_actual = t.get_text()
                        t.set_text(texto_actual.replace('.', ',') + "%")
                    ax2.set_xlabel('Hora del Día')
                    ax2.set_ylabel('')
                    st.pyplot(fig2)
                    
                st.write("") 

            # --- Cierre y Descarga ---
            writer.close()
            excel_data = output.getvalue()
            
            st.divider()
            st.subheader("📥 Descargar Reporte")
            st.markdown("Descarga el Excel con las pestañas coloreadas y listas para presentar.")
            st.download_button(
                label="Descargar Reporte en Excel",
                data=excel_data,
                file_name=nombre_archivo_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Ocurrió un error general: {e}")
        st.markdown("Por favor revisa el archivo subido.")
