Contexto del Proyecto: Interfaz Gráfica para TVK6
1. Propósito General y Funcionalidad Clave
Este proyecto es una aplicación de escritorio para Windows, macOS o Linux que sirve como una interfaz gráfica de usuario (GUI) moderna para un dispositivo de hardware llamado TVK6.

El TVK6 es un equipo de calibración (probablemente para medidores de energía) que se comunica a través de un puerto serie (COM) y presenta su propia interfaz en modo texto, similar a un terminal VT100.

La aplicación envuelve y moderniza este dispositivo, ofreciendo una experiencia de usuario gráfica e intuitiva. En lugar de que el usuario interactúe con una pantalla de texto y códigos de control, la aplicación interpreta esa salida y la traduce en botones, tablas y formularios visuales.

Funcionalidades más importantes:

Automatización: Ejecuta secuencias de comandos para realizar tareas complejas con un solo clic, como la "Calibración Rápida".
Gestión de Datos: Almacena modelos de medidores (con sus constantes y límites) en una base de datos para reutilizarlos fácilmente.
Historial de Calibraciones: Guarda un registro persistente de cada calibración realizada, incluyendo todos los parámetros y resultados.
Generación de Reportes: Crea certificados de calibración profesionales en formato PDF, listos para ser impresos o enviados.
Visualización en Tiempo Real: Muestra los resultados de la calibración en una tabla gráfica que colorea los valores según si pasan o fallan los límites establecidos (di/ds).
2. Tecnologías Utilizadas
Lenguaje de Programación: Python.
Framework de GUI: PySide6 (bindings oficiales de Python para el framework Qt). La interfaz está definida en un archivo .ui (interfaz_tvk6.ui) que se carga dinámicamente.
Comunicación con Hardware: Librería pyserial para la comunicación a través del puerto serie (COM).
Base de Datos: SQLite (a través del módulo sqlite3 de la librería estándar de Python) para almacenar los modelos de medidores y el historial de calibraciones en un archivo local (medidores.db).
Generación de PDF: Librería reportlab para crear los certificados de calibración.
Concurrencia: QThread de PySide6 para manejar la comunicación serie en un hilo de ejecución separado, evitando que la interfaz gráfica se congele.
3. Arquitectura del Software
La arquitectura es el punto más ingenioso del proyecto y se basa en un patrón de "Screen Scraping" (análisis de pantalla) inteligente:

SerialWorker: Se ejecuta en un hilo secundario y es el único componente que habla directamente con el TVK6. Lee continuamente la salida de texto cruda del dispositivo (incluyendo códigos de control ANSI) y la emite como una señal.
ScreenEmulator: Recibe el texto crudo del SerialWorker. Su función es interpretar los códigos de control ANSI (como "mover cursor a la fila 5, columna 10" o "borrar línea") y reconstruir una "fotografía" o snapshot de cómo se vería la pantalla del terminal del TVK6 en un momento dado.
StateManager: Es el cerebro de la aplicación. Recibe el snapshot de la pantalla del emulador. Usando un archivo de configuración (menu_config.json), detecta en qué menú o estado se encuentra el dispositivo (ej: "Menú Principal", "Vista de Calibración") buscando palabras clave en el texto de la pantalla.
MenuManager: Una vez que el StateManager determina el estado actual, el MenuManager consulta el mismo archivo menu_config.json para saber qué botones dinámicos debe dibujar en la interfaz gráfica.
MainWindow: Orquesta todo. Gestiona la ventana principal, conecta las señales de los botones a los slots que envían comandos de vuelta al SerialWorker, y maneja la visibilidad de los diferentes paneles gráficos (como la tabla de calibración o las cabeceras de datos).
SequenceManager: Cuando se activa una tarea automática (como la "Calibración Rápida"), este gestor toma una lista de comandos y los envía uno por uno al SerialWorker, con pausas entre ellos para dar tiempo al TVK6 a procesarlos.
En resumen, el flujo es: Hardware TVK6 -> SerialWorker (lectura) -> ScreenEmulator (reconstrucción) -> StateManager (detección de estado) -> MenuManager y MainWindow (actualización de la GUI). La interacción del usuario sigue el camino inverso.

