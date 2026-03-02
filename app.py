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
La aplicación generará un resumen ejecutivo, mapas de calor por cada semana y un reporte en Excel descargable.
""")

# Diccionario para traducir meses
MESES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto', 
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}

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
            
            # Encontrar el día y hora pico global
            pico_global = filtered_df.groupby(['day_of_week', 'hour'])['# Riders'].sum().idxmax()
            pico_global_valor = filtered_df.groupby(['day_of_week', 'hour'])['# Riders'].sum().max()
            
            # Encontrar la peor semana
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
            La semana que presentó mayores desafíos fue la **Semana {peor_semana}**. Se sugiere revisar la asignación de recursos o llegadas de vuelos en estos bloques horarios.
            """)
            st.divider()

            # 3. Preparar Excel en memoria
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine='openpyxl')
            
            # Guardar el detalle completo en la primera hoja
            filtered_df.to_excel(writer, sheet_name='Detalle_Completo', index=False)

            # 4. Generar Mapas de Calor por Semana
            semanas = sorted(filtered_df['week'].unique())
            days_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

            for week in semanas:
                week_df = filtered_df[filtered_df['week'] == week]
                
                # Calcular el rango de fechas de esta semana
                una_fecha = week_df['tm_start_local_at'].iloc[0]
                lunes = una_fecha - timedelta(days=una_fecha.weekday())
                domingo = lunes + timedelta(days=6)
                
                # Formatear el título (Ej: 9 al 15 de febrero de 2026)
                mes_lunes = MESES[lunes.month]
                mes_domingo = MESES[domingo.month]
                
                if lunes.month == domingo.month:
                    titulo_semana = f"Semana {week}: {lunes.day} al {domingo.day} de {mes_lunes} de {lunes.year}"
                else:
                    titulo_semana = f"Semana {week}: {lunes.day} de {mes_lunes} al {domingo.day} de {mes_domingo} de {domingo.year}"
                
                st.subheader(titulo_semana)

                # Pivot Absoluto
                pivot_abs = week_df.pivot_table(index='day_of_week', columns='hour', values='# Riders', aggfunc='sum').reindex(days_order)
                for h in range(24):
                    if h not in pivot_abs.columns:
                        pivot_abs[h] = 0
                pivot_abs = pivot_abs[range(24)].fillna(0)
                
                # Pivot Porcentaje
                total_pasajeros_semana = pivot_abs.values.sum()
                pivot_pct = (pivot_abs / total_pasajeros_semana) * 100 if total_pasajeros_semana > 0 else pivot_abs
                
                # Guardar pivots en Excel
                pivot_abs.to_excel(writer, sheet_name=f'S{week}_Absoluto')
                pivot_pct.to_excel(writer, sheet_name=f'S{week}_Porcentaje')

                # Renderizar gráficos
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Cantidad de pasajeros (+30 min)**")
                    fig1, ax1 = plt.subplots(figsize=(10, 5))
                    sns.heatmap(pivot_abs, ax=ax1, cmap='YlOrRd', annot=True, fmt='g', linewidths=.5)
                    ax1.set_xlabel('Hora del Día')
                    ax1.set_ylabel('Día de la Semana')
                    st.pyplot(fig1)
                    
                with col2:
                    st.markdown("**Porcentaje de pasajeros (+30 min)**")
                    fig2, ax2 = plt.subplots(figsize=(10, 5))
                    sns.heatmap(pivot_pct, ax=ax2, cmap='YlGnBu', annot=True, fmt='.1f', linewidths=.5)
                    for t in ax2.texts:
                        t.set_text(t.get_text() + " %")
                    ax2.set_xlabel('Hora del Día')
                    ax2.set_ylabel('')
                    st.pyplot(fig2)
                    
                st.write("") # Espacio entre semanas

            # 5. Cerrar y preparar el botón de descarga del Excel
            writer.close()
            excel_data = output.getvalue()
            
            st.divider()
            st.subheader("📥 Descargar Datos")
            st.markdown("Descarga un archivo Excel con el detalle completo y las tablas de calor de cada semana en pestañas separadas.")
            st.download_button(
                label="Descargar Reporte en Excel",
                data=excel_data,
                file_name="reporte_espera_losa.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
        st.markdown("Verifica que el archivo tenga el formato correcto y use ';' como separador.")
