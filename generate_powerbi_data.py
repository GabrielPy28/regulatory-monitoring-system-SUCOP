import pandas as pd
import json
from datetime import datetime
import numpy as np

def load_normativas():
    """Carga los datos desde normativas.json"""
    with open('normativas.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def create_dimension_tables(normativas):
    """Crea tablas de dimensiones"""
    
    # Dim_Estado
    estados = pd.DataFrame({
        'id_estado': range(1, len(set(n['estado'] for n in normativas)) + 1),
        'estado': sorted(set(n['estado'] for n in normativas))
    })
    
    # Dim_Tiempo
    fechas = []
    for n in normativas:
        fechas.extend([n['fecha_publicacion'], n['fecha_cierre']])
    fechas = sorted(set(fechas))
    
    dim_tiempo = pd.DataFrame({
        'fecha_id': range(1, len(fechas) + 1),
        'fecha': fechas,
        'año': [datetime.strptime(f, '%d/%m/%Y').year for f in fechas],
        'mes': [datetime.strptime(f, '%d/%m/%Y').month for f in fechas],
        'trimestre': [f"Q{(datetime.strptime(f, '%d/%m/%Y').month-1)//3 + 1}" for f in fechas]
    })
    
    # Dim_Entidad
    dim_entidad = pd.DataFrame({
        'id_entidad': [1],
        'entidad': ['Ministerio de Agricultura y Desarrollo Rural'],
        'sector': ['Agropecuario']
    })
    
    return estados, dim_tiempo, dim_entidad

def create_fact_table(normativas, estados, dim_tiempo):
    """Crea la tabla de hechos principal"""
    
    # Crear mapeos para las claves foráneas
    estado_map = {estado: id_estado for id_estado, estado in zip(estados['id_estado'], estados['estado'])}
    fecha_map = {fecha: id_fecha for id_fecha, fecha in zip(dim_tiempo['fecha_id'], dim_tiempo['fecha'])}
    
    # Crear registros para la tabla de hechos
    records = []
    for n in normativas:
        record = {
            'id_normativa': hash(n['url']) % 10**8,  # Generar ID único
            'titulo': n['titulo'],
            'url': n['url'],
            'id_estado': estado_map[n['estado']],
            'id_fecha_publicacion': fecha_map[n['fecha_publicacion']],
            'id_fecha_cierre': fecha_map[n['fecha_cierre']],
            'id_entidad': 1,  # Solo tenemos una entidad
            'num_comentarios': n['comentarios'],
            'dias_consulta': (datetime.strptime(n['fecha_cierre'], '%d/%m/%Y') - 
                            datetime.strptime(n['fecha_publicacion'], '%d/%m/%Y')).days
        }
        records.append(record)
    
    return pd.DataFrame(records)

def calculate_metrics(fact_table, dim_tiempo):
    """Calcula métricas agregadas para análisis"""
    
    # Métricas por estado
    metricas_estado = fact_table.groupby('id_estado').agg({
        'num_comentarios': ['count', 'sum', 'mean'],
        'dias_consulta': 'mean'
    }).round(2)
    
    # Métricas temporales
    fact_table['año_publicacion'] = fact_table['id_fecha_publicacion'].map(
        dim_tiempo.set_index('fecha_id')['año']
    )
    fact_table['mes_publicacion'] = fact_table['id_fecha_publicacion'].map(
        dim_tiempo.set_index('fecha_id')['mes']
    )
    
    metricas_tiempo = fact_table.groupby(['año_publicacion', 'mes_publicacion']).agg({
        'num_comentarios': ['count', 'sum'],
        'dias_consulta': 'mean'
    }).round(2)
    
    return metricas_estado, metricas_tiempo

def generate_powerbi_file():
    """Genera archivo Excel estructurado para Power BI"""
    try:
        # Cargar datos
        normativas = load_normativas()
        
        # Crear tablas dimensionales
        dim_estados, dim_tiempo, dim_entidad = create_dimension_tables(normativas)
        
        # Crear tabla de hechos
        fact_normativas = create_fact_table(normativas, dim_estados, dim_tiempo)
        
        # Calcular métricas
        metricas_estado, metricas_tiempo = calculate_metrics(fact_normativas, dim_tiempo)
        
        # Crear archivo Excel con múltiples hojas
        with pd.ExcelWriter('normativas_powerbi.xlsx', engine='openpyxl') as writer:
            # Tablas dimensionales
            dim_estados.to_excel(writer, sheet_name='Dim_Estados', index=False)
            dim_tiempo.to_excel(writer, sheet_name='Dim_Tiempo', index=False)
            dim_entidad.to_excel(writer, sheet_name='Dim_Entidad', index=False)
            
            # Tabla de hechos
            fact_normativas.to_excel(writer, sheet_name='Fact_Normativas', index=False)
            
            # Métricas
            metricas_estado.to_excel(writer, sheet_name='Metricas_Estado')
            metricas_tiempo.to_excel(writer, sheet_name='Metricas_Tiempo')
        
        print("\nArchivo 'normativas_powerbi.xlsx' generado exitosamente.")
        print("\nPara crear visualizaciones en Power BI:")
        print("1. Abra Power BI Desktop")
        print("2. Seleccione 'Obtener datos' > 'Excel'")
        print("3. Seleccione el archivo 'normativas_powerbi.xlsx'")
        print("4. Importe todas las hojas")
        print("5. En la vista de modelo, establezca las siguientes relaciones:")
        print("   - Fact_Normativas.id_estado -> Dim_Estados.id_estado")
        print("   - Fact_Normativas.id_fecha_publicacion -> Dim_Tiempo.fecha_id")
        print("   - Fact_Normativas.id_fecha_cierre -> Dim_Tiempo.fecha_id")
        print("   - Fact_Normativas.id_entidad -> Dim_Entidad.id_entidad")
        
    except Exception as e:
        print(f"Error al generar archivo: {str(e)}")

if __name__ == "__main__":
    generate_powerbi_file() 