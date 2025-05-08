import requests
from bs4 import BeautifulSoup
import polars as pl
from datetime import datetime
import json
import logging
from typing import Dict, List, Optional
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from webdriver_manager.microsoft import EdgeChromiumDriverManager

class SUCOPCrawler:
    ESTADOS_VALIDOS = ["Activa", "Cerrada", "Finalizada"]
    TIPOS_DOCUMENTO = [
        "AIN", "Acuerdo", "Agenda regulatoria", "Auto", "CONPES", 
        "Circular", "Concepto", "Decreto", "Directiva Presidencial",
        "Edicto", "Instrucción", "Ley", "Oficio", "Ordenanza", "Otro",
        "Problema AIN", "Resolución"
    ]

    @staticmethod
    def solicitar_filtros():
        """Solicita los filtros al usuario por consola"""
        print("\n=== Configuración de filtros para el crawler SUCOP ===")
        print("(Presione Enter sin escribir nada para omitir un filtro)\n")

        # Solicitar estado
        print("\nEstados disponibles:")
        for i, estado in enumerate(SUCOPCrawler.ESTADOS_VALIDOS, 1):
            print(f"{i}. {estado}")
        while True:
            estado_input = input("\nSeleccione el número del estado (o Enter para omitir): ").strip()
            if not estado_input:
                estado = None
                break
            try:
                idx = int(estado_input) - 1
                if 0 <= idx < len(SUCOPCrawler.ESTADOS_VALIDOS):
                    estado = SUCOPCrawler.ESTADOS_VALIDOS[idx]
                    break
                else:
                    print("Número no válido. Intente de nuevo.")
            except ValueError:
                print("Por favor, ingrese un número válido.")

        # Solicitar tipo de documento
        print("\nTipos de documento disponibles:")
        for i, tipo in enumerate(SUCOPCrawler.TIPOS_DOCUMENTO, 1):
            print(f"{i}. {tipo}")
        while True:
            tipo_input = input("\nSeleccione el número del tipo de documento (o Enter para omitir): ").strip()
            if not tipo_input:
                tipo_documento = None
                break
            try:
                idx = int(tipo_input) - 1
                if 0 <= idx < len(SUCOPCrawler.TIPOS_DOCUMENTO):
                    tipo_documento = SUCOPCrawler.TIPOS_DOCUMENTO[idx]
                    break
                else:
                    print("Número no válido. Intente de nuevo.")
            except ValueError:
                print("Por favor, ingrese un número válido.")

        # Solicitar fechas
        print("\nIngrese las fechas en formato DD/MM/YYYY")
        while True:
            fecha_inicio = input("Fecha de inicio (o Enter para omitir): ").strip()
            if not fecha_inicio:
                fecha_inicio = None
                fecha_fin = None
                break
            
            fecha_fin = input("Fecha de fin: ").strip()
            if not fecha_fin:
                fecha_inicio = None
                fecha_fin = None
                break
            
            try:
                inicio = datetime.strptime(fecha_inicio, "%d/%m/%Y")
                fin = datetime.strptime(fecha_fin, "%d/%m/%Y")
                if inicio <= fin:
                    break
                else:
                    print("Error: La fecha de inicio debe ser anterior o igual a la fecha de fin.")
            except ValueError:
                print("Error: Formato de fecha incorrecto. Use DD/MM/YYYY")

        return estado, tipo_documento, fecha_inicio, fecha_fin

    def __init__(self, estado: str = None, tipo_documento: str = None, fecha_inicio: str = None, fecha_fin: str = None):
        """
        Inicializa el crawler con filtros opcionales
        
        Args:
            estado (str, opcional): Estado del documento (Activa, Cerrada, Finalizada)
            tipo_documento (str, opcional): Tipo de documento (AIN, Acuerdo, etc.)
            fecha_inicio (str, opcional): Fecha de inicio en formato DD/MM/YYYY
            fecha_fin (str, opcional): Fecha de fin en formato DD/MM/YYYY
        """
        self.estado = estado
        self.tipo_documento = tipo_documento
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        
        # Validar fechas si se proporcionan
        if fecha_inicio and fecha_fin:
            try:
                inicio = datetime.strptime(fecha_inicio, "%d/%m/%Y")
                fin = datetime.strptime(fecha_fin, "%d/%m/%Y")
                if inicio > fin:
                    raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin")
            except ValueError as e:
                raise ValueError(f"Error en el formato de fechas: {str(e)}")
        
        self.base_url = "https://www.sucop.gov.co/busqueda?pageSize=100"  # Solicitar 100 resultados por página
        self.setup_logging()
        self.setup_driver()

    def setup_logging(self):
        """Configura el sistema de logging"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('sucop_crawler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('SUCOPCrawler')

    def setup_driver(self):
        """Configura el driver de Microsoft Edge con manejo mejorado de errores"""
        try:
            # Configurar opciones de Edge
            edge_options = Options()
            edge_options.add_argument('--headless')
            edge_options.add_argument('--start-maximized')
            edge_options.add_argument('--disable-gpu')
            edge_options.add_argument('--no-sandbox')
            edge_options.add_argument('--disable-dev-shm-usage')
            edge_options.add_argument('--disable-extensions')
            edge_options.add_argument('--disable-popup-blocking')
            edge_options.add_argument('--ignore-certificate-errors')
            
            # Configurar el servicio de Edge
            service = Service(EdgeChromiumDriverManager().install())

            self.driver = webdriver.Edge(service=service, options=edge_options)
            self.wait = WebDriverWait(self.driver, 30)  # Aumentar el tiempo de espera a 30 segundos
            self.logger.info("Driver de Microsoft Edge configurado exitosamente")
            
        except Exception as e:
            self.logger.error(f"Error al configurar el driver de Edge: {str(e)}")
            raise Exception(f"No se pudo inicializar el driver de Edge: {str(e)}")

    def retry_with_delay(self, func, max_retries=3, delay=5):
        """Reintenta una función con un retraso entre intentos"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                self.logger.warning(f"Intento {attempt + 1} de {max_retries} falló: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    raise
    
    def wait_and_click(self, by, value, timeout=30):
        """Espera a que un elemento sea clickeable y lo clickea"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(1)  # Pequeña pausa para asegurar que el elemento sea visible
            element.click()
            return True
        except Exception as e:
            self.logger.error(f"Error al hacer click en elemento {value}: {str(e)}")
            return False

    def wait_and_select(self, by, value, option_text, timeout=30):
        """Espera a que un select esté presente y selecciona una opción"""
        try:
            # Esperar a que el elemento esté presente
            select_element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            
            # Esperar a que la página cargue completamente
            time.sleep(5)
            
            # Obtener el HTML del select para debug
            select_html = select_element.get_attribute('outerHTML')
            self.logger.debug(f"HTML del select {value}:")
            self.logger.debug(select_html)
            
            # Intentar obtener todas las opciones directamente del HTML
            options = select_element.find_elements(By.TAG_NAME, "option")
            option_texts = [opt.text for opt in options]
            self.logger.debug(f"Opciones disponibles en {value}: {option_texts}")
            
            if not options:
                self.logger.warning(f"No se encontraron opciones en el select {value}")
                return False
            
            # Intentar encontrar una opción que coincida parcialmente
            for option in options:
                option_text_lower = option.text.lower()
                search_text_lower = option_text.lower()
                if search_text_lower in option_text_lower:
                    self.logger.debug(f"Encontrada opción coincidente: {option.text}")
                    option.click()
                    return True
            
            self.logger.warning(f"No se encontró ninguna opción que coincida con '{option_text}'")
            return False
            
        except Exception as e:
            self.logger.error(f"Error al seleccionar opción {option_text} en {value}: {str(e)}")
            return False

    def apply_filters(self):
        """Aplica los filtros configurados en la página"""
        try:
            # Aplicar filtro de estado si se especificó
            if self.estado:
                try:
                    estado_select = Select(self.driver.find_element(By.ID, "slt-estado"))
                    estado_select.select_by_visible_text(self.estado)
                    self.logger.debug(f"Filtro de estado aplicado: {self.estado}")
                    time.sleep(2)
                except Exception as e:
                    self.logger.error(f"Error al aplicar filtro de estado: {str(e)}")
            
            # Aplicar filtro de tipo de documento si se especificó
            if self.tipo_documento:
                try:
                    tipo_doc_select = Select(self.driver.find_element(By.ID, "slt-documentType"))
                    tipo_doc_select.select_by_visible_text(self.tipo_documento)
                    self.logger.debug(f"Filtro de tipo de documento aplicado: {self.tipo_documento}")
                    time.sleep(2)
                except Exception as e:
                    self.logger.error(f"Error al aplicar filtro de tipo de documento: {str(e)}")
            
            # Aplicar filtros de fecha si se especificaron
            if self.fecha_inicio:
                try:
                    fecha_inicio_input = self.driver.find_element(By.ID, "txt-inicio")
                    self.driver.execute_script("arguments[0].value = arguments[1]", fecha_inicio_input, self.fecha_inicio)
                    # Simular evento de cambio para activar la búsqueda
                    self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'))", fecha_inicio_input)
                    self.logger.debug(f"Fecha de inicio aplicada: {self.fecha_inicio}")
                    time.sleep(1)
                except Exception as e:
                    self.logger.error(f"Error al aplicar fecha de inicio: {str(e)}")
            
            if self.fecha_fin:
                try:
                    fecha_fin_input = self.driver.find_element(By.ID, "txt-fin")
                    self.driver.execute_script("arguments[0].value = arguments[1]", fecha_fin_input, self.fecha_fin)
                    # Simular evento de cambio para activar la búsqueda
                    self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'))", fecha_fin_input)
                    self.logger.debug(f"Fecha de fin aplicada: {self.fecha_fin}")
                    time.sleep(1)
                except Exception as e:
                    self.logger.error(f"Error al aplicar fecha de fin: {str(e)}")
            
            # Si se aplicó algún filtro, esperar a que se actualicen los resultados
            if any([self.estado, self.tipo_documento, self.fecha_inicio, self.fecha_fin]):
                try:
                    # Esperar a que se actualice la lista de resultados
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "bq-proceso"))
                    )
                    time.sleep(3)  # Espera adicional para asegurar que todo se haya cargado
                except Exception as e:
                    self.logger.warning(f"Tiempo de espera excedido al actualizar resultados: {str(e)}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error al aplicar filtros: {str(e)}")
            return False

    def get_page_content(self, url: str) -> Optional[str]:
        """Obtiene el contenido de una página web usando Selenium con reintentos"""
        def _get_content():
            all_page_sources = []
            self.driver.get(url)
            
            # Esperar a que la página cargue completamente
            time.sleep(5)
            
            # Esperar a que cargue el selector de sector y seleccionar la opción
            if not self.wait_and_select(By.ID, "slt-sector", "Agropecuario"):
                raise Exception("No se pudo seleccionar el sector")
            self.logger.debug("Sector seleccionado")
            
            # Esperar un momento para que se actualice el selector de entidad
            time.sleep(5)
            
            # Seleccionar la entidad con el nombre completo
            if not self.wait_and_select(By.ID, "slt-entidad", "Ministerio de Agricultura y Desarrollo Rural"):
                raise Exception("No se pudo seleccionar la entidad")
            self.logger.debug("Entidad seleccionada")
            
            # Aplicar filtros configurados
            if not self.apply_filters():
                self.logger.warning("No se pudieron aplicar todos los filtros")
            
            # Esperar más tiempo a que se carguen los resultados
            time.sleep(10)
            
            current_page = 1
            while True:
                try:
                    # Intentar encontrar los resultados con diferentes clases
                    proceso_elements = self.driver.find_elements(By.CLASS_NAME, "bq-proceso")
                    if not proceso_elements:
                        proceso_elements = self.driver.find_elements(By.CLASS_NAME, "proceso-container")
                    
                    if proceso_elements:
                        self.logger.debug(f"Se encontraron {len(proceso_elements)} elementos de proceso en la página {current_page}")
                        all_page_sources.append(self.driver.page_source)
                    else:
                        self.logger.warning(f"No se encontraron elementos de proceso en la página {current_page}")
                    
                    # Buscar el siguiente número de página
                    try:
                        # Buscar todos los enlaces de paginación
                        page_links = self.driver.find_elements(By.CLASS_NAME, "J-paginationjs-page")
                        self.logger.debug(f"Encontrados {len(page_links)} enlaces de paginación")
                        
                        # Loggear todos los enlaces encontrados para debug
                        for link in page_links:
                            data_num = link.get_attribute('data-num')
                            classes = link.get_attribute('class')
                            self.logger.debug(f"Enlace encontrado: data-num='{data_num}', clase='{classes}'")
                        
                        next_page_found = False
                        for link in page_links:
                            try:
                                # Obtener el número de página del atributo data-num
                                data_num = link.get_attribute('data-num')
                                if data_num and data_num.isdigit():
                                    page_num = int(data_num)
                                    if page_num == current_page + 1:
                                        self.logger.debug(f"Encontrado enlace a página {page_num}")
                                        # Hacer scroll hasta el enlace
                                        self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                        time.sleep(2)
                                        # Intentar hacer clic usando JavaScript
                                        self.driver.execute_script("arguments[0].click();", link)
                                        current_page = page_num
                                        next_page_found = True
                                        # Esperar a que se carguen los nuevos resultados
                                        time.sleep(5)
                                        self.logger.debug(f"Navegando a la página {current_page}")
                                        break
                            except Exception as e:
                                self.logger.warning(f"Error al procesar enlace de página: {str(e)}")
                                continue
                        
                        if not next_page_found:
                            self.logger.debug("No se encontraron más páginas")
                            break
                        
                    except Exception as e:
                        self.logger.debug(f"Error al buscar enlaces de página: {str(e)}")
                        # Intentar buscar directamente el enlace usando el atributo data-num
                        try:
                            next_link = self.driver.find_element(By.CSS_SELECTOR, f".J-paginationjs-page[data-num='{current_page + 1}']")
                            self.logger.debug(f"Encontrado enlace a página {current_page + 1} usando selector CSS")
                            self.driver.execute_script("arguments[0].click();", next_link)
                            current_page += 1
                            time.sleep(5)
                        except Exception as e2:
                            self.logger.debug(f"No se pudo encontrar el enlace usando selector CSS: {str(e2)}")
                            break
                    
                except Exception as e:
                    self.logger.error(f"Error al procesar la página {current_page}: {str(e)}")
                    break
            
            # Obtener el número total de resultados
            try:
                resultados_div = self.driver.find_element(By.ID, "bq-resultados")
                total_resultados = resultados_div.find_element(By.TAG_NAME, "div").text
                self.logger.info(f"Total de resultados encontrados: {total_resultados}")
            except Exception as e:
                self.logger.warning(f"No se pudo obtener el total de resultados: {str(e)}")
            
            # Combinar el contenido de todas las páginas
            return "\n".join(all_page_sources)

        try:
            return self.retry_with_delay(_get_content)
        except Exception as e:
            self.logger.error(f"Error al obtener la página {url} después de todos los reintentos: {str(e)}")
            return None
        
    def parse_normativa(self, html_content: str) -> List[Dict]:
        """Parsea el contenido HTML y extrae la información de las normativas"""
        normativas = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Intentar encontrar procesos con diferentes clases
            procesos = soup.find_all('div', class_='bq-proceso')
            if not procesos:
                procesos = soup.find_all('div', class_='proceso-container')
            
            self.logger.debug(f"Número de procesos encontrados: {len(procesos)}")
            
            # Guardar el HTML para debug si no hay procesos
            if not procesos:
                self.logger.debug("HTML completo para debug:")
                self.logger.debug(html_content[:1000])  # Primeros 1000 caracteres
            
            for proceso in procesos:
                try:
                    # Extraer título y URL - intentar diferentes clases
                    header = proceso.find('div', class_='bq-proceso-header-title')
                    if not header:
                        header = proceso.find('div', class_='proceso-title')
                    
                    if not header:
                        self.logger.warning("No se encontró el encabezado del proceso")
                        continue
                        
                    link = header.find('a')
                    if not link:
                        self.logger.warning("No se encontró el enlace en el encabezado")
                        continue
                        
                    titulo = link.text.strip()
                    url = link.get('href', '')
                    
                    if not url:
                        self.logger.warning("URL vacía encontrada")
                        continue
                    
                    # Extraer fechas - intentar diferentes clases
                    fechas = proceso.find('div', class_='bq-normaFechas') or proceso.find('div', class_='fechas-container')
                    if fechas:
                        fecha_publicacion = ''
                        fecha_cierre = ''
                        
                        pub_div = fechas.find('div', class_='bq-col-publicado') or fechas.find('div', class_='fecha-publicacion')
                        if pub_div:
                            fecha_span = pub_div.find('span', class_='bq-fechas-value') or pub_div.find('span', class_='fecha')
                            if fecha_span:
                                fecha_publicacion = fecha_span.text.strip()
                        
                        cierre_div = fechas.find('div', class_='bq-col-cierre') or fechas.find('div', class_='fecha-cierre')
                        if cierre_div:
                            fecha_span = cierre_div.find('span', class_='bq-fechas-value') or cierre_div.find('span', class_='fecha')
                            if fecha_span:
                                fecha_cierre = fecha_span.text.strip()
                    else:
                        self.logger.warning("No se encontró el contenedor de fechas")
                        fecha_publicacion = ''
                        fecha_cierre = ''
                    
                    # Extraer estado - intentar diferentes clases
                    estado = ''
                    estado_div = proceso.find('div', class_='estado-container') or proceso.find('div', class_='estado')
                    if estado_div:
                        estado_text = estado_div.find('div')
                        if estado_text:
                            estado = estado_text.text.strip()
                    
                    # Extraer número de comentarios - intentar diferentes clases
                    comentarios = 0
                    comentarios_div = proceso.find('div', class_='respuestasContainer') or proceso.find('div', class_='comentarios')
                    if comentarios_div:
                        num_div = comentarios_div.find('div', class_='bq-statics-number') or comentarios_div.find('div', class_='numero')
                        if num_div:
                            try:
                                comentarios = int(num_div.text.strip())
                            except ValueError:
                                self.logger.warning(f"No se pudo convertir el número de comentarios: {num_div.text.strip()}")
                    
                    normativa = {
                        'titulo': titulo,
                        'url': url,
                        'fecha_publicacion': fecha_publicacion,
                        'fecha_cierre': fecha_cierre,
                        'estado': estado,
                        'comentarios': comentarios
                    }
                    
                    # Verificar si la normativa ya existe antes de agregarla
                    if not any(n['url'] == url for n in normativas):
                        normativas.append(normativa)
                        self.logger.debug(f"Nueva normativa agregada: {titulo}")
                    
                except Exception as e:
                    self.logger.error(f"Error al procesar una normativa: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error al procesar el HTML: {str(e)}")
        
        self.logger.info(f"Total de normativas únicas encontradas: {len(normativas)}")
        return normativas

    def transform_data(self, normativas: List[Dict]) -> pl.DataFrame:
        """
        Aplica transformaciones ETL a los datos extraídos
        """
        try:
            if not normativas:
                self.logger.warning("No hay datos para transformar")
                return None
            
            # Convertir a DataFrame de polars
            df = pl.DataFrame(normativas)
            
            # Transformaciones básicas
            df = df.with_columns([
                # Convertir fechas a formato estándar
                pl.col('fecha_publicacion').str.strptime(pl.Date, '%d/%m/%Y').alias('fecha_publicacion'),
                pl.col('fecha_cierre').str.strptime(pl.Date, '%d/%m/%Y').alias('fecha_cierre'),
                
                # Limpiar y estandarizar textos
                pl.col('titulo').str.strip().str.replace_all(r'\s+', ' ').alias('titulo'),
                
                # Convertir comentarios a número
                pl.col('comentarios').cast(pl.Int32).fill_null(0).alias('comentarios'),
                
                # Añadir columnas derivadas
                pl.lit('Ministerio de Agricultura y Desarrollo Rural').alias('entidad'),
                pl.lit('Agropecuario').alias('sector'),
                
                # Añadir timestamps
                pl.lit(datetime.now()).alias('fecha_extraccion')
            ])
            
            # Reordenar columnas
            columnas = [
                'titulo', 'url', 'fecha_publicacion', 'fecha_cierre', 
                'estado', 'comentarios', 'entidad', 'sector', 'fecha_extraccion'
            ]
            df = df.select(columnas)
            
            self.logger.info("Datos transformados exitosamente")
            return df
            
        except Exception as e:
            self.logger.error(f"Error al transformar los datos: {str(e)}")
            return None

    def save_to_json(self, data: List[Dict], filename: str = 'normativas.json'):
        """Guarda los datos en formato JSON"""
        try:
            if not data:
                self.logger.warning("No hay datos para guardar en JSON")
                return
                
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Datos guardados exitosamente en {filename}")
            self.logger.debug(f"Contenido guardado en JSON: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Error al guardar los datos en JSON: {str(e)}")

    def save_to_csv(self, data: List[Dict], filename: str = 'normativas.csv'):
        """Guarda los datos transformados en formato CSV"""
        try:
            if not data:
                self.logger.warning("No hay datos para guardar en CSV")
                return
            
            # Aplicar transformaciones
            df = self.transform_data(data)
            if df is None:
                return
            
            # Guardar como CSV con punto y coma como separador
            df.write_csv(filename, separator=';')
            self.logger.info(f"Datos guardados exitosamente en {filename}")
            
            # Generar estadísticas básicas
            stats = {
                'total_normativas': len(df),
                'normativas_por_estado': df.group_by('estado').count().to_dict(as_series=False),
                'promedio_comentarios': df['comentarios'].mean(),
                'rango_fechas': {
                    'min': df['fecha_publicacion'].min().strftime('%Y-%m-%d'),
                    'max': df['fecha_publicacion'].max().strftime('%Y-%m-%d')
                }
            }
            
            # Guardar estadísticas en JSON
            stats_file = filename.replace('.csv', '_stats.json')
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Estadísticas guardadas en {stats_file}")
            
        except Exception as e:
            self.logger.error(f"Error al guardar los datos en CSV: {str(e)}")

    def run(self):
        """Ejecuta el crawler"""
        try:
            self.logger.info("Iniciando el crawler de SUCOP...")
            
            # Obtener el contenido de la página
            content = self.get_page_content(self.base_url)
            if not content:
                self.logger.error("No se pudo obtener el contenido de la página")
                return
                
            self.logger.debug(f"Contenido obtenido de longitud: {len(content)}")
            
            # Procesar las normativas
            normativas = self.parse_normativa(content)
            
            if not normativas:
                self.logger.warning("No se encontraron normativas para procesar")
                return
                
            self.logger.info(f"Se encontraron {len(normativas)} normativas")
            
            # Guardar los resultados en JSON y CSV
            self.save_to_json(normativas)
            self.save_to_csv(normativas)
            
            self.logger.info(f"Crawler finalizado. Se procesaron {len(normativas)} normativas.")
        
        finally:
            # Cerrar el navegador
            self.driver.quit()

    @staticmethod
    def json_to_csv(json_file: str = 'normativas.json', csv_file: str = 'normativas.csv'):
        """Convierte un archivo JSON de normativas a formato CSV"""
        logger = logging.getLogger('SUCOPCrawler')
        
        try:
            # Leer el archivo JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                normativas = json.load(f)
            
            if not normativas:
                logger.warning("No hay datos en el archivo JSON")
                return
            
            # Convertir a DataFrame de polars
            df = pl.DataFrame(normativas)
            
            # Aplicar las mismas transformaciones que en transform_data
            df = df.with_columns([
                # Convertir fechas a formato estándar
                pl.col('fecha_publicacion').str.strptime(pl.Date, '%d/%m/%Y').alias('fecha_publicacion'),
                pl.col('fecha_cierre').str.strptime(pl.Date, '%d/%m/%Y').alias('fecha_cierre'),
                
                # Limpiar y estandarizar textos
                pl.col('titulo').str.strip().str.replace_all(r'\s+', ' ').alias('titulo'),
                
                # Convertir comentarios a número
                pl.col('comentarios').cast(pl.Int32).fill_null(0).alias('comentarios'),
                
                # Añadir columnas derivadas
                pl.lit('Ministerio de Agricultura y Desarrollo Rural').alias('entidad'),
                pl.lit('Agropecuario').alias('sector'),
                
                # Añadir timestamps
                pl.lit(datetime.now()).alias('fecha_extraccion')
            ])
            
            # Reordenar columnas
            columnas = [
                'titulo', 'url', 'fecha_publicacion', 'fecha_cierre', 
                'estado', 'comentarios', 'entidad', 'sector', 'fecha_extraccion'
            ]
            df = df.select(columnas)
            
            # Guardar como CSV
            df.write_csv(csv_file, separator=';')
            logger.info(f"CSV generado exitosamente: {csv_file}")
            
            # Generar estadísticas básicas
            stats = {
                'total_normativas': len(df),
                'normativas_por_estado': df.group_by('estado').count().to_dict(as_series=False),
                'promedio_comentarios': df['comentarios'].mean(),
                'rango_fechas': {
                    'min': df['fecha_publicacion'].min().strftime('%Y-%m-%d'),
                    'max': df['fecha_publicacion'].max().strftime('%Y-%m-%d')
                }
            }
            
            # Guardar estadísticas
            stats_file = csv_file.replace('.csv', '_stats.json')
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            logger.info(f"Estadísticas guardadas en {stats_file}")
            
        except Exception as e:
            logger.error(f"Error al convertir JSON a CSV: {str(e)}")

if __name__ == "__main__":
    try:
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('sucop_crawler.log'),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger('SUCOPCrawler')
        
        # Preguntar al usuario qué operación desea realizar
        print("\n=== Sistema de Monitoreo Regulatorio SUCOP ===")
        print("1. Ejecutar crawler completo")
        print("2. Generar CSV desde archivo JSON existente")
        
        opcion = input("\nSeleccione una opción (1/2): ").strip()
        
        if opcion == "1":
            # Solicitar filtros y ejecutar crawler
            estado, tipo_documento, fecha_inicio, fecha_fin = SUCOPCrawler.solicitar_filtros()
            
            print("\n=== Resumen de filtros seleccionados ===")
            print(f"Estado: {estado if estado else 'No seleccionado'}")
            print(f"Tipo de documento: {tipo_documento if tipo_documento else 'No seleccionado'}")
            print(f"Fecha inicio: {fecha_inicio if fecha_inicio else 'No seleccionada'}")
            print(f"Fecha fin: {fecha_fin if fecha_fin else 'No seleccionada'}")
            
            confirmacion = input("\n¿Desea proceder con estos filtros? (s/n): ").strip().lower()
            if confirmacion != 's':
                print("Operación cancelada por el usuario.")
                exit()
            
            crawler = SUCOPCrawler(
                estado=estado,
                tipo_documento=tipo_documento,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            crawler.run()
            
        elif opcion == "2":
            # Generar CSV desde JSON existente
            json_file = input("\nNombre del archivo JSON (Enter para usar 'normativas.json'): ").strip()
            if not json_file:
                json_file = 'normativas.json'
                
            csv_file = input("Nombre del archivo CSV a generar (Enter para usar 'normativas.csv'): ").strip()
            if not csv_file:
                csv_file = 'normativas.csv'
            
            print(f"\nGenerando CSV desde {json_file}...")
            SUCOPCrawler.json_to_csv(json_file, csv_file)
            
        else:
            print("Opción no válida.")
        
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        print("\nProceso finalizado.") 