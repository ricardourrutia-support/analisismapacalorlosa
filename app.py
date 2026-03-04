import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
from datetime import timedelta

st.set_page_config(page_title="Dashboard de Operaciones Aeropuerto", layout="wide")

st.title("Análisis Operativo: Aeropuerto ✈️")
st.markdown("Selecciona el tipo de estudio que deseas realizar y luego carga el archivo correspondiente.")

# 1. Selector del tipo de análisis
tipo_analisis = st.radio(
    "¿Qué quieres estudiar hoy?",
    (
        "Distribución espera en losa (+30 min)", 
        "Distribución de la impuntualidad (Off Time)",
        "Disponibilidad de Flota (Vans)"
    )
)

# Diccionario para traducir meses
MESES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto', 
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

# Colores y estilos
CABIFY_PURPLE = "#7142FF"
cabify_cmap = sns.light_palette(CABIFY_PURPLE, as_cmap=True)
VANS_BLUE = "#1E90FF"
vans_cmap = "Blues"

# AHORA ACEPTAMOS CSV Y XLSX
uploaded_file = st.file_uploader("Carga tu archivo aquí (CSV o Excel)", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # ==========================================
        # LECTURA ROBUSTA (CSV o Excel)
        # ==========================================
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        else:
            try:
                df = pd.read_csv(uploaded_file, sep=';')
                if len(df.columns) < 3:  # Probablemente era separado por comas
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, sep=',')
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=',')

        # ==========================================
        # LÓGICA: DISPONIBILIDAD DE FLOTA (VANS)
        # ==========================================
        if tipo_analisis == "Disponibilidad de Flota (Vans)":
            if 'Patente' not in df.columns or 'Fecha de Operación' not in df.columns:
                st.error("⚠️ El archivo cargado no parece ser el de 'Disponibilidad de Flota'. Verifica el archivo o cambia el tipo de análisis.")
                st.stop()
                
            df['Fecha de Operación'] = pd.to_datetime(df['Fecha de Operación'], errors='coerce')
            df['Hora'] = pd.to_numeric(df['Hora'], errors='coerce')
            df = df.dropna(subset=['Hora', 'Fecha de Operación'])
            
            # Agrupar por fecha y hora exacta
            daily_hourly = df.groupby(['Fecha de Operación', 'Hora'])['Patente'].nunique().reset_index()
            
            # Renombrar columnas para usar el mismo bucle de renderizado posterior
            daily_hourly['tm_start_local_at'] = daily_hourly['Fecha de Operación']
            daily_hourly['hour'] = daily_hourly['Hora']
            daily_hourly['valor_metrica'] = daily_hourly['Patente']
            filtered_df = daily_hourly.copy()
            
            titulo_metrica = "Promedio de Vans Activas"
            nombre_archivo_excel = "reporte_disponibilidad_vans.xlsx"
            agg_func = 'mean'
            color_map = vans_cmap
            excel_color = VANS_BLUE
            mostrar_porcentaje = False

            # --- Resumen Ejecutivo de Vans ---
            st.header("📝 Resumen Ejecutivo")
            if not filtered_df.empty:
                promedio_global = filtered_df['valor_metrica'].mean()
                dias_espanol = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
                filtered_df['day_of_week_num'] = filtered_df['tm_start_local_at'].dt.dayofweek
                filtered_df['day_of_week'] = filtered_df['day_of_week_num'].map(dias_espanol)
                
                pico_global = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].mean().idxmax()
                pico_global_valor = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].mean().max()
                
                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric("Promedio Global (Vans/Hora)", f"{promedio_global:.1f}")
                col_res2.metric("Pico de Disponibilidad", f"{pico_global[0]} a las {pico_global[1]}:00", f"{pico_global_valor:.1f} vans")
                col_res3.metric("Total Patentes Únicas", f"{df['Patente'].nunique()}")
                
                st.markdown(f"> **Análisis rápido:** La flota operativa mantiene un promedio de **{promedio_global:.1f} vans** activas por franja horaria. El bloque con mayor disponibilidad histórica es el **{pico_global[0]} a las {pico_global[1]}:00**.")
                st.divider()

        # ==========================================
        # LÓGICA: LOSA (+30 MIN) Y OFF TIME
        # ==========================================
        else:
            df['tm_start_local_at'] = pd.to_datetime(df['tm_start_local_at'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
            df = df.dropna(subset=['tm_start_local_at'])
            
            if tipo_analisis == "Distribución espera en losa (+30 min)":
                if 'Segmento Tiempo en Losa' not in df.columns:
                    st.error("⚠️ El archivo cargado no parece ser el de 'Espera en Losa'. Verifica el archivo.")
                    st.stop()
                categorias_espera = ['03. 30 - 45 min', '04. 45+']
                filtered_df = df[df['Segmento Tiempo en Losa'].isin(categorias_espera)].copy()
                titulo_metrica = "Pasajeros Afectados (+30 min)"
                texto_resumen = "experimentaron esperas superiores a 30 minutos en losa."
                nombre_archivo_excel = "reporte_espera_losa.xlsx"
                
            else: # Off Time
                if 'Segment Arrived to Airport vs Requested' not in df.columns:
                    st.error("⚠️ El archivo cargado no parece ser el de 'On Time'. Verifica el archivo.")
                    st.stop()
                filtered_df = df[df['Segment Arrived to Airport vs Requested'] != '02. A tiempo (0-20 min antes)'].copy()
                titulo_metrica = "Pasajeros Impuntuales (Off Time)"
                texto_resumen = "llegaron al aeropuerto con un desfase importante."
                nombre_archivo_excel = "reporte_impuntualidad.xlsx"

            filtered_df['hour'] = filtered_df['tm_start_local_at'].dt.hour
            filtered_df['valor_metrica'] = filtered_df['# Riders']
            agg_func = 'sum'
            color_map = cabify_cmap
            excel_color = CABIFY_PURPLE
            mostrar_porcentaje = True

            # --- Resumen Ejecutivo Losa/Off Time ---
            st.header("📝 Resumen Ejecutivo")
            if not filtered_df.empty:
                dias_espanol = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
                filtered_df['day_of_week_num'] = filtered_df['tm_start_local_at'].dt.dayofweek
                filtered_df['day_of_week'] = filtered_df['day_of_week_num'].map(dias_espanol)
                filtered_df['week'] = filtered_df['tm_start_local_at'].dt.isocalendar().week
                
                total_afectados = filtered_df['valor_metrica'].sum()
                pico_global = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].sum().idxmax()
                pico_global_valor = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].sum().max()
                
                peor_semana_datos = filtered_df.groupby('week')['valor_metrica'].sum()
                peor_semana = peor_semana_datos.idxmax()
                peor_semana_valor = peor_semana_datos.max()
                
                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric(f"Total {titulo_metrica}", f"{total_afectados:,.0f}")
                col_res2.metric("Pico Crítico (Global)", f"{pico_global[0]} a las {pico_global[1]}:00", f"{pico_global_valor:,.0f} casos")
                col_res3.metric("Semana más crítica", f"Semana {peor_semana}", f"{peor_semana_valor:,.0f} casos")
                
                st.markdown(f"> **Análisis rápido:** Durante el periodo evaluado, un total de **{total_afectados:,.0f} pasajeros** {texto_resumen} El momento de mayor tensión ocurrió los días **{pico_global[0]} a las {pico_global[1]}:00 horas**, acumulando un total de {pico_global_valor:,.0f} casos.")
                st.divider()

        # ==========================================
        # RENDERIZADO COMÚN DE MAPAS DE CALOR Y EXCEL
        # ==========================================
        if filtered_df.empty:
            st.warning("No se encontraron registros válidos para analizar en el archivo subido.")
        else:
            filtered_df['week'] = filtered_df['tm_start_local_at'].dt.isocalendar().week
            
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            workbook = writer.book
            pct_format = workbook.add_format({'num_format': '0.00%'})
            filtered_df.to_excel(writer, sheet_name='Detalle_Completo', index=False)

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

                # Pivot Absoluto / Promedio
                pivot_abs = week_df.pivot_table(index='day_of_week', columns='hour', values='valor_metrica', aggfunc=agg_func).reindex(days_order)
                for h in range(24):
                    if h not in pivot_abs.columns:
                        pivot_abs[h] = 0
                pivot_abs = pivot_abs[range(24)].fillna(0)
                
                # Guardar en Excel
                pivot_abs.to_excel(writer, sheet_name=f'S{week}_Absoluto')
                filas_excel = len(pivot_abs)
                cols_excel = len(pivot_abs.columns)
                ws_abs = writer.sheets[f'S{week}_Absoluto']
                ws_abs.conditional_format(1, 1, filas_excel, cols_excel, 
                                          {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': excel_color})
                
                # Dibujar gráficos web
                if mostrar_porcentaje:
                    col1, col2 = st.columns(2)
                    
                    # Gráfico 1: Absoluto
                    with col1:
                        st.markdown(f"**Volumen Absoluto - {titulo_metrica}**")
                        fig1, ax1 = plt.subplots(figsize=(10, 5))
                        sns.heatmap(pivot_abs, ax=ax1, cmap=color_map, annot=True, fmt='g', linewidths=.5)
                        ax1.set_xlabel('Hora del Día')
                        ax1.set_ylabel('Día de la Semana')
                        st.pyplot(fig1)
                        
                    # Gráfico 2: Porcentaje
                    with col2:
                        total_pasajeros_semana = pivot_abs.values.sum()
                        pivot_pct_web = (pivot_abs / total_pasajeros_semana) * 100 if total_pasajeros_semana > 0 else pivot_abs
                        pivot_pct_excel = (pivot_abs / total_pasajeros_semana) if total_pasajeros_semana > 0 else pivot_abs
                        
                        pivot_pct_excel.to_excel(writer, sheet_name=f'S{week}_Porcentaje')
                        ws_pct = writer.sheets[f'S{week}_Porcentaje']
                        ws_pct.set_column(1, cols_excel, None, pct_format)
                        ws_pct.conditional_format(1, 1, filas_excel, cols_excel, 
                                                  {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': excel_color})
                                                  
                        st.markdown("**Distribución Relativa (%)**")
                        fig2, ax2 = plt.subplots(figsize=(10, 5))
                        sns.heatmap(pivot_pct_web, ax=ax2, cmap=color_map, annot=True, fmt='.2f', linewidths=.5)
                        for t in ax2.texts:
                            texto_actual = t.get_text()
                            t.set_text(texto_actual.replace('.', ',') + "%")
                        ax2.set_xlabel('Hora del Día')
                        ax2.set_ylabel('')
                        st.pyplot(fig2)
                else:
                    # RENDERIZADO PARA VANS (Solo una columna central)
                    st.markdown(f"**{titulo_metrica}**")
                    fig1, ax1 = plt.subplots(figsize=(12, 4))
                    sns.heatmap(pivot_abs, ax=ax1, cmap=color_map, annot=True, fmt='.1f', linewidths=.5)
                    ax1.set_xlabel('Hora del Día')
                    ax1.set_ylabel('Día de la Semana')
                    st.pyplot(fig1)

                st.write("") 

            # --- Cierre y Descarga ---
            writer.close()
            excel_data = output.getvalue()
            
            st.divider()
            st.subheader("📥 Descargar Reporte")
            st.markdown("Descarga el Excel con las matrices generadas.")
            st.download_button(
                label="Descargar Reporte en Excel",
                data=excel_data,
                file_name=nombre_archivo_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Ocurrió un error general al procesar el archivo: {e}")
        st.markdown("Por favor revisa el archivo subido y asegúrate de que corresponda con el análisis seleccionado.")
