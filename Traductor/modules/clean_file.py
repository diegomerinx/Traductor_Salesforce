from tkinter import messagebox
import os
import shutil
from .properties import *

logger = get_logger(__file__)

def filter_and_clean_lines(input_file):
    logger.debug(f"Abriendo el archivo: {input_file}")
    with open(input_file, "r", encoding=ENCODING) as file:
        lines = file.readlines()
    original_lines = len(lines)
    filtered_lines = []
    flow_lines = []
    last_flow_version = {}
    unique_keys = set()
    duplicated_lines = []
    untranslatable_lines = []

    logger.debug(f"Total de líneas leídas: {original_lines}")

    for line in lines:
        parts = line.split("\t", 1)
        key = parts[0]

        if line.rstrip():
            if key in unique_keys:
                duplicated_lines.append(line)
                continue
            unique_keys.add(key)

            if WRONG_KEY_TEXT in key and (WRONG_FLOW_TYPE1 in key or WRONG_FLOW_TYPE2 in key):
                untranslatable_lines.append(line)
                continue

        if line.lower().startswith("flow"):
            flow_lines.append(line)
            flow_key_parts = key.split(".")
            flow_key = ".".join(flow_key_parts[0:3])
            logger.debug(f"Procesando línea de flujo: {key}")

            if not flow_key_parts[3].isdigit():
                filtered_lines.append(line)
                logger.debug(f"Versión de flujo no numérica detectada, línea agregada directamente: {line.strip()}")
                continue

            flow_version = int(flow_key_parts[3])
            if not (flow_key in last_flow_version and flow_version <= last_flow_version[flow_key]):
                last_flow_version[flow_key] = flow_version
                logger.debug(f"Actualizando última versión del flujo {flow_key} a {flow_version}")
        else:
            filtered_lines.append(line)
            logger.debug(f"Línea no relacionada con flujos, agregada directamente: {line.strip()}")

    for key, version in last_flow_version.items():
        key_with_version = key + "." + str(version)
        for line in flow_lines:
            if key_with_version in line:
                filtered_lines.append(line)
                logger.debug(f"Línea de flujo con la versión más reciente agregada: {line.strip()}")

    logger.debug(f"Escribiendo {len(filtered_lines)} líneas filtradas en el archivo: {SOURCE_FILE_PATH}")
    with open(SOURCE_FILE_PATH, "w", encoding=ENCODING) as file:
        file.writelines(filtered_lines)
    
    logger.info(f"Filtradas {original_lines - len(filtered_lines)}/{original_lines} líneas de {input_file} a {SOURCE_FILE_PATH}")

    if duplicated_lines:
        with open(DUPLICATED_KEYS_FILE_PATH, "w", encoding=ENCODING) as file:
            file.writelines(duplicated_lines)
            logger.info(f"Guardadas {len(duplicated_lines)} keys duplicadas en {DUPLICATED_KEYS_FILE_PATH}")
            
    if untranslatable_lines:
        with open(UNTRANSLATABLE_LINES_FILE_PATH, "w", encoding=ENCODING) as file:
            file.writelines(untranslatable_lines)
            logger.info(f"Guardadas {len(untranslatable_lines)} líneas no traducibles en {UNTRANSLATABLE_LINES_FILE_PATH}")

def clean_file(input_file):
    if os.path.exists(STATE_FILE):
        logger.warning(f"El archivo {STATE_FILE} ya existe. Se omite este proceso")
        messagebox.showinfo("Información", f"El archivo {STATE_FILE} ya existe. Se omite este proceso")
        return True

    if not input_file:
        messagebox.showwarning("Advertencia", "No se ha seleccionado ningún archivo.")
        logger.debug("No se ha seleccionado ningún archivo.")
        return False

    if not os.path.samefile(input_file, SOURCE_FILE_PATH):
        shutil.copy(input_file, SOURCE_FILE_PATH)
    logger.debug(f"Archivo .stf preparado: {input_file}")

    base, ext = os.path.splitext(input_file)
    new_name = base + "_old_flow_versions" + ext
    index = 0
    while True:
        try:
            os.rename(input_file, new_name)
            break
        except FileExistsError:
            index += 1
            new_name = f"{base}_old_flow_versions_{index}{ext}"

    logger.info(f"Archivo renombrado de {input_file} a {new_name}")
    input_file = new_name

    filter_and_clean_lines(input_file)
    return True
