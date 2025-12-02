"""
Módulo de configuración para la aplicación TVK6 Serial Console.

Centraliza todas las constantes y parámetros para facilitar su modificación.
"""
import re

# --- Configuración Serial ---
PORT = 'COM4'   # IMPORTANTE: AJUSTA ESTO al puerto correcto donde esté conectado el TVK6
BAUDRATE = 4800
TIMEOUT = 2

# --- Expresiones Regulares ---
# Limpia códigos de escape ANSI/VT100 (crucial para el parsing)
ANSI_ESCAPE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')