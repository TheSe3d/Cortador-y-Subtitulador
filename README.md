# Subtitulador Automático

Corta los silencios de un video o audio y genera subtítulos `.srt` sincronizados con el corte, usando [Whisper](https://github.com/openai/whisper) (vía [faster-whisper](https://github.com/SYSTRAN/faster-whisper)).

![Captura de la ventana](assets/captura.png)

![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green)
![CI](https://github.com/TheSe3d/subtitulador/actions/workflows/ci.yml/badge.svg)

## Características

- Quita los silencios y une solo las partes con voz.
- Genera subtítulos `.srt` con los tiempos ya recalculados para el video cortado.
- Modo **solo subtítulos** si no quieres tocar el video.
- Transcripción con GPU NVIDIA (CUDA) y respaldo automático a CPU.
- Español, inglés o detección automática de idioma.
- Campo de **vocabulario** para mejorar la escritura de términos técnicos o en inglés.
- Número de palabras por subtítulo ajustable (de 1 a 5).
- Formatos de video y audio: `mp4`, `mov`, `avi`, `mkv`, `mp3`, `wav`, `m4a`, `flac`, `ogg`.

## Requisitos

- **Python 3.10 o superior**, con Tcl/Tk (viene incluido en la instalación oficial de Windows).
- **ffmpeg y ffprobe** en el PATH. No se instalan con pip:
  ```
  winget install Gyan.FFmpeg
  ```
- **GPU NVIDIA y drivers actualizados** (opcional, pero recomendado). Sin GPU el programa funciona en CPU, pero es más lento.

## Instalación

```bash
pip install "subtitulador[cuda] @ git+https://github.com/TheSe3d/subtitulador"
```

Si no tienes GPU NVIDIA, instala sin el extra `[cuda]`:

```bash
pip install "git+https://github.com/TheSe3d/subtitulador"
```

## Uso

Ejecuta en la terminal:

```bash
subtitulador
```

O también:

```bash
python -m subtitulador
```

Pasos:

1. Elige el archivo.
2. Elige el modo (ver tabla abajo).
3. Ajusta el modelo, idioma, palabras por subtítulo y, si aplica, el relleno y el vocabulario.
4. Pulsa **Procesar**.

| Opción | Qué hace |
|---|---|
| Solo subtítulos | Genera el `.srt` con los tiempos originales. El video no se modifica. |
| Cortar video y subtítulos | Quita los silencios, genera el video nuevo y el `.srt` sincronizado con él. |

### Modelos

| Modelo | Velocidad | Precisión |
|---|---|---|
| `tiny`, `base` | Rápido | Menor |
| `medium` | Equilibrio | Buena (valor por defecto) |
| `large-v3` | Lento | La mejor |

La primera vez que usas un modelo se descarga desde internet.

## Cómo funciona

1. **Transcripción:** Whisper detecta la voz y devuelve el texto con el tiempo de cada palabra.
2. **Cortes:** cada frase se expande con el *relleno* para no cortar palabras, y se descartan los tramos que se solapan.
3. **Subtítulos:** las palabras se agrupan por pausas, puntuación y número máximo, y sus tiempos se convierten a la línea de tiempo del video cortado.
4. **Render:** un solo comando de ffmpeg corta, une y codifica con NVENC (o libx264 si no hay GPU compatible).

## Solución de problemas

- **`ffmpeg` no se reconoce como comando:** instálalo y revisa que la carpeta `bin` esté en el PATH. Abre una terminal nueva después de instalarlo.
- **`CUDA` no disponible o error de DLL:** instala el extra `[cuda]` o revisa que los drivers de NVIDIA estén actualizados. El programa cambia a CPU automáticamente.
- **Falta memoria:** usa un modelo más chico (`small` o `base`).
- **El inglés sale con ortografía en español:** agrega las palabras en el campo de vocabulario o usa `large-v3`.

## Roadmap

- [ ] Ejecutable para Windows en la sección de Releases.
- [ ] Soporte para Linux y macOS.
- [ ] Editar el `.srt` dentro de la aplicación.

## Contribuir

Las contribuciones son bienvenidas. Lee [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir un pull request.

## Licencia

[MIT](LICENSE) © Ángel Germán George Barragán

## Agradecimientos

- [OpenAI Whisper](https://github.com/openai/whisper)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (SYSTRAN)
- [ffmpeg](https://ffmpeg.org/)
