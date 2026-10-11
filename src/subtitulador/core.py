"""Transcripción, cálculo de cortes, subtítulos y render. No depende de la interfaz gráfica."""

import os
import subprocess
import sys
from typing import Callable

PAUSA_MAX = 0.5  
EXT_AUDIO = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
MODELOS = ["tiny", "base", "small", "medium", "large-v3"]
IDIOMAS = {
    "Español": "es",
    "Inglés": "en",
    "Detectar automáticamente": None,
}
FLAGS_PROC = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

Emit = Callable[..., None]


def configurar_cuda():
    """Registra las DLL de CUDA instaladas con pip (nvidia-cublas / nvidia-cudnn).

    Debe llamarse antes de crear el modelo. Funciona en modo script y empaquetado con PyInstaller.
    """
    if os.name != "nt":
        return
    if getattr(sys, "frozen", False):
        bases = [sys._MEIPASS]
    else:
        bases = [p for p in sys.path if "site-packages" in p][:1]
    for base in bases:
        for ruta in (os.path.join(base, "nvidia", "cublas", "bin"),
                     os.path.join(base, "nvidia", "cudnn", "bin")):
            if os.path.isdir(ruta):
                os.add_dll_directory(ruta)


def format_time(seconds):
    total_ms = int(round(seconds * 1000))
    h, resto = divmod(total_ms, 3_600_000)
    m, resto = divmod(resto, 60_000)
    s, ms = divmod(resto, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def es_audio(path):
    return os.path.splitext(path)[1].lower() in EXT_AUDIO


def duracion_media(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
        stdin=subprocess.DEVNULL, creationflags=FLAGS_PROC,
    )
    return float(r.stdout.strip())


def transcribir(video_path, modelo, idioma, vocabulario, emit: Emit, duracion):
    """Transcribe con GPU; si falla, reintenta en CPU."""
    from faster_whisper import BatchedInferencePipeline, WhisperModel

    intentos = [("cuda", "float16", 16), ("cpu", "int8", 4)]
    for i, (dispositivo, tipo, lote) in enumerate(intentos):
        try:
            emit("paso", f"Cargando el modelo ({dispositivo})...")
            model = WhisperModel(modelo, device=dispositivo, compute_type=tipo)
            pipeline = BatchedInferencePipeline(model=model)

            emit("paso", f"Analizando silencios y sacando texto de: {video_path}")
            gen, info = pipeline.transcribe(
                video_path,
                language=idioma,
                initial_prompt=vocabulario,
                word_timestamps=True,
                vad_filter=True,
                beam_size=1,
                batch_size=lote,
            )
            if idioma is None:
                emit("info", f"Idioma detectado: {info.language} "
                             f"({info.language_probability:.0%})")

            segments = []
            for seg in gen:
                segments.append(seg)
                avance = min(seg.end / duracion, 1.0)
                emit("progreso",
                     f"Transcribiendo... {seg.end:.0f}s de {duracion:.0f}s",
                     0.6 * avance)
            return segments
        except Exception as e:
            if i == len(intentos) - 1:
                raise
            emit("info", f"GPU no disponible ({e}). Usando CPU...")


def agrupar_subtitulos(segments, max_palabras):
    """Agrupa palabras: máximo N por subtítulo, y parte por pausa o puntuación."""
    palabras = [w for seg in segments for w in (seg.words or []) if w.word.strip()]
    bloques, actual = [], []
    for w in palabras:
        texto = w.word.strip()
        if actual:
            gap = w.start - actual[-1].end
            if gap > PAUSA_MAX or len(actual) >= max_palabras:
                bloques.append(actual)
                actual = []
        actual.append(w)
        if texto[-1] in ".?!":
            bloques.append(actual)
            actual = []
    if actual:
        bloques.append(actual)
    return bloques


def mapear(t, intervalos, offsets):
    """Convierte un tiempo del original al tiempo del archivo cortado."""
    for (s, e), off in zip(intervalos, offsets):
        if t < s:
            return off
        if t <= e:
            return off + (t - s)
    s, e = intervalos[-1]
    return offsets[-1] + (e - s)


def renderizar(video_path, intervalos, salida, solo_audio, total, emit: Emit, vcodec):
    n = len(intervalos)
    partes = []

    if solo_audio:
        partes.append(f"[0:a]asplit={n}" + "".join(f"[sa{i}]" for i in range(n)) + ";")
    else:
        partes.append(f"[0:v]split={n}" + "".join(f"[sv{i}]" for i in range(n)) + ";")
        partes.append(f"[0:a]asplit={n}" + "".join(f"[sa{i}]" for i in range(n)) + ";")

    for i, (s, e) in enumerate(intervalos):
        partes.append(f"[sa{i}]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")
        if not solo_audio:
            partes.append(f"[sv{i}]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];")

    if solo_audio:
        entradas = "".join(f"[a{i}]" for i in range(n))
        filtro = "".join(partes) + f"{entradas}concat=n={n}:v=0:a=1[outa]"
        maps = ["-map", "[outa]"]
        codecs = ["-c:a", "libmp3lame", "-q:a", "2"]
    else:
        entradas = "".join(f"[v{i}][a{i}]" for i in range(n))
        filtro = "".join(partes) + f"{entradas}concat=n={n}:v=1:a=1[outv][outa]"
        maps = ["-map", "[outv]", "-map", "[outa]"]
        codecs = ["-c:v", vcodec, "-c:a", "aac"]

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-progress", "pipe:1", "-nostats",
           "-i", video_path, "-filter_complex", filtro,
           *maps, *codecs, salida]

    proc = subprocess.Popen(
        cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", creationflags=FLAGS_PROC,
    )
    for linea in proc.stdout:
        linea = linea.strip()
        if linea.startswith(("out_time_us=", "out_time_ms=")):
            valor = linea.split("=", 1)[1]
            try:
                t = int(valor) / 1_000_000  
            except ValueError:
                continue
            avance = min(t / total, 1.0)
            emit("progreso",
                 f"Renderizando... {t:.0f}s de {total:.0f}s",
                 0.7 + 0.3 * avance)

    rc = proc.wait()
    err = proc.stderr.read()
    if rc != 0:
        raise RuntimeError(f"ffmpeg falló (código {rc}):\n{err.strip()}")


def procesar(video_path, modelo, idioma, vocabulario, max_palabras, padding, cortar, emit: Emit):
    dir_path = os.path.dirname(video_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    solo_audio = es_audio(video_path)
    ext_salida = ".mp3" if solo_audio else ".mp4"
    output_media = os.path.join(dir_path, f"{base_name}_cortado{ext_salida}") if cortar else None
    output_srt = os.path.join(dir_path, f"{base_name}_cortado_subtitulos.srt")

    duracion = duracion_media(video_path)
    segments = transcribir(video_path, modelo, idioma, vocabulario, emit, duracion)
    emit("info", f"Segmentos detectados: {len(segments)}")

    if cortar:
        emit("paso", "Calculando cortes exactos y re-sincronizando subtítulos...")
        intervalos = []
        last_end_cut = 0.0
        for seg in segments:
            s = max(last_end_cut, seg.start - padding)
            e = min(duracion, seg.end + padding)
            if s >= e:
                continue
            intervalos.append((s, e))
            last_end_cut = e

        if not intervalos:
            raise RuntimeError("No se detectó voz en el archivo.")

        offsets, acumulado = [], 0.0
        for s, e in intervalos:
            offsets.append(acumulado)
            acumulado += e - s
        total = acumulado
    else:
        intervalos = [(0.0, duracion)]
        offsets = [0.0]
        total = duracion

    srt_bloques = []
    for i, bloque in enumerate(agrupar_subtitulos(segments, max_palabras), 1):
        ini = mapear(bloque[0].start, intervalos, offsets)
        fin = mapear(bloque[-1].end, intervalos, offsets)
        if fin <= ini:
            fin = ini + 0.05
        texto = " ".join(w.word.strip() for w in bloque)
        srt_bloques.append(f"{i}\n{format_time(ini)} --> {format_time(fin)}\n{texto}\n")

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_bloques))
    emit("ok", f"¡Subtítulos guardados! ({len(srt_bloques)} bloques)")

    if cortar:
        emit("progreso", "Preparando render...", 0.7)
        emit("paso", "Uniendo las partes sin silencios (El render puede tomar unos minutos...)")
        try:
            renderizar(video_path, intervalos, output_media, solo_audio, total, emit, "h264_nvenc")
        except RuntimeError:
            if solo_audio:
                raise
            emit("info", "NVENC no disponible, usando libx264 (más lento)...")
            renderizar(video_path, intervalos, output_media, solo_audio, total, emit, "libx264")

    emit("fin", "¡Todo listo, ewe!", (output_media, output_srt, dir_path))
    return output_media, output_srt, dir_path
