import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Análisis de Espera en Losa", layout="wide")

st.title("Mapa de Calor: Pasajeros con +30 min de espera en losa ✈️")
st.markdown("""
Sube tu archivo CSV para visualizar en qué días y horarios se concentran los pasajeros que esperaron más de 30 minutos.
""")

# Carga de archivo
uploaded_file = st.file_uploader("Carga el archivo CSV", type=['csv'])

if uploaded_file is not None:
    try:
        # Leer el archivo
        df = pd.read_csv(uploaded_file, sep=';')
        
        # Convertir a datetime
        df['tm_start_local_at'] = pd.to_datetime(df['tm_start_local_at'], format='%d/%m/%Y %H:%M:%S')
        
        # Filtrar solo esperas +30 minutos
        categorias_espera = ['03. 30 - 45 min', '04. 45+']
        filtered_df = df[df['Segmento Tiempo en Losa'].isin(categorias_espera)].copy()
        
        # Extraer variables temporales
        filtered_df['hour'] = filtered_df['tm_start_local_at'].dt.hour
        # Usamos el número del día para ordenar correctamente (0=Lunes, 6=Domingo)
        filtered_df['day_of_week_num'] = filtered_df['tm_start_local_at'].dt.dayofweek
        
        # Mapeo a español
        dias_espanol = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
        filtered_df['day_of_week'] = filtered_df['day_of_week_num'].map(dias_espanol)
        filtered_df['week'] = filtered_df['tm_start_local_at'].dt.isocalendar().week

        # Seleccionar semana a analizar
        semanas = sorted(filtered_df['week'].unique())
        semana_seleccionada = st.selectbox("Selecciona la semana a visualizar:", semanas)

        # Filtrar por la semana seleccionada
        week_df = filtered_df[filtered_df['week'] == semana_seleccionada]
        
        if week_df.empty:
            st.warning("No hay datos de +30 minutos para esta semana.")
        else:
            # Orden de días
            days_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            
            # --- PIVOT: CANTIDAD DE PASAJEROS (Absoluto) ---
            pivot_abs = week_df.pivot_table(index='day_of_week', columns='hour', values='# Riders', aggfunc='sum').reindex(days_order)
            
            # Completar horas faltantes de 0 a 23
            for h in range(24):
                if h not in pivot_abs.columns:
                    pivot_abs[h] = 0
            pivot_abs = pivot_abs[range(24)].fillna(0)
            
            # --- PIVOT: PORCENTAJE DE PASAJEROS ---
            total_pasajeros_semana = pivot_abs.values.sum()
            pivot_pct = (pivot_abs / total_pasajeros_semana) * 100
            
            # Visualización en Streamlit
            st.subheader(f"Análisis Semana {semana_seleccionada}")
            
            col1, col2 = st.columns(2)
            
            # Gráfico Absoluto
            with col1:
                st.markdown("**Cantidad total de pasajeros (+30 min)**")
                fig1, ax1 = plt.subplots(figsize=(10, 6))
                sns.heatmap(pivot_abs, ax=ax1, cmap='YlOrRd', annot=True, fmt='g', linewidths=.5)
                ax1.set_xlabel('Hora del Día')
                ax1.set_ylabel('Día de la Semana')
                st.pyplot(fig1)
                
            # Gráfico Porcentaje
            with col2:
                st.markdown("**Porcentaje de pasajeros (+30 min)**")
                fig2, ax2 = plt.subplots(figsize=(10, 6))
                sns.heatmap(pivot_pct, ax=ax2, cmap='YlGnBu', annot=True, fmt='.1f', linewidths=.5)
                # Añadir símbolo % a las anotaciones
                for t in ax2.texts:
                    t.set_text(t.get_text() + " %")
                ax2.set_xlabel('Hora del Día')
                ax2.set_ylabel('') # Ocultar para no repetir
                st.pyplot(fig2)

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
        st.markdown("Verifica que el archivo tenga el formato correcto y use ';' como separador.")
