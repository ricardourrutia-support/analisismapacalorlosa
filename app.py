import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
from datetime import timedelta

st.set_page_config(page_title="Análisis de Espera en Losa", layout="wide")

st.title("Mapa de Calor: Pasajeros con +30 min de espera en losa ✈️")
st.markdown("""
Sube tu archivo CSV para visualizar los patrones de espera por semana. 
La aplicación generará un resumen ejecutivo, mapas de calor por cada semana y un reporte en Excel con los colores ya aplicados.
""")

# Diccionario para traducir meses
MESES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto', 
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

# Color morado estilo Cabify
CABIFY_PURPLE = "#7142FF"
# Crear un mapa de colores (colormap) que va de blanco a morado
cabify_cmap = sns.light_palette(CABIFY_PURPLE, as_cmap=True)

uploaded_file = st.file_uploader("Carga el archivo CSV", type=['csv'])

if uploaded_file is not None:
    try:
        # 1. Lectura y preparación de datos
        df = pd.read_csv(uploaded_file, sep=';')
        df['tm_start_local_at'] = pd.to_datetime(df['tm_start_local_at'], format='%d/%m/%Y %H:%M:%S')
        
        # Filtrar solo esperas +30 minutos
        categorias_espera = ['03. 30 - 45 min', '04. 45+']
        filtered_df = df[df['Segmento Tiempo en Losa'].isin(categorias_espera)].copy()
        
        if filtered_df.empty:
            st.warning("No se encontraron registros con esperas mayores a 30 minutos en este archivo.")
        else:
            # Extraer variables temporales
            filtered_df['hour'] = filtered_df['tm_start_local_at'].dt.hour
            filtered_df['day_of_week_num'] = filtered_df['tm_start_local_at'].dt.dayofweek
            dias_espanol = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
            filtered_df['day_of_week'] = filtered_df['day_of_week_num'].map(dias_espanol)
            filtered_df['week'] = filtered_df['tm_start_local_at'].dt.isocalendar().week
            filtered_df['year'] = filtered_df['tm_start_local_at'].dt.year

            # 2. Resumen Ejecutivo Automático
            st.header("📝 Resumen Ejecutivo")
            total_afectados = filtered_df['# Riders'].sum()
            
            pico_global = filtered_df.groupby(['day_of_week', 'hour'])['# Riders'].sum().idxmax()
            pico_global_valor = filtered_df.groupby(['day_of_week', 'hour'])['# Riders'].sum().max()
            
            peor_semana_datos = filtered_df.groupby('week')['# Riders'].sum()
            peor_semana = peor_semana_datos.idxmax()
            peor_semana_valor = peor_semana_datos.max()
            
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Total Pasajeros Afectados (+30 min)", f"{total_afectados:,}")
            col_res2.metric("Pico Crítico (Global)", f"{pico_global[0]} a las {pico_global[1]}:00", f"{pico_global_valor} pasajeros")
            col_res3.metric("Semana más crítica", f"Semana {peor_semana}", f"{peor_semana_valor} pasajeros")
            
            st.markdown(f"""
            > **Análisis rápido:** Durante el periodo analizado, un total de **{total_afectados} pasajeros** experimentaron esperas superiores a 30 minutos en losa. 
            El momento de mayor tensión operativa ocurrió los días **{pico_global[0]} a las {pico_global[1]}:00 horas**, acumulando un total de {pico_global_valor} incidentes de espera prolongada. 
            La semana que presentó mayores desafíos fue la **Semana {peor_semana}**.
            """)
            st.divider()

            # 3. Preparar Excel en memoria (con xlsxwriter para los colores)
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            workbook = writer.book
            
            # Formato para porcentajes en Excel
            pct_format = workbook.add_format({'num_format': '0.00%'})
            
            filtered_df.to_excel(writer, sheet_name='Detalle_Completo', index=False)

            # 4. Generar Mapas de Calor por Semana
            semanas = sorted(filtered_df['week'].unique())
            days_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

            for week in semanas:
                week_df = filtered_df[filtered_df['week'] == week]
                
                # Calcular fechas de la semana
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

                # --- Lógica de Datos ---
                pivot_abs = week_df.pivot_table(index='day_of_week', columns='hour', values='# Riders', aggfunc='sum').reindex(days_order)
                for h in range(24):
                    if h not in pivot_abs.columns:
                        pivot_abs[h] = 0
                pivot_abs = pivot_abs[range(24)].fillna(0)
                
                total_pasajeros_semana = pivot_abs.values.sum()
                
                # Para la gráfica en Streamlit usamos base 100
                pivot_pct_web = (pivot_abs / total_pasajeros_semana) * 100 if total_pasajeros_semana > 0 else pivot_abs
                
                # Para el Excel usamos base 1 (0 a 1) para que el formato de Excel % funcione correcto
                pivot_pct_excel = (pivot_abs / total_pasajeros_semana) if total_pasajeros_semana > 0 else pivot_abs

                # --- Guardado y Pintado en Excel ---
                pivot_abs.to_excel(writer, sheet_name=f'S{week}_Absoluto')
                pivot_pct_excel.to_excel(writer, sheet_name=f'S{week}_Porcentaje')
                
                filas_excel = len(pivot_abs)
                cols_excel = len(pivot_abs.columns)
                
                # Pintar pestaña de Absolutos
                ws_abs = writer.sheets[f'S{week}_Absoluto']
                ws_abs.conditional_format(1, 1, filas_excel, cols_excel, 
                                          {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': CABIFY_PURPLE})
                
                # Pintar pestaña de Porcentajes
                ws_pct = writer.sheets[f'S{week}_Porcentaje']
                ws_pct.set_column(1, cols_excel, None, pct_format)
                ws_pct.conditional_format(1, 1, filas_excel, cols_excel, 
                                          {'type': '2_color_scale', 'min_color': '#FFFFFF', 'max_color': CABIFY_PURPLE})

                # --- Renderizar gráficos en la App ---
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Cantidad de pasajeros (+30 min)**")
                    fig1, ax1 = plt.subplots(figsize=(10, 5))
                    sns.heatmap(pivot_abs, ax=ax1, cmap=cabify_cmap, annot=True, fmt='g', linewidths=.5)
                    ax1.set_xlabel('Hora del Día')
                    ax1.set_ylabel('Día de la Semana')
                    st.pyplot(fig1)
                    
                with col2:
                    st.markdown("**Porcentaje de pasajeros (+30 min)**")
                    fig2, ax2 = plt.subplots(figsize=(10, 5))
                    # fmt='.2f' genera el número con 2 decimales, luego cambiamos punto por coma
                    sns.heatmap(pivot_pct_web, ax=ax2, cmap=cabify_cmap, annot=True, fmt='.2f', linewidths=.5)
                    for t in ax2.texts:
                        texto_actual = t.get_text()
                        # Si es "0.00", se transforma a "0,00%"
                        t.set_text(texto_actual.replace('.', ',') + "%")
                        
                    ax2.set_xlabel('Hora del Día')
                    ax2.set_ylabel('')
                    st.pyplot(fig2)
                    
                st.write("") 

            # 5. Cerrar Excel
            writer.close()
            excel_data = output.getvalue()
            
            st.divider()
            st.subheader("📥 Descargar Datos con Mapa de Calor")
            st.markdown("Descarga un archivo Excel. Las pestañas de cada semana ya vienen con el estilo de color aplicado a las celdas.")
            st.download_button(
                label="Descargar Reporte en Excel",
                data=excel_data,
                file_name="reporte_espera_losa_cabify.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
        st.markdown("Verifica que el archivo tenga el formato correcto y use ';' como separador.")
