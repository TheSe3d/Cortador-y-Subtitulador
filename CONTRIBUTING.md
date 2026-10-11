# Cómo contribuir

¡Gracias por tu interés! Antes de empezar:

## Preparar el entorno

```bash
git clone https://github.com/TU_USUARIO/subtitulador
cd subtitulador
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Necesitas `ffmpeg` y `ffprobe` en el PATH para probar el flujo completo. Las pruebas unitarias no lo requieren.

## Antes de enviar un cambio

```bash
ruff check .
pytest
```

Ambos comandos deben pasar. El CI de GitHub los ejecuta en cada pull request.

## Estilo de código

- Formato de Python estándar, líneas de máximo 100 caracteres.
- La lógica va en `core.py` y no debe depender de tkinter. La interfaz va en `gui.py`.
- Las funciones nuevas que no toquen archivos ni la GPU deben tener una prueba en `tests/`.

## Commits

Usa mensajes cortos en imperativo, por ejemplo `Agregar soporte para archivos .m4a`.

## Pull requests

1. Crea una rama desde `main`.
2. Describe qué cambia y por qué.
3. Si cambia la interfaz, incluye una captura.
4. Actualiza `CHANGELOG.md` en la sección `Sin publicar`.

## Reportar errores

Abre un issue con la plantilla de error e incluye la versión de Python, si usas GPU, y el mensaje completo de la consola.
