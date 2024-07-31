import time
import threading
import os
import json
from openai import OpenAI
from .properties import *

logger = get_logger(__file__)

client = OpenAI(api_key=API_KEY)
cancel_flag = False
wait_event = threading.Event()

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as state_file:
            return json.load(state_file)
    return []

def dynamic_wait_time(start_time, min_wait=10, max_wait=600):
    elapsed_time = time.time() - start_time
    wait_time = min(max_wait, max(min_wait, int(elapsed_time / 60)))
    logger.debug(f"Tiempo de espera ajustado a: {wait_time} segundos.")
    return wait_time

def process_batch(file_path):
    logger.debug(f"Subiendo el archivo de entrada {file_path}...")
    batch_input_file = None
    with open(file_path, "rb") as file:
        batch_input_file = client.files.create(
            file=file,
            purpose="batch"
        )
        
    if batch_input_file is None:
        return None

    logger.debug(f"Archivo de entrada subido con ID: {batch_input_file.id}")

    batch_input_file_id = batch_input_file.id
    logger.debug("Creando el batch...")

    batch = client.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"description": f"Proceso de traducción del archivo {file_path}"}
    )

    logger.debug(f"Batch creado con ID: {batch.id}")

    logger.debug("Supervisando el estado del batch...")
    start_time = time.time()
    status = client.batches.retrieve(batch.id).status
    while status not in ["completed", "failed", "cancelled", "expired"]:
        wait_time = dynamic_wait_time(start_time)
        logger.debug(f"Estado actual del batch: {status}. Esperando {wait_time} segundos.")
        wait_event.wait(wait_time)
        if cancel_flag:
            try:
                client.batches.cancel(batch.id)
                logger.debug("Batch cancelado.")
                return None
            except Exception as e:
                logger.error(f"Ha ocurrido el siguiente error al intentar cancelar el batch; {e}")
        status = client.batches.retrieve(batch.id).status

    if status == "completed":
        logger.debug("El batch se ha completado. Obteniendo resultados...")
        output_file_id = client.batches.retrieve(batch.id).output_file_id
        content = client.files.content(output_file_id)
        return content.read()
    else:
        logger.error(f"El batch no se completó exitosamente. Estado final: {status}")
        return None

def export_batch(file_parts, progress_bar):
    if not file_parts:
        logger.warning(f"No se han pasado como parámetro los archivos de input para el batch. Buscando en la carpeta {BATCH_DATA_ROOT}")
        file_parts = get_file_parts(BATCH_DATA_ROOT)
        if not file_parts:
            logger.error(f"No se han encontrado archivos .jsonl en {BATCH_DATA_ROOT}")
            return False

    processed_parts = load_state()

    if file_parts == processed_parts:
        logger.warning("El proceso de traducción ya había finalizado")
        return True

    if processed_parts: 
        logger.info(f"Reanudando proceso después de cancelación. Los archivos que ya han sido procesados son: {', '.join(processed_parts)}")

    for file_part in file_parts:
        progress_bar.update(min(90, progress_bar.progress.get() + 30/len(file_parts)), f"Procesando batch {file_part}")
        if file_part in processed_parts:
            continue
        result = process_batch(file_part)
        if result:
            with open(BATCH_OUTPUT_FILE_PATH, "ab") as output_file:
                output_file.write(result)
            processed_parts.append(file_part)
            save_state(processed_parts)
            logger.info(f"Archivo {file_part} processado. Guardando progreso en {STATE_FILE}")
        if cancel_flag:
            logger.debug("Handling cancel")
            return False

    logger.info("Proceso de traducción completado.")
    return True