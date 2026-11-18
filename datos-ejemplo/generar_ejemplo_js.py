"""Copia items.csv y config.csv dentro de ejemplo.js.

Sirve para abrir index.html con doble clic (file://): ahí el navegador no deja
leer archivos con fetch, así que la página usa esta copia. Si editas los CSV
de ejemplo, vuelve a correr:  python datos-ejemplo/generar_ejemplo_js.py
"""
import json
import pathlib

carpeta = pathlib.Path(__file__).resolve().parent
datos = {
    "items": (carpeta / "items.csv").read_text(encoding="utf-8"),
    "config": (carpeta / "config.csv").read_text(encoding="utf-8"),
}
js = (
    "/* Generado por generar_ejemplo_js.py a partir de items.csv y config.csv. No editar a mano. */\n"
    "window.DATOS_EJEMPLO = " + json.dumps(datos, ensure_ascii=False, indent=1) + ";\n"
)
(carpeta / "ejemplo.js").write_text(js, encoding="utf-8")
print("Listo:", carpeta / "ejemplo.js")
