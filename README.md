# Sistema de Monitoreo Regulatorio SUCOP

Este proyecto implementa un crawler para el Sistema Único de Consulta Pública (SUCOP) de Colombia, enfocado en el monitoreo de normativas del sector agropecuario.

## Características

- Extracción automatizada de normativas del SUCOP
- Filtros por estado, tipo de documento y fechas
- Transformación y limpieza de datos (ETL)
- Generación de estadísticas básicas
- Exportación a múltiples formatos (JSON, CSV, Excel)
- Visualización de datos con Power BI

## Requisitos

- Python 3.8+
- Microsoft Edge (navegador)
- Power BI Desktop (para visualizaciones)
- Dependencias listadas en `requirements.txt`

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

### Crawler SUCOP

```bash
python sucop_crawler.py
```

El script ofrece dos opciones:
1. Ejecutar crawler completo (con filtros interactivos)
2. Generar CSV desde archivo JSON existente

### Generación de Datos para Power BI

```bash
python generate_powerbi_data.py
```

Este script genera un archivo Excel estructurado (`normativas_powerbi.xlsx`) con:
- Tablas dimensionales (Estados, Tiempo, Entidad)
- Tabla de hechos (Normativas)
- Métricas precalculadas

## Estructura de Datos

### Modelo Dimensional para Power BI

1. **Tabla de Hechos (Fact_Normativas)**
   - id_normativa
   - titulo
   - url
   - id_estado (FK)
   - id_fecha_publicacion (FK)
   - id_fecha_cierre (FK)
   - id_entidad (FK)
   - num_comentarios
   - dias_consulta

2. **Tablas Dimensionales**
   - Dim_Estados (id_estado, estado)
   - Dim_Tiempo (fecha_id, fecha, año, mes, trimestre)
   - Dim_Entidad (id_entidad, entidad, sector)

3. **Tablas de Métricas**
   - Metricas_Estado (agregaciones por estado)
   - Metricas_Tiempo (agregaciones temporales)

### Esquema SQL
El sistema utiliza un esquema SQL (ver `schema.sql`) con las siguientes tablas principales:
- Normativas
- Entidades
- Estados
- Tipos de documento
- Palabras clave
- Alertas

## Visualizaciones Power BI

### Configuración Inicial
1. Abrir Power BI Desktop
2. Seleccionar 'Obtener datos' > 'Excel'
3. Importar `normativas_powerbi.xlsx`
4. Establecer relaciones entre tablas:
   - Fact_Normativas.id_estado -> Dim_Estados.id_estado
   - Fact_Normativas.id_fecha_publicacion -> Dim_Tiempo.fecha_id
   - Fact_Normativas.id_fecha_cierre -> Dim_Tiempo.fecha_id
   - Fact_Normativas.id_entidad -> Dim_Entidad.id_entidad

### Dashboards Sugeridos

1. **Visión General**
   - KPIs principales
   - Tendencia temporal de normativas
   - Distribución por estado
   - Mapa de calor de actividad

2. **Análisis de Participación**
   - Top 10 normativas por comentarios
   - Línea de tiempo de consultas
   - Indicadores de participación ciudadana
   - Filtros dinámicos

3. **Análisis Temporal**
   - Calendario visual
   - Comparativa mensual
   - Análisis de estacionalidad
   - Predicción de tendencias

## Propuesta de Arquitectura AWS

### Componentes Core

1. **Capa de Extracción**
   - AWS Lambda para ejecutar el crawler
   - Amazon EventBridge para programar ejecuciones
   - AWS Systems Manager Parameter Store para credenciales

2. **Capa de Almacenamiento**
   - Amazon S3 para datos crudos y procesados
   - Amazon RDS (PostgreSQL) para datos estructurados
   - Amazon DynamoDB para caché y metadatos

3. **Capa de Procesamiento**
   - AWS Glue para jobs ETL
   - Amazon EMR para procesamiento batch
   - AWS Lambda para transformaciones ligeras

4. **Capa de Análisis**
   - Amazon Athena para consultas ad-hoc
   - Amazon QuickSight para visualizaciones
   - Amazon OpenSearch Service para búsqueda de texto completo

### Componentes de Monitoreo y Alertas

1. **Monitoreo**
   - Amazon CloudWatch para logs y métricas
   - AWS X-Ray para tracing
   - Amazon SNS para notificaciones

2. **Sistema de Alertas**
   - Amazon EventBridge para reglas de alertas
   - AWS Lambda para procesamiento de alertas
   - Amazon SES para envío de correos
   - Amazon SNS para notificaciones push

### Seguridad y Gobernanza

1. **Seguridad**
   - AWS IAM para gestión de accesos
   - AWS KMS para encriptación
   - AWS WAF para protección de APIs

2. **Gobernanza**
   - AWS CloudTrail para auditoría
   - AWS Config para compliance
   - Amazon Macie para clasificación de datos sensibles

### Diagrama de Arquitectura

```
[Crawler Lambda] → [EventBridge] → [S3 Raw]
         ↓
[Glue ETL Jobs] → [S3 Processed] → [RDS PostgreSQL]
         ↓
[Lambda Alerts] → [SNS/SES] → [Users]
         ↓
[QuickSight] ← [Athena] ← [Data Lake]
```

### Estimación de Costos (mensual)

- AWS Lambda: ~$20
- Amazon S3: ~$30
- Amazon RDS: ~$50
- AWS Glue: ~$100
- Otros servicios: ~$100
- **Total estimado**: ~$300/mes

## Outputs del Sistema

1. **Datos Crudos**
   - `normativas.json`: Datos extraídos del crawler
   - `normativas.csv`: Datos normalizados en formato CSV

2. **Datos Procesados**
   - `normativas_powerbi.xlsx`: Modelo dimensional para Power BI
   - `normativas_stats.json`: Estadísticas y métricas

3. **Visualizaciones**
   - Dashboard en Power BI
   - Reportes automatizados
   - Alertas personalizadas

## Contribuir

1. Fork el repositorio
2. Cree una rama (`git checkout -b feature/mejora`)
3. Commit sus cambios (`git commit -am 'Añade mejora'`)
4. Push a la rama (`git push origin feature/mejora`)
5. Cree un Pull Request

## Licencia

Este proyecto está licenciado bajo MIT License. 