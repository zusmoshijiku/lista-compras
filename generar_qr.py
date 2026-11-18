"""Genera el código QR de la colecta en PNG y SVG.

Uso:
    python generar_qr.py "https://usuario.github.io/lista-compras/"
    python generar_qr.py "https://usuario.github.io/lista-compras/?s=lider-centro" -o qr/lider-centro

Crea <salida>.png y <salida>.svg (por defecto qr-colecta.png / qr-colecta.svg).
Corrección de errores nivel H (resiste ~30 % de daño), zona de silencio de 4
módulos o más, negro sobre blanco.

Requiere el paquete "segno" (Python puro, sin otras dependencias):
    pip install segno
"""
import argparse
import pathlib
import sys


def main():
    ap = argparse.ArgumentParser(description="Genera el QR de la colecta (PNG y SVG).")
    ap.add_argument("url", help="URL que abrirá el QR (la de GitHub Pages)")
    ap.add_argument("-o", "--salida", default="qr-colecta",
                    help="ruta base de salida, sin extensión (por defecto: qr-colecta)")
    ap.add_argument("--escala", type=int, default=20,
                    help="píxeles por módulo en el PNG (por defecto: 20)")
    ap.add_argument("--borde", type=int, default=4,
                    help="zona de silencio en módulos (mínimo y por defecto: 4)")
    args = ap.parse_args()

    url = args.url.strip()
    if not url.lower().startswith(("https://", "http://")):
        ap.error("la URL debe empezar con https:// (o http://)")
    if args.borde < 4:
        ap.error("la zona de silencio debe ser de al menos 4 módulos")
    if args.escala < 1:
        ap.error("la escala debe ser 1 o más")

    try:
        import segno
    except ImportError:
        print("Falta el paquete 'segno'. Instálalo con:\n    pip install segno", file=sys.stderr)
        sys.exit(1)

    # make_qr fuerza un QR normal (no Micro QR); boost_error=False mantiene el nivel H exacto.
    qr = segno.make_qr(url, error="h", boost_error=False)

    base = pathlib.Path(args.salida)
    base.parent.mkdir(parents=True, exist_ok=True)
    png = base.with_suffix(".png")
    svg = base.with_suffix(".svg")
    colores = dict(dark="#000000", light="#ffffff")
    qr.save(str(png), scale=args.escala, border=args.borde, **colores)
    qr.save(str(svg), scale=10, border=args.borde, xmldecl=False, svgclass=None, lineclass=None,
            title="Lista de la colecta", **colores)

    modulos = qr.symbol_size(scale=1, border=0)[0]
    total = qr.symbol_size(scale=args.escala, border=args.borde)[0]
    print(f"URL:        {url}")
    print(f"QR:         versión {qr.version}, nivel {qr.error.upper()}, {modulos}×{modulos} módulos + borde de {args.borde}")
    print(f"PNG:        {png} ({total}×{total} px)")
    print(f"SVG:        {svg} (vectorial, ideal para imprimir)")
    print("Imprime el QR de al menos 3 × 3 cm y pruébalo con dos celulares antes de imprimir en cantidad.")


if __name__ == "__main__":
    main()
