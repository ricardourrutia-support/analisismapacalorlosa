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
        "Disponibilidad de Flota (Vans)",
        "Demanda de Reservas (Ventas)"
    )
)

# Diccionario para traducir meses
MESES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto', 
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

# Colores y estilos corporativos
CABIFY_PURPLE = "#7142FF"
cabify_cmap = sns.light_palette(CABIFY_PURPLE, as_cmap=True)
VANS_BLUE = "#1E90FF"
vans_cmap = "Blues"

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
                if len(df.columns) < 3: 
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, sep=',')
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=',')

        dias_espanol = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}

        # ==========================================
        # LÓGICA: DISPONIBILIDAD DE FLOTA (VANS)
        # ==========================================
        if tipo_analisis == "Disponibilidad de Flota (Vans)":
            if 'Patente' not in df.columns or 'Fecha de Operación' not in df.columns:
                st.error("⚠️ El archivo cargado no parece ser el de 'Disponibilidad de Flota'.")
                st.stop()
                
            df['Fecha de Operación'] = pd.to_datetime(df['Fecha de Operación'], errors='coerce')
            df['Hora'] = pd.to_numeric(df['Hora'], errors='coerce')
            df = df.dropna(subset=['Hora', 'Fecha de Operación'])
            
            daily_hourly = df.groupby(['Fecha de Operación', 'Hora'])['Patente'].nunique().reset_index()
            daily_hourly['tm_start_local_at'] = daily_hourly['Fecha de Operación']
            daily_hourly['hour'] = daily_hourly['Hora']
            daily_hourly['valor_metrica'] = daily_hourly['Patente']
            
            daily_hourly['day_of_week_num'] = daily_hourly['tm_start_local_at'].dt.dayofweek
            daily_hourly['day_of_week'] = daily_hourly['day_of_week_num'].map(dias_espanol)
            daily_hourly['week'] = daily_hourly['tm_start_local_at'].dt.isocalendar().week
            
            filtered_df = daily_hourly.copy()
            df_for_excel = filtered_df.copy()
            
            titulo_metrica = "Promedio de Vans Activas"
            nombre_archivo_excel = "reporte_disponibilidad_vans.xlsx"
            agg_func = 'mean'
            color_map = vans_cmap
            excel_color = VANS_BLUE
            mostrar_porcentaje = False
            heatmap_fmt = '.1f'

            st.header("📝 Resumen Ejecutivo")
            if not filtered_df.empty:
                promedio_global = filtered_df['valor_metrica'].mean()
                pico_global = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].mean().idxmax()
                pico_global_valor = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].mean().max()
                
                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric("Promedio Global (Vans/Hora)", f"{promedio_global:.1f}")
                col_res2.metric("Pico de Disponibilidad", f"{pico_global[0]} a las {pico_global[1]}:00", f"{pico_global_valor:.1f} vans")
                col_res3.metric("Total Patentes Únicas", f"{df['Patente'].nunique()}")
                st.divider()

        # ==========================================
        # LÓGICA: DEMANDA DE RESERVAS (VENTAS)
        # ==========================================
        elif tipo_analisis == "Demanda de Reservas (Ventas)":
            if 'ds_product_name' not in df.columns or 'createdAt_local' not in df.columns:
                st.error("⚠️ El archivo cargado no parece ser la Base de Datos de Ventas.")
                st.stop()
            
            # Segmentador interactivo para la WEB
            st.markdown("### 📊 Segmentación de Demanda en Pantalla")
            tipo_demanda = st.selectbox(
                "Selecciona el tipo de servicio a visualizar aquí:",
                ("Compartida", "Exclusiva", "Total")
            )
            
            df_full_demanda = df[df['ds_product_name'].isin(['van_compartida', 'van_exclusive'])].copy()
            df_full_demanda['tm_start_local_at'] = pd.to_datetime(df_full_demanda['createdAt_local'], errors='coerce')
            df_full_demanda = df_full_demanda.dropna(subset=['tm_start_local_at'])
            
            df_full_demanda['hour'] = df_full_demanda['tm_start_local_at'].dt.hour
            df_full_demanda['valor_metrica'] = 1 
            df_full_demanda['Segmento'] = df_full_demanda['ds_product_name'].map({'van_compartida': 'Compartida', 'van_exclusive': 'Exclusiva'})
            df_full_demanda['day_of_week_num'] = df_full_demanda['tm_start_local_at'].dt.dayofweek
            df_full_demanda['day_of_week'] = df_full_demanda['day_of_week_num'].map(dias_espanol)
            df_full_demanda['week'] = df_full_demanda['tm_start_local_at'].dt.isocalendar().week
            
            df_for_excel = df_full_demanda.copy()

            if tipo_demanda == "Compartida":
                filtered_df = df_full_demanda[df_full_demanda['Segmento'] == 'Compartida'].copy()
                titulo_metrica = "Volumen de Reservas (Compartidas)"
                color_map = "Greens"
            elif tipo_demanda == "Exclusiva":
                filtered_df = df_full_demanda[df_full_demanda['Segmento'] == 'Exclusiva'].copy()
                titulo_metrica = "Volumen de Reservas (Exclusivas)"
                color_map = "Oranges"
            else:
                filtered_df = df_full_demanda.copy()
                titulo_metrica = "Volumen de Reservas (Total)"
                color_map = "PuBuGn"
            
            nombre_archivo_excel = "reporte_ventas_interactivo.xlsx"
            agg_func = 'sum'
            excel_color = "#008080" # Teal Base para el Excel
            mostrar_porcentaje = False
            heatmap_fmt = 'g'

            st.header("📝 Resumen Ejecutivo")
            if not filtered_df.empty:
                total_afectados = filtered_df['valor_metrica'].sum()
                pico_global = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].sum().idxmax()
                pico_global_valor = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].sum().max()
                
                col_res1, col_res2 = st.columns(2)
                col_res1.metric(f"Total {titulo_metrica}", f"{total_afectados:,.0f}")
                col_res2.metric("Pico de Demanda", f"{pico_global[0]} a las {pico_global[1]}:00", f"{pico_global_valor:,.0f} reservas")
                st.divider()

        # ==========================================
        # LÓGICA: LOSA (+30 MIN) Y OFF TIME
        # ==========================================
        else:
            df['tm_start_local_at'] = pd.to_datetime(df['tm_start_local_at'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
            df = df.dropna(subset=['tm_start_local_at'])
            
            if tipo_analisis == "Distribución espera en losa (+30 min)":
                if 'Segmento Tiempo en Losa' not in df.columns:
                    st.error("⚠️ El archivo cargado no parece ser el de 'Espera en Losa'.")
                    st.stop()
                categorias_espera = ['03. 30 - 45 min', '04. 45+']
                filtered_df = df[df['Segmento Tiempo en Losa'].isin(categorias_espera)].copy()
                titulo_metrica = "Pasajeros Afectados (+30 min)"
                nombre_archivo_excel = "reporte_espera_losa.xlsx"
            else:
                if 'Segment Arrived to Airport vs Requested' not in df.columns:
                    st.error("⚠️ El archivo cargado no parece ser el de 'On Time'.")
                    st.stop()
                filtered_df = df[df['Segment Arrived to Airport vs Requested'] != '02. A tiempo (0-20 min antes)'].copy()
                titulo_metrica = "Pasajeros Impuntuales (Off Time)"
                nombre_archivo_excel = "reporte_impuntualidad.xlsx"

            filtered_df['hour'] = filtered_df['tm_start_local_at'].dt.hour
            filtered_df['valor_metrica'] = filtered_df['# Riders']
            filtered_df['day_of_week_num'] = filtered_df['tm_start_local_at'].dt.dayofweek
            filtered_df['day_of_week'] = filtered_df['day_of_week_num'].map(dias_espanol)
            filtered_df['week'] = filtered_df['tm_start_local_at'].dt.isocalendar().week
            
            df_for_excel = filtered_df.copy()
            agg_func = 'sum'
            color_map = cabify_cmap
            excel_color = CABIFY_PURPLE
            mostrar_porcentaje = True
            heatmap_fmt = 'g'

            st.header("📝 Resumen Ejecutivo")
            if not filtered_df.empty:
                total_afectados = filtered_df['valor_metrica'].sum()
                pico_global = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].sum().idxmax()
                pico_global_valor = filtered_df.groupby(['day_of_week', 'hour'])['valor_metrica'].sum().max()
                
                col_res1, col_res2 = st.columns(2)
                col_res1.metric(f"Total {titulo_metrica}", f"{total_afectados:,.0f}")
                col_res2.metric("Pico Crítico (Global)", f"{pico_global[0]} a las {pico_global[1]}:00", f"{pico_global_valor:,.0f} casos")
                st.divider()

        # ==========================================
        # RENDERIZADO DE EXCEL Y GRÁFICOS WEB
        # ==========================================
        if df_for_excel.empty:
            st.warning("No se encontraron registros válidos para analizar en el archivo subido.")
        else:
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            workbook = writer.book
            pct_format = workbook.add_format({'num_format': '0.00%'})
            bold_format = workbook.add_format({'bold': True, 'bg_color': '#f3f3f3', 'border': 1})
            
            df_for_excel.to_excel(writer, sheet_name='Detalle_Completo', index=False)

            # Si es reporte de ventas, creamos una hoja secundaria oculta para las fórmulas del Excel
            if tipo_analisis == "Demanda de Reservas (Ventas)":
                df_pivot_data = df_for_excel[['week', 'day_of_week', 'hour', 'Segmento', 'valor_metrica']].copy()
                df_pivot_data.to_excel(writer, sheet_name='Data_Pivot', index=False)
                writer.sheets['Data_Pivot'].hide()

            semanas = sorted(df_for_excel['week'].unique())
            days_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

            for week in semanas:
                week_df_excel = df_for_excel[df_for_excel['week'] == week]
                week_df_web = filtered_df[filtered_df['week'] == week] if not filtered_df.empty else pd.DataFrame()
                
                una_fecha = week_df_excel['tm_start_local_at'].iloc[0]
                lunes = una_fecha - timedelta(days=una_fecha.weekday())
                domingo = lunes + timedelta(days=6)
                mes_lunes = MESES[lunes.month]
                mes_domingo = MESES[domingo.month]
                if lunes.month == domingo.month:
                    titulo_semana = f"Semana {week}: {lunes.day} al {domingo.day} de {mes_lunes} de {lunes.year}"
                else:
                    titulo_semana = f"Semana {week}: {lunes.day} de {mes_lunes} al {domingo.day} de {mes_domingo} de {domingo.year}"
                
                st.subheader(titulo_semana)

                # --- 1. GENERAR PESTAÑAS EN EXCEL ---
                if tipo_analisis == "Demanda de Reservas (Ventas)":
                    ws_name = f'S{week}_Ventas_Interactivo'
                    ws = workbook.add_worksheet(ws_name)
                    
                    # Filtro Interactivo en Excel
                    ws.write('A1', 'Seleccione Segmento:', bold_format)
                    ws.data_validation('B1', {'validate': 'list', 'source': ['Compartida', 'Exclusiva', 'Total']})
                    ws.write('B1', 'Total', bold_format)
                    
                    # Dibujar cabeceras de matriz
                    ws.write('A3', 'Día / Hora', bold_format)
                    for c_idx, h in enumerate(range(24)):
                        ws.write(2, c_idx + 1, h, bold_format)
                        
                    for r_idx, day in enumerate(days_order):
                        ws.write(r_idx + 3, 0, day, bold_format)
                        for c_idx, h in enumerate(range(24)):
                            col_letter = chr(66 + c_idx) if c_idx < 25 else 'Z'
                            cell_hour = f'{col_letter}$3'
                            cell_day = f'$A{r_idx + 4}'
                            
                            # Fórmula mágica: SUMIFS condicionado al menú desplegable
                            formula = f'=IF($B$1="Total", SUMIFS(Data_Pivot!E:E, Data_Pivot!A:A, {week}, Data_Pivot!B:B, {cell_day}, Data_Pivot!C:C, {cell_hour}), SUMIFS(Data_Pivot!E:E, Data_Pivot!A:A, {week}, Data_Pivot!B:B, {cell_day}, Data_Pivot!C:C, {cell_hour}, Data_Pivot!D:D, $B$1))'
                            ws.write_formula(r_idx + 3, c_idx + 1, formula)
                            
                    # Colorear matriz con formato condicional
                    ws.conditional_format(3, 1, 9, 24, {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': excel_color})
                    
                else:
                    # Reportes estáticos habituales
                    pivot_abs = week_df_excel.pivot_table(index='day_of_week', columns='hour', values='valor_metrica', aggfunc=agg_func).reindex(days_order)
                    for h in range(24): 
                        if h not in pivot_abs.columns: pivot_abs[h] = 0
                    pivot_abs = pivot_abs[range(24)].fillna(0)
                    
                    pivot_abs.to_excel(writer, sheet_name=f'S{week}_Absoluto')
                    ws_abs = writer.sheets[f'S{week}_Absoluto']
                    ws_abs.conditional_format(1, 1, len(pivot_abs), len(pivot_abs.columns), 
                                              {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': excel_color})
                                              
                    if mostrar_porcentaje:
                        total_pasajeros_semana = pivot_abs.values.sum()
                        pivot_pct_excel = (pivot_abs / total_pasajeros_semana) if total_pasajeros_semana > 0 else pivot_abs
                        pivot_pct_excel.to_excel(writer, sheet_name=f'S{week}_Porcentaje')
                        ws_pct = writer.sheets[f'S{week}_Porcentaje']
                        ws_pct.set_column(1, len(pivot_abs.columns), None, pct_format)
                        ws_pct.conditional_format(1, 1, len(pivot_abs), len(pivot_abs.columns), 
                                                  {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': excel_color})

                # --- 2. GENERAR GRÁFICOS WEB ---
                if week_df_web.empty:
                    st.info("No hay registros para mostrar en esta semana según el filtro seleccionado.")
                    continue
                    
                pivot_web = week_df_web.pivot_table(index='day_of_week', columns='hour', values='valor_metrica', aggfunc=agg_func).reindex(days_order)
                for h in range(24): 
                    if h not in pivot_web.columns: pivot_web[h] = 0
                pivot_web = pivot_web[range(24)].fillna(0)

                if mostrar_porcentaje:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Volumen Absoluto - {titulo_metrica}**")
                        fig1, ax1 = plt.subplots(figsize=(10, 5))
                        sns.heatmap(pivot_web, ax=ax1, cmap=color_map, annot=True, fmt=heatmap_fmt, linewidths=.5)
                        ax1.set_xlabel('Hora del Día')
                        ax1.set_ylabel('Día de la Semana')
                        st.pyplot(fig1)
                        
                    with col2:
                        total_pasajeros_web = pivot_web.values.sum()
                        pivot_pct_web = (pivot_web / total_pasajeros_web) * 100 if total_pasajeros_web > 0 else pivot_web
                                                  
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
                    st.markdown(f"**{titulo_metrica}**")
                    fig1, ax1 = plt.subplots(figsize=(12, 4))
                    sns.heatmap(pivot_web, ax=ax1, cmap=color_map, annot=True, fmt=heatmap_fmt, linewidths=.5)
                    ax1.set_xlabel('Hora del Día')
                    ax1.set_ylabel('Día de la Semana')
                    st.pyplot(fig1)

                st.write("") 

            writer.close()
            excel_data = output.getvalue()
            
            st.divider()
            st.subheader("📥 Descargar Reporte Completo")
            if tipo_analisis == "Demanda de Reservas (Ventas)":
                st.markdown("🚀 **¡El archivo interactivo está listo!** Al descargar el Excel, ve a la celda **B1**. Podrás desplegar un menú para alternar entre *Compartida*, *Exclusiva* o *Total*, y el mapa de calor se actualizará mágicamente frente a tus ojos.")
            else:
                st.markdown("Descarga tu Excel. Todas las pestañas ya están coloreadas.")
                
            st.download_button(
                label="Descargar Reporte en Excel",
                data=excel_data,
                file_name=nombre_archivo_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Ocurrió un error general al procesar el archivo: {e}")
        st.markdown("Por favor revisa el archivo subido y asegúrate de que corresponda con el análisis seleccionado.")
