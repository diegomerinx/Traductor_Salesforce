import psutil
import json
import configparser
import logging
from logging import FileHandler
import os
import shutil
from datetime import datetime

package_root_path = None
working_dir_path = None

def set_main_directory(f):
    global package_root_path, working_dir_path

    main_file_path = os.path.abspath(f)
    directory = os.path.dirname(main_file_path)
    os.chdir(directory)

    package_root_path = directory
    working_dir_path = os.path.dirname(directory)
    init_config()

def init_config():
    global RESOURCES_ROOT, STATIC_RESOURCES_ROOT, LOG_ROOT, WRONG_KEY_TEXT, WRONG_FLOW_TYPE1, WRONG_FLOW_TYPE2
    global ENCODING, MODEL_NAME, PROMPT, KEYS_FILE_PATH, BATCH_OUTPUT_FILE_PATH, CHARACTER_LIMITS_FILE_PATH
    global METADATA_TYPES_FILE_PATH, BATCH_DATA_ROOT, MAX_BATCH_INPUT_LINES_INT, STATE_FILE, API_KEY
    global INPUT_DIR_NAME, OUTPUT_DIR_NAME, SOURCE_FILE_NAME, TRANSLATED_FILE_NAME, EXCEL_FILE_NAME, CONFIGURATION_FILE_PATH
    global DUPLICATED_KEYS_FILE_NAME, UNTRANSLATABLE_LINES_FILE_NAME, INPUT_ROOT, OUTPUT_ROOT, SOURCE_FILE_PATH
    global TRANSLATED_FILE_PATH, EXCEL_FILE_PATH, DUPLICATED_KEYS_FILE_PATH, UNTRANSLATABLE_LINES_FILE_PATH

    CONFIGURATION_FILE_PATH = os.path.join(package_root_path, "resources/static/config.properties")
    CONFIGURATION_SETTINGS = "DEFAULT"

    configuration = configparser.ConfigParser()
    configuration.read(CONFIGURATION_FILE_PATH)
    default_configuration = configuration[CONFIGURATION_SETTINGS]

    RESOURCES_ROOT = default_configuration["RESOURCES_ROOT"]
    STATIC_RESOURCES_ROOT = default_configuration["STATIC_RESOURCES_ROOT"]
    LOG_ROOT = default_configuration["LOG_ROOT"]
    WRONG_KEY_TEXT = default_configuration["WRONG_KEY_TEXT"]
    WRONG_FLOW_TYPE1 = default_configuration["WRONG_FLOW_TYPE1"]
    WRONG_FLOW_TYPE2 = default_configuration["WRONG_FLOW_TYPE2"]
    ENCODING = default_configuration["ENCODING"]
    MODEL_NAME = default_configuration["MODEL_NAME"]
    PROMPT = default_configuration["PROMPT"]

    KEYS_FILE_PATH = default_configuration["KEYS_FILE_PATH"]
    BATCH_OUTPUT_FILE_PATH = default_configuration["BATCH_OUTPUT_FILE_PATH"]
    CHARACTER_LIMITS_FILE_PATH = default_configuration["CHARACTER_LIMITS_FILE_PATH"]
    METADATA_TYPES_FILE_PATH = default_configuration["METADATA_TYPES_FILE_PATH"]
    BATCH_DATA_ROOT = default_configuration["BATCH_DATA_ROOT"]
    MAX_BATCH_INPUT_LINES_INT = int(default_configuration["MAX_BATCH_INPUT_LINES"])
    STATE_FILE = default_configuration["STATE_FILE"]
    API_KEY = default_configuration["API_KEY"]

    INPUT_DIR_NAME = default_configuration["INPUT_DIR_NAME"]
    OUTPUT_DIR_NAME = default_configuration["OUTPUT_DIR_NAME"]
    SOURCE_FILE_NAME = default_configuration["SOURCE_FILE_NAME"]
    TRANSLATED_FILE_NAME = default_configuration["TRANSLATED_FILE_NAME"]
    EXCEL_FILE_NAME = default_configuration["EXCEL_FILE_NAME"]
    DUPLICATED_KEYS_FILE_NAME = default_configuration["DUPLICATED_KEYS_FILE_NAME"]
    UNTRANSLATABLE_LINES_FILE_NAME = default_configuration["UNTRANSLATABLE_LINES_FILE_NAME"]

    prepare_dirs()

def get_logger(script_path):
    script_name = os.path.splitext(os.path.basename(script_path))[0]
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False


    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_ROOT, f"{script_name}_{current_time}.log")
    file_handler = FileHandler(log_file, encoding=ENCODING)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(threadName)s - %(message)s"))
    logger.addHandler(file_handler)

    return logger

def get_file_parts(directory):
    jsonl_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".jsonl"):
                jsonl_files.append(os.path.join(root, file))
    return jsonl_files

def clean_all():
    clean_state()
    clean_root(BATCH_DATA_ROOT)

def clean_root(root_dir):
    def remove_file(file_path, n_try=0):
        DELETE_TRIES = 5
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except PermissionError:
                print(f"Ha ocurrido un error al eliminar el archivo {file_path}. Iniciando intento {n_try}/{DELETE_TRIES}")
                handle_permission_error(file_path)
                if n_try < DELETE_TRIES:
                    remove_file(file_path, n_try + 1)

    for root, _, files in os.walk(root_dir):
        file_paths = [os.path.join(root, file) for file in files]
        
        for file_path in file_paths:
            remove_file(file_path)

def handle_permission_error(file_path):
    for proc in psutil.process_iter(['pid', 'name', 'open_files']):
        try:
            open_files = proc.info['open_files']
            if open_files:
                for open_file in open_files:
                    if open_file.path == file_path:
                        proc.terminate()
                        proc.wait(timeout=3)
                        print(f"Terminado proceso {proc.info['name']} con PID {proc.info['pid']} que estaba usando el archivo {file_path}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


    
def clean_state():
    files_to_remove = [STATE_FILE, BATCH_OUTPUT_FILE_PATH, KEYS_FILE_PATH]
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)

def save_state(processed_parts):
    with open(STATE_FILE, "w") as state_file:
        json.dump(processed_parts, state_file)

def save_backup():
    root_logger = logging.getLogger()
    handlers = root_logger.handlers[:]
    for handler in handlers:
        if isinstance(handler, FileHandler):
            handler.close()
            root_logger.removeHandler(handler)
    
    now = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
    backup_dir = os.path.join(working_dir_path, f"backup_{now}")

    if os.path.exists(backup_dir):
        try:
            shutil.rmtree(backup_dir)
        except Exception as e:
            return f"Ha ocurrido un error al intentar eliminar el directorio \"{backup_dir}\" para crear uno nuevo: {e}"

    os.makedirs(backup_dir)

    for root, _, files in os.walk(package_root_path):
        for file in files:
            full_path = os.path.join(root, file)

            if file.endswith(".py"):
                continue

            relative_path = os.path.relpath(full_path, package_root_path)
            backup_path = os.path.join(backup_dir, relative_path)

            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            absolute_static_resources_root = os.path.abspath(STATIC_RESOURCES_ROOT)
            absolute_input_root = os.path.abspath(INPUT_ROOT)
            absolute_output_root = os.path.abspath(OUTPUT_ROOT)            

            if (os.path.commonpath([os.path.abspath(full_path), absolute_static_resources_root]) == absolute_static_resources_root or
                os.path.commonpath([os.path.abspath(full_path), absolute_input_root]) == absolute_input_root or
                os.path.commonpath([os.path.abspath(full_path), absolute_output_root]) == absolute_output_root):
                try:
                    shutil.copy2(full_path, backup_path)
                except PermissionError:
                    return f"Ha ocurrido un error de permisos al copiar el archivo {full_path} a {backup_path}"
                except Exception as e:
                    return f"Ha ocurrido un error inesperado al copiar el archivo {full_path} a {backup_path}\n{e}"
            else:
                try:
                    shutil.move(full_path, backup_path)
                except PermissionError:
                    return f"Ha ocurrido un error de permisos al mover el archivo {full_path} a {backup_path}"
                except Exception as e:
                    return f"Ha ocurrido un error inesperado al mover el archivo {full_path} a {backup_path}\n{e}"

    return f"Copia de seguridad creada en {backup_dir}"

def prepare_dirs():
    global INPUT_ROOT, OUTPUT_ROOT, SOURCE_FILE_PATH, TRANSLATED_FILE_PATH, EXCEL_FILE_PATH, DUPLICATED_KEYS_FILE_PATH, UNTRANSLATABLE_LINES_FILE_PATH

    try:
        INPUT_ROOT = os.path.join(working_dir_path, INPUT_DIR_NAME)
        OUTPUT_ROOT = os.path.join(working_dir_path, OUTPUT_DIR_NAME)
        
        SOURCE_FILE_PATH = os.path.join(INPUT_ROOT, SOURCE_FILE_NAME)
        TRANSLATED_FILE_PATH = os.path.join(OUTPUT_ROOT, TRANSLATED_FILE_NAME)
        EXCEL_FILE_PATH = os.path.join(OUTPUT_ROOT, EXCEL_FILE_NAME)
        DUPLICATED_KEYS_FILE_PATH = os.path.join(OUTPUT_ROOT, DUPLICATED_KEYS_FILE_NAME)
        UNTRANSLATABLE_LINES_FILE_PATH = os.path.join(OUTPUT_ROOT, UNTRANSLATABLE_LINES_FILE_NAME)
        
        required_dirs = [
            RESOURCES_ROOT, 
            BATCH_DATA_ROOT,
            LOG_ROOT,
            INPUT_ROOT, 
            OUTPUT_ROOT
        ]

        required_files = [
            CHARACTER_LIMITS_FILE_PATH, 
            CONFIGURATION_FILE_PATH, 
            METADATA_TYPES_FILE_PATH
        ]
        
        for directory in required_dirs:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        for file in required_files:
            if not os.path.exists(file):
                print("La configuración del paquete es incorrecta")
                return False
        
        return True
    
    except Exception:
        print("La configuración del paquete es incorrecta")
        return False