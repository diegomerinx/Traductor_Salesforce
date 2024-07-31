import json
import os
import pandas
import re
from .properties import *

logger = get_logger(__file__)

translations = {}
batchoutput = []
html_tag_pattern = re.compile(r"<.*?>")
special_character_patterm = re.compile(r"(\n|\t|\r)")

with open(CHARACTER_LIMITS_FILE_PATH, "r", encoding=ENCODING) as file:
    character_limits = json.load(file)
logger.info(f"Archivo de límites de carácteres leído: {CHARACTER_LIMITS_FILE_PATH}")

with open(KEYS_FILE_PATH, "r", encoding=ENCODING) as file:
    keys = json.load(file)
logger.info(f"Archivo de claves leído: {KEYS_FILE_PATH}")

with open(METADATA_TYPES_FILE_PATH, "r", encoding=ENCODING) as file:
    metadata_types = json.load(file)
logger.info(f"Archivo de definición de metadatos leído: {METADATA_TYPES_FILE_PATH}")

def get_label_type(key):
    for metadata_type, pattern in metadata_types.items():
        if re.search(pattern, key):
            return metadata_type
    return "DEFAULT_LABEL_TYPE"

def exceeds_char_limit(label_type, translated_label):
    char_limit = character_limits.get(label_type, character_limits["DEFAULT_LABEL_TYPE"])
    if translated_label is None:
        logger.error(f"translated_label para la key \"{label_type}\" es None")
        return False
    return len(translated_label) > char_limit

def write_long_translation_to_excel(key, original_label, translated_label, char_limit):
    df = pandas.DataFrame([[key, original_label, translated_label, char_limit, len(translated_label)]], columns=["Key", "Original", "Traducido", "Límite de Carácteres", "Número de Carácteres"])
    if os.path.exists(EXCEL_FILE_PATH):
        existing_df = pandas.read_excel(EXCEL_FILE_PATH)
        df = pandas.concat([existing_df, df]).drop_duplicates(subset=["Key"]).reset_index(drop=True)
    df.to_excel(EXCEL_FILE_PATH, index=False)
    logger.info(f"Escribiendo traducción larga en el archivo Excel: {EXCEL_FILE_PATH}")

logger.info("Iniciando la reconstrucción del archivo con las traducciones.")

def replace_special_characters(text):
    return re.sub(special_character_patterm, lambda match: {"\n": "\\n", "\t": "\\t", "\r": "\\r"}[match.group()], text)

def process_batch_output():
    if not os.path.exists(BATCH_OUTPUT_FILE_PATH):
        logger.error(f"No se ha encontrado el archivo resultante del batch \"{BATCH_OUTPUT_FILE_PATH}\"")
        return False

    with open(BATCH_OUTPUT_FILE_PATH, "r", encoding=ENCODING) as file:
        for line in file:
            batchoutput.append(json.loads(line))
    logger.info(f"Archivo de batch output leído: {BATCH_OUTPUT_FILE_PATH}")

    for item in batchoutput:
        try:
            custom_id = item["custom_id"]
            translated_text = item["response"]["body"]["choices"][0]["message"]["content"].rstrip()
            if translated_text:
                translations[custom_id] = translated_text
                logger.debug(f"Traducción obtenida para el custom_id {custom_id}")
            else:
                logger.error(f"No existe traducción para el custom_id {custom_id}")
        except KeyError as e:
            logger.error(f"Error al obtener la traducción para el custom_id {custom_id}: {e}")
    
    os.makedirs(os.path.dirname(TRANSLATED_FILE_PATH), exist_ok=True)
    if not os.path.exists(SOURCE_FILE_PATH):
        logger.error(f"No se ha encontrado el archivo de entrada en {SOURCE_FILE_PATH}")
        return False
    
    with open(SOURCE_FILE_PATH, "r", encoding=ENCODING) as infile, open(TRANSLATED_FILE_PATH, "w", encoding=ENCODING) as outfile:
        for line in infile:
            if line.startswith("#"):
                outfile.write(line)
                logger.debug(f"Escribiendo línea no traducible: {line.rstrip()}")
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                key, label = parts
                if key not in keys:
                    logger.warning(f"La key \"{key}\" no está dentro de {KEYS_FILE_PATH}")
                    continue
                request_id = keys[key]

                if request_id not in translations:
                    logger.warning(f"La key \"{request_id}\" no tiene traducción asociada")
                    continue
                translated_label = replace_special_characters(translations[request_id])
                label_type = get_label_type(key)
                if exceeds_char_limit(label_type, translated_label):
                    char_limit = character_limits[label_type]
                    write_long_translation_to_excel(key, label, translated_label, char_limit)
                    logger.debug(f"Escribiendo traducción larga en el Excel para key {key}")
                else:
                    outfile.write(f"{key}\t{translated_label}\n")
                    logger.debug(f"Escribiendo línea traducida para key {key}: {translated_label}")
            else:
                outfile.write(line)
                logger.debug(f"Escribiendo línea no traducible: {line.rstrip()}")

    logger.info(f"Archivo traducido guardado en: {TRANSLATED_FILE_PATH}")
    return True