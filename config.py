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
# Regex mejorada para limpiar todos los códigos de escape ANSI/VT100,
# incluyendo secuencias CSI (ESC [...) y otras como (ESC # ...), y códigos de un solo carácter.
# Esta regex simple y agresiva elimina cualquier secuencia que comience con ESC (\x1b)
# y los caracteres de control SO/SI. Esto es más robusto para la salida del TVK6.
ANSI_ESCAPE = re.compile(r'(\x1b\[[0-9;?]*[A-Za-z])|(\x1b[#()][A-Z0-9])|[\x0e\x0f]')