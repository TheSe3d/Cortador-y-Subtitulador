"""Interfaz gráfica (tkinter) de Subtitulador Automático."""

import os
import queue
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from .core import IDIOMAS, MODELOS, configurar_cuda, procesar

C = {
    "fondo": "#0f1117",
    "panel": "#171a24",
    "consola": "#0b0d13",
    "borde": "#262a38",
    "texto": "#e7e9f0",
    "suave": "#8b90a3",
    "acento": "#7c5cff",
    "acento_hover": "#9478ff",
    "ok": "#3ddc97",
    "error": "#ff6b6b",
    "paso": "#7cc4ff",
}
FUENTE = ("Segoe UI", 10)
FUENTE_TITULO = ("Segoe UI Semibold", 18)
FUENTE_MONO = ("Consolas", 10)
FUENTE_MONO_NEG = ("Consolas", 10, "bold")


class App:
    def __init__(self, root):
        self.root = root
        self.video_path = None
        self.ultimo_dir = None
        self.procesando = False
        self.cola = queue.Queue()

        root.title("Subtitulador Automático")
        root.geometry("1000x840")
        root.minsize(820, 680)
        root.configure(bg=C["fondo"])
        root.option_add("*TCombobox*Listbox.background", C["panel"])
        root.option_add("*TCombobox*Listbox.foreground", C["texto"])

        self._estilos()
        self._construir()
        self._actualizar_controles()
        self._log("Listo. Elige un archivo para comenzar.", "info")
        self.root.after(80, self._revisar_cola)

    def _estilos(self):
        s = ttk.Style(self.root)
        s.theme_use("clam")

        s.configure("TFrame", background=C["fondo"])
        s.configure("Card.TFrame", background=C["panel"])
        s.configure("TLabel", background=C["fondo"], foreground=C["texto"], font=FUENTE)
        s.configure("Card.TLabel", background=C["panel"], foreground=C["texto"], font=FUENTE)
        s.configure("Suave.TLabel", background=C["panel"], foreground=C["suave"], font=FUENTE)
        s.configure("Sub.TLabel", background=C["fondo"], foreground=C["suave"], font=FUENTE)
        s.configure("Titulo.TLabel", background=C["fondo"], foreground=C["texto"],
                    font=FUENTE_TITULO)

        s.configure("Accent.TButton", background=C["acento"], foreground="white",
                    font=("Segoe UI Semibold", 10), padding=(18, 9), borderwidth=0,
                    focuscolor=C["acento"])
        s.map("Accent.TButton",
              background=[("disabled", C["borde"]), ("active", C["acento_hover"])],
              foreground=[("disabled", C["suave"])])

        s.configure("Sec.TButton", background=C["borde"], foreground=C["texto"],
                    font=FUENTE, padding=(14, 8), borderwidth=0, focuscolor=C["borde"])
        s.map("Sec.TButton",
              background=[("disabled", C["panel"]), ("active", "#333a4d")],
              foreground=[("disabled", C["suave"])])

        s.configure("TProgressbar", background=C["acento"], troughcolor=C["borde"],
                    borderwidth=0, thickness=10)

        s.configure("TCombobox", fieldbackground=C["borde"], background=C["borde"],
                    foreground=C["texto"], arrowcolor=C["texto"], borderwidth=0)
        s.map("TCombobox",
              fieldbackground=[("readonly", C["borde"])],
              foreground=[("readonly", C["texto"])],
              selectbackground=[("readonly", C["borde"])],
              selectforeground=[("readonly", C["texto"])])

        s.configure("TSpinbox", fieldbackground=C["borde"], background=C["borde"],
                    foreground=C["texto"], arrowcolor=C["texto"], borderwidth=0)
        s.map("TSpinbox", fieldbackground=[("readonly", C["borde"])],
              foreground=[("readonly", C["texto"])])

        s.configure("TEntry", fieldbackground=C["borde"], foreground=C["texto"],
                    insertcolor=C["texto"], borderwidth=0)

        s.configure("Card.TRadiobutton", background=C["panel"], foreground=C["texto"],
                    font=FUENTE, indicatorbackground=C["borde"], focuscolor=C["panel"])
        s.map("Card.TRadiobutton",
              background=[("active", C["panel"])],
              indicatorbackground=[("selected", C["acento"])],
              foreground=[("disabled", C["suave"])])

        s.configure("Horizontal.TScale", background=C["panel"], troughcolor=C["borde"])

    def _fila(self, parent, r, etiqueta, widget, ayuda=None, pady=7):
        if etiqueta:
            ttk.Label(parent, text=etiqueta, style="Card.TLabel").grid(
                row=r, column=0, sticky="w", pady=pady, padx=(0, 16))
        widget.grid(row=r, column=1, sticky="w", pady=pady)
        if ayuda:
            ttk.Label(parent, text=ayuda, style="Suave.TLabel", wraplength=440,
                      justify="left").grid(row=r, column=2, sticky="w", pady=pady,
                                           padx=(16, 0))

    def _construir(self):
        cont = ttk.Frame(self.root, padding=24)
        cont.pack(fill="both", expand=True)

        ttk.Label(cont, text="Subtitulador Automático", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(cont, text="Corta silencios y genera subtítulos con Whisper",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 18))

        tarjeta = ttk.Frame(cont, style="Card.TFrame", padding=20)
        tarjeta.pack(fill="x")
        tarjeta.columnconfigure(2, weight=1)

        self.btn_elegir = ttk.Button(tarjeta, text="Elegir archivo", style="Sec.TButton",
                                     command=self._elegir)
        self._fila(tarjeta, 0, "Archivo", self.btn_elegir)
        self.lbl_archivo = ttk.Label(tarjeta, text="Ningún archivo seleccionado",
                                     style="Suave.TLabel", wraplength=440)
        self.lbl_archivo.grid(row=0, column=2, sticky="w", pady=7, padx=(16, 0))

        self.modo = tk.StringVar(value="cortar")
        self.radio_solo = ttk.Radiobutton(
            tarjeta, text="Solo subtítulos", value="solo", variable=self.modo,
            style="Card.TRadiobutton", command=self._actualizar_controles)
        self.radio_cortar = ttk.Radiobutton(
            tarjeta, text="Cortar video y subtítulos", value="cortar", variable=self.modo,
            style="Card.TRadiobutton", command=self._actualizar_controles)
        self._fila(tarjeta, 1, "Modo", self.radio_solo,
                   "Genera solo el archivo .srt con los subtítulos. El video no se toca.")
        self._fila(tarjeta, 2, None, self.radio_cortar,
                   "Quita los silencios del video y genera el .srt ya sincronizado con el corte.")

        self.combo_modelo = ttk.Combobox(tarjeta, values=MODELOS, state="readonly", width=14)
        self.combo_modelo.set("medium")
        self._fila(tarjeta, 3, "Modelo", self.combo_modelo,
                   "tiny/base: rápido y menos preciso · medium: equilibrio · "
                   "large-v3: el más preciso, pero el más lento.")

        self.combo_idioma = ttk.Combobox(tarjeta, values=list(IDIOMAS.keys()),
                                         state="readonly", width=24)
        self.combo_idioma.set("Español")
        self._fila(tarjeta, 4, "Idioma", self.combo_idioma,
                   "Idioma del audio. Whisper elige uno por archivo; "
                   "“Detectar” lo decide solo al inicio.")

        self.spin_palabras = ttk.Spinbox(tarjeta, from_=1, to=5, width=6,
                                         state="readonly", justify="center")
        self.spin_palabras.set(3)
        self._fila(tarjeta, 5, "Palabras por subtítulo", self.spin_palabras,
                   "Máximo de palabras por bloque del SRT (de 1 a 5).")

        frame_relleno = ttk.Frame(tarjeta, style="Card.TFrame")
        self.relleno = tk.DoubleVar(value=0.25)
        self.escala_relleno = ttk.Scale(frame_relleno, from_=0.0, to=1.0,
                                        variable=self.relleno,
                                        command=self._actualizar_relleno, length=200)
        self.escala_relleno.pack(side="left")
        self.lbl_relleno = ttk.Label(frame_relleno, text="0.25 s", style="Card.TLabel", width=7)
        self.lbl_relleno.pack(side="left", padx=8)
        self._fila(tarjeta, 6, "Relleno", frame_relleno,
                   "Segundos extra antes y después de cada frase al cortar. "
                   "Solo aplica en modo “cortar”.")

        self.vocab_var = tk.StringVar()
        self.entry_vocab = ttk.Entry(tarjeta, textvariable=self.vocab_var, width=30, font=FUENTE)
        self._fila(tarjeta, 7, "Vocabulario", self.entry_vocab,
                   "Términos técnicos o en inglés separados por coma (Docker, Kafka). "
                   "Mejoran cómo se escriben.")

        frame_botones = ttk.Frame(tarjeta, style="Card.TFrame")
        self.btn_procesar = ttk.Button(frame_botones, text="▶  Procesar",
                                       style="Accent.TButton", command=self._procesar)
        self.btn_procesar.pack(side="left")
        self.btn_abrir = ttk.Button(frame_botones, text="Abrir carpeta",
                                    style="Sec.TButton", command=self._abrir_carpeta)
        self.btn_abrir.pack(side="left", padx=(12, 0))
        self._fila(tarjeta, 8, None, frame_botones, pady=(16, 0))

        self.barra = ttk.Progressbar(cont, maximum=100, mode="determinate")
        self.barra.pack(fill="x", pady=(18, 4))
        self.lbl_progreso = ttk.Label(cont, text="Esperando archivo", style="Sub.TLabel")
        self.lbl_progreso.pack(anchor="w")

        marco = tk.Frame(cont, bg=C["consola"])
        marco.pack(fill="both", expand=True, pady=(14, 0))

        self.consola = tk.Text(
            marco, bg=C["consola"], fg=C["texto"], font=FUENTE_MONO,
            relief="flat", bd=0, padx=14, pady=12, wrap="word",
            state="disabled", highlightthickness=0, insertbackground=C["texto"],
        )
        sb = ttk.Scrollbar(marco, command=self.consola.yview)
        self.consola.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.consola.pack(side="left", fill="both", expand=True)

        self.consola.tag_configure("hora", foreground=C["suave"])
        self.consola.tag_configure("info", foreground=C["texto"])
        self.consola.tag_configure("paso", foreground=C["paso"], font=FUENTE_MONO_NEG)
        self.consola.tag_configure("ok", foreground=C["ok"])
        self.consola.tag_configure("error", foreground=C["error"])

    def _log(self, texto, tag="info"):
        hora = datetime.now().strftime("%H:%M:%S")
        self.consola.configure(state="normal")
        self.consola.insert("end", f"[{hora}] ", "hora")
        self.consola.insert("end", texto + "\n", tag)
        self.consola.see("end")
        self.consola.configure(state="disabled")

    def _actualizar_relleno(self, valor):
        self.lbl_relleno.configure(text=f"{float(valor):.2f} s")

    def _actualizar_controles(self):
        ocupado = self.procesando
        cortar = self.modo.get() == "cortar"
        estado_lista = "disabled" if ocupado else "readonly"

        self.radio_solo.configure(state="disabled" if ocupado else "normal")
        self.radio_cortar.configure(state="disabled" if ocupado else "normal")
        self.combo_modelo.configure(state=estado_lista)
        self.combo_idioma.configure(state=estado_lista)
        self.spin_palabras.configure(state=estado_lista)
        self.entry_vocab.configure(state="disabled" if ocupado else "normal")
        self.btn_elegir.state(["disabled"] if ocupado else ["!disabled"])
        self.escala_relleno.state(["disabled"] if (ocupado or not cortar) else ["!disabled"])

        listo = (not ocupado) and self.video_path is not None
        self.btn_procesar.state(["!disabled"] if listo else ["disabled"])

    def _palabras_por_subtitulo(self):
        try:
            n = int(self.spin_palabras.get())
        except ValueError:
            n = 3
        return max(1, min(5, n))

    def _elegir(self):
        ruta = filedialog.askopenfilename(
            title="Selecciona el video o audio",
            filetypes=[("Archivos multimedia",
                        "*.mp4 *.mov *.avi *.mkv *.mp3 *.wav *.m4a *.flac *.ogg"),
                       ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        self.video_path = ruta
        self.lbl_archivo.configure(text=os.path.basename(ruta))
        self.barra.configure(value=0)
        self.lbl_progreso.configure(text="Listo para procesar")
        self._log(f"Archivo seleccionado: {ruta}", "info")
        self._actualizar_controles()

    def _procesar(self):
        if not self.video_path or self.procesando:
            return
        modelo = self.combo_modelo.get()
        nombre_idioma = self.combo_idioma.get()
        idioma = IDIOMAS[nombre_idioma]
        vocabulario = self.vocab_var.get().strip() or None
        max_palabras = self._palabras_por_subtitulo()
        cortar = self.modo.get() == "cortar"
        padding = float(self.relleno.get())
        nombre_modo = "cortar video y subtítulos" if cortar else "solo subtítulos"

        self.btn_abrir.state(["disabled"])
        self.procesando = True
        self._actualizar_controles()
        self.barra.configure(value=0)
        self._log(f"Iniciando: {nombre_modo}, modelo '{modelo}', idioma {nombre_idioma}, "
                  f"{max_palabras} palabras por subtítulo"
                  + (f", relleno {padding:.2f} s" if cortar else ""), "paso")
        if vocabulario:
            self._log(f"Vocabulario: {vocabulario}", "info")

        threading.Thread(
            target=self._hilo_proceso,
            args=(self.video_path, modelo, idioma, vocabulario, max_palabras, padding, cortar),
            daemon=True,
        ).start()

    def _hilo_proceso(self, video, modelo, idioma, vocabulario, max_palabras, padding, cortar):
        def emit(kind, text=None, value=None):
            self.cola.put((kind, text, value))

        try:
            procesar(video, modelo, idioma, vocabulario, max_palabras, padding, cortar, emit)
        except Exception:
            self.cola.put(("fallo", traceback.format_exc(), None))

    def _abrir_carpeta(self):
        if not self.ultimo_dir:
            return
        if sys.platform == "win32":
            os.startfile(self.ultimo_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self.ultimo_dir])
        else:
            subprocess.Popen(["xdg-open", self.ultimo_dir])

    def _revisar_cola(self):
        try:
            while True:
                self._manejar(self.cola.get_nowait())
        except queue.Empty:
            pass
        self.root.after(80, self._revisar_cola)

    def _manejar(self, msg):
        kind, text, value = msg

        if kind in ("info", "paso", "ok"):
            self._log(text, kind)

        elif kind == "progreso":
            self.lbl_progreso.configure(text=text)
            if value is not None:
                self.barra.configure(value=value * 100)

        elif kind == "fin":
            media, srt, carpeta = value
            self.ultimo_dir = carpeta
            self._log(text, "ok")
            if media:
                self._log(f"Video sin silencios guardado en: {media}", "ok")
            self._log(f"SRT guardado en: {srt}", "ok")
            self.barra.configure(value=100)
            self.lbl_progreso.configure(text="Completado")
            self.btn_abrir.state(["!disabled"])
            self.procesando = False
            self._actualizar_controles()

        elif kind == "fallo":
            self.lbl_progreso.configure(text="Ocurrió un error")
            for linea in text.rstrip().splitlines():
                self._log(linea, "error")
            ultima = text.strip().splitlines()[-1]
            messagebox.showerror("Error", ultima)
            self.procesando = False
            self._actualizar_controles()


def main():
    configurar_cuda()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
