import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, Future
from modules.properties import *
import modules.export_batch as export_batch
import modules.clean_file as clean_file

logger = get_logger(__file__)

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.minsize(400, 250)
        self.file_path = None
        self.progress_bar = None
        self.executor = ThreadPoolExecutor(max_workers=5)

        self.title("Procesador de archivos STF")

        container = tk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        self.label = tk.Label(container, text="Bienvenido al programa de procesamiento de archivos STF")
        self.label.pack(pady=20, anchor=tk.N)

        self.check_button = tk.Button(container, text="Seleccionar Archivo", command=self.select_file)
        self.check_button.pack(pady=20, anchor=tk.N)

        self.center_window()

        self.check_previous_state()

    def center_window(self, window=None):
        window = window or self
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def check_previous_state(self):
        if os.path.exists(STATE_FILE):
            resume = messagebox.askyesno("Reanudar proceso", "Se ha detectado un progreso anterior. ¿Desea reanudar el proceso?")
            if resume:
                self.start_processing(resume=True)
            else:
                self.configure_window()
        else:
            self.configure_window()

    def configure_window(self):
        clean_all()

        file_path = self.check_input_directory()
        if file_path:
            self.check_button.config(text=f"Comenzar", command=lambda: self.confirm_file(file_path))
        else:
            self.check_button.config(text="Seleccionar Archivo", command=self.select_file)

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecciona el archivo .stf",
            filetypes=[("STF files", "*.stf")],
            initialdir=working_dir_path
        )
        if file_path:
            if not os.path.commonpath([os.path.abspath(file_path), os.path.abspath(INPUT_ROOT)]).startswith(os.path.abspath(INPUT_ROOT)):
                self.copy_file_to_input(file_path)
            else:
                self.file_path = file_path
            self.start_processing()

    def copy_file_to_input(self, file_path):
        clean_root(INPUT_ROOT)
        input_file_path = os.path.join(INPUT_ROOT, SOURCE_FILE_NAME)
        shutil.copy(file_path, input_file_path)
        self.file_path = input_file_path
        logger.info(f"Archivo copiado a {input_file_path}")

    def confirm_file(self, file_path):
        self.file_path = file_path
        self.start_processing()

    def start_processing(self, resume=False):
        for widget in self.winfo_children():
            widget.pack_forget()

        container = tk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        self.progress_bar = ProgressBar(container)
        self.progress_bar.pack(pady=20, anchor=tk.N)

        self.cancel_button = tk.Button(container, text="Cancelar", command=self.show_confirmation_window)
        self.cancel_button.pack(pady=20, anchor=tk.S)

        self.center_window()

        if not resume:
            self.update_progress(10, "Limpieza del archivo")
            future = self.executor.submit(clean_file.clean_file, self.file_path)
            self.check_future(future, self.after_clean_file)
        else:
            file_parts = get_file_parts(BATCH_DATA_ROOT)
            self.export_file_parts(file_parts)

    def check_future(self, future: Future, callback):
        if future.done():
            result = future.result()
            self.after(0, callback, result)
        else:
            self.after(100, self.check_future, future, callback)

    def after_clean_file(self, success):
        if success:
            self.update_progress(30, "Generación del archivo de input para el batch")
            from modules.generate_batch_input import generate_batch_input
            future = self.executor.submit(generate_batch_input)
            self.check_future(future, self.after_generate_batch_input)
        else:
            messagebox.showerror("Error", "Error al limpiar el archivo.")

    def after_generate_batch_input(self, file_parts):
        self.export_file_parts(file_parts)

    def export_file_parts(self, file_parts):
        self.update_progress(60, "Exportación del batch")
        future = self.executor.submit(export_batch.export_batch, file_parts, self.progress_bar)
        self.check_future(future, self.after_export_batch)

    def after_export_batch(self, batch_exported):
        if batch_exported:
            from modules.process_batch_output import process_batch_output
            future = self.executor.submit(process_batch_output)
            self.check_future(future, self.after_process_batch_output)
        else:
            logger.warning("El proceso de Traducción no se ha completado")

    def after_process_batch_output(self, output_processed):
        if output_processed:
            self.update_progress(100, "Proceso de Traducción Completado")
            self.after(0, self.backup)
        else:
            logger.warning("Error al procesar el batch output")
            messagebox.showerror("Error", "Error al procesar el batch output")

    def backup(self):
        info_text = save_backup()
        messagebox.showinfo("Proceso finalizado", info_text)
        self.after(0, self.finalize)

    def finalize(self):
        self.destroy()

    def update_progress(self, value, text):
        if self.progress_bar:
            self.progress_bar.update(value, text)

    def check_input_directory(self):
        input_dir = INPUT_ROOT
        if not os.path.exists(input_dir):
            return None

        stf_files = [file for file in os.listdir(input_dir) if file.endswith(".stf")]
        if len(stf_files) == 1:
            return os.path.join(input_dir, stf_files[0])
        return None

    def show_confirmation_window(self):
        self.confirmation_window = tk.Toplevel(self)
        self.confirmation_window.minsize(400, 250)
        self.confirmation_window.title("Confirmación")

        container = tk.Frame(self.confirmation_window)
        container.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(container, text="¿Está seguro de que desea cancelar el proceso?")
        label.pack(pady=10, anchor=tk.N)

        button_frame = tk.Frame(container)
        button_frame.pack(side=tk.BOTTOM, pady=20, anchor=tk.S)

        yes_button = tk.Button(button_frame, text="Sí", command=self.cancel_process)
        yes_button.pack(side=tk.LEFT, padx=20)

        no_button = tk.Button(button_frame, text="No", command=self.abort_cancel)
        no_button.pack(side=tk.RIGHT, padx=20)

        self.center_window(self.confirmation_window)

    def cancel_process(self):
        logger.info("Cancelando el proceso...")
        export_batch.cancel_flag = True
        export_batch.wait_event.set()
        logger.debug("wait_event set")
        self.update_progress(self.progress_bar.progress.get(), "Cancelando el proceso...")
        if self.confirmation_window:
            self.confirmation_window.destroy()
        self.ask_save_progress()

    def abort_cancel(self):
        logger.info("Reanudando el proceso...")
        current_progress = self.progress_bar.progress.get()
        current_message = self.progress_bar.label.cget("text")
        if self.confirmation_window:
            self.confirmation_window.destroy()
        else:
            self.update_progress(current_progress, current_message)

    def ask_save_progress(self):
        save_progress = messagebox.askyesno("Guardar progreso", "¿Desea guardar el progreso?")
        self.finalize_cancel(save_progress)

    def finalize_cancel(self, save_progress):
        self.executor.shutdown(wait=True)
        self.destroy()

        if save_progress:
            logger.info(f"Proceso cancelado.")
        else:
            logger.info("No se guardará el progreso actual. Eliminando archivos.")
            clean_all()


class ProgressBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.progress = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress, maximum=100)
        self.progress_bar.pack(pady=20)
        self.label = tk.Label(self, text="")
        self.label.pack(pady=10)
        self.update(0, "Iniciando proceso")

    def update(self, value, text):
        self.progress.set(value)
        self.label.config(text=text)
        self.update_idletasks()

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
