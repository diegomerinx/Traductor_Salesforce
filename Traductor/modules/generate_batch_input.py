import time
import os
import json
from .properties import *

logger = get_logger(__file__)

keys_dict = {}

def create_request(label, custom_id):
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": PROMPT
                },
                {
                    "role": "user",
                    "content": label
                }
            ],
            "max_tokens": 1000
        }
    }

def save_keys():
    with open(KEYS_FILE_PATH, "w", encoding=ENCODING) as file:
        json.dump(keys_dict, file, ensure_ascii=False, indent=4)
    logger.info(f"Archivo JSON con las keys guardado en: {KEYS_FILE_PATH}")

def process_line(line, index):
    if line.startswith("#"):
        logger.debug(f"Línea comentada: {line}")
        return None
    logger.debug(f"{index} - Procesando línea: {line}")
    parts = line.split("\t", 1)
    if len(parts) == 2:
        key, label = parts
        custom_id = f"request-{index}"
        keys_dict[key] = custom_id
        return create_request(label, custom_id)
        
    logger.debug(f"Línea no traducible: {line}")
    return None

def generate_input_files(input_path=SOURCE_FILE_PATH, max_lines=MAX_BATCH_INPUT_LINES_INT):
    input_files_paths = []
    logger.info(f"Iniciando la creación de solicitudes batch a partir del archivo {input_path}")

    def read_lines(filepath):
        with open(filepath, "r", encoding=ENCODING) as file:
            yield from file

    file_number = 1
    jsonl_file = None
    index = 1
    line_count = max_lines

    for line in read_lines(input_path):
        request = process_line(line.rstrip(), index)

        if request:
            line_count += 1
            index += 1
            if line_count > max_lines:
                line_count = 1
                if jsonl_file:
                    jsonl_file.close()
                input_file_path = f"{BATCH_DATA_ROOT}batch_part_{file_number}.jsonl"
                os.makedirs(os.path.dirname(input_file_path), exist_ok=True)
                input_files_paths.append(input_file_path)
                jsonl_file = open(input_file_path, "w", encoding=ENCODING)
                file_number += 1
            jsonl_file.write(json.dumps(request, ensure_ascii=False) + "\n")
    
    if jsonl_file:
        jsonl_file.close()

    logger.debug(f"Total de solicitudes creadas: {index - 1}")

    save_keys()

    logger.info(f"Archivos JSONL con las solicitudes batch guardados en: {BATCH_DATA_ROOT}")
    return input_files_paths

def generate_batch_input():
    start_time = time.time()
    input_files = generate_input_files()
    end_time = time.time()
    logger.info(f"Tiempo total de creación de solicitudes batch: {(end_time - start_time):.2f} segundos")
    return input_files
