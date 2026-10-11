# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

## [1.0.0] - 2026-10-11

### Corregido
- El ejecutable de Windows ahora incluye el modelo de detección de voz, así que ya no falla al procesar.
- El ejecutable ahora usa la GPU NVIDIA cuando está disponible.

## [0.1.0] - 2026-10-11

### Agregado
- Interfaz gráfica con modos "Solo subtítulos" y "Cortar video y subtítulos".
- Transcripción con faster-whisper y respaldo automático de GPU a CPU.
- Selector de idioma: español, inglés o detección automática.
- Campo de vocabulario para términos técnicos o en inglés.
- Número de palabras por subtítulo ajustable.
- Render con ffmpeg (NVENC, con respaldo a libx264).
- Soporte para archivos de audio (salida en MP3).
- Pruebas unitarias para el cálculo de tiempos y subtítulos.
