"""Genera el código QR de la colecta en PNG y SVG, con el logo al centro.

Uso:
    python generar_qr.py "https://usuario.github.io/lista-compras/"
    python generar_qr.py "https://usuario.github.io/lista-compras/?s=lider-centro" -o qr/lider-centro
    python generar_qr.py "https://..." --logo otro-logo.png --logo-area 12
    python generar_qr.py "https://..." --sin-logo

Crea <salida>.png y <salida>.svg (por defecto qr-colecta.png / qr-colecta.svg).
Corrección de errores nivel H (resiste ~30 % de daño), zona de silencio de 4
módulos o más, negro sobre blanco.

El logo (por defecto logo-qr.png) se recorta a su contenido y va sobre un recuadro
blanco con la misma forma que el logo. --logo-area fija qué porcentaje de la
superficie del QR tapa ese recuadro: 12 % por defecto, 15 % como máximo. El nivel H
lo compensa, pero prueba siempre el QR impreso con varios celulares.

Requiere:
    pip install segno      (genera el QR; Python puro)
    pip install pillow     (solo para poner el logo)
"""
import argparse
import base64
import io
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
LOGO_POR_DEFECTO = AQUI / "logo-qr.png"
AREA_POR_DEFECTO = 12.0  # % de la superficie del QR que tapa el recuadro del logo
AREA_MAX = 15.0
MARGEN = 1               # módulos de blanco entre el logo y el resto del QR
FINDER = 9               # los patrones de las esquinas ocupan 8 módulos (+1 de holgura)



def caja_logo(modulos, area_pct, proporcion):
    """(x, y, ancho, alto) del recuadro en módulos, centrado.

    Los QR tienen lado impar (21, 25, 29…); con ancho y alto impares el recuadro cae justo
    sobre la grilla. Entre los recuadros que no pasan del área pedida ni tocan los patrones
    de las esquinas, se elige el que deja el logo (proporcion = ancho / alto) más grande.
    """
    limite = area_pct / 100 * modulos * modulos
    tope = modulos - 2 * FINDER
    mejor, mejor_alto_logo = (3, 3), -1.0
    for alto in range(3, tope + 1, 2):
        for ancho in range(3, tope + 1, 2):
            if ancho * alto > limite:
                break
            alto_logo = min((ancho - 2 * MARGEN) / proporcion, alto - 2 * MARGEN)
            if alto_logo > mejor_alto_logo + 1e-9:
                mejor, mejor_alto_logo = (ancho, alto), alto_logo
    ancho, alto = mejor
    return (modulos - ancho) // 2, (modulos - alto) // 2, ancho, alto


def cargar_logo(ruta):
    """Abre el logo y recorta el borde transparente (o blanco, si no tiene transparencia)."""
    from PIL import Image, ImageChops

    logo = Image.open(ruta).convert("RGBA")
    caja = logo.getchannel("A").getbbox()
    if caja == (0, 0, logo.width, logo.height):
        blanco = Image.new("RGB", logo.size, (255, 255, 255))
        caja = ImageChops.difference(logo.convert("RGB"), blanco).getbbox() or caja
    return logo.crop(caja) if caja else logo


def logo_en_png(ruta_png, logo, caja, escala, borde):
    from PIL import Image, ImageDraw

    qr = Image.open(ruta_png).convert("RGB")
    x, y, ancho, alto = caja
    x0, y0 = (borde + x) * escala, (borde + y) * escala
    ImageDraw.Draw(qr).rounded_rectangle(
        [x0, y0, x0 + ancho * escala - 1, y0 + alto * escala - 1], radius=escala, fill="#ffffff")
    interior = ((ancho - 2 * MARGEN) * escala, (alto - 2 * MARGEN) * escala)
    im = logo.copy()
    im.thumbnail(interior, Image.LANCZOS)
    if im.width < interior[0] and im.height < interior[1]:  # logos chicos: agrandar hasta llenar
        k = min(interior[0] / im.width, interior[1] / im.height)
        im = logo.resize((round(logo.width * k), round(logo.height * k)), Image.LANCZOS)
    pos = (x0 + (ancho * escala - im.width) // 2, y0 + (alto * escala - im.height) // 2)
    qr.paste(im, pos, im)
    qr.save(ruta_png, optimize=True)


def logo_en_svg(ruta_svg, logo, caja, escala, borde):
    x, y, ancho, alto = caja
    x0, y0 = (borde + x) * escala, (borde + y) * escala
    iw, ih = (ancho - 2 * MARGEN) * escala, (alto - 2 * MARGEN) * escala
    k = min(iw / logo.width, ih / logo.height)
    w, h = logo.width * k, logo.height * k
    buf = io.BytesIO()
    logo.save(buf, format="PNG", optimize=True)
    href = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    svg = ruta_svg.read_text(encoding="utf-8")
    if "xmlns:xlink" not in svg:
        svg = svg.replace("<svg ", '<svg xmlns:xlink="http://www.w3.org/1999/xlink" ', 1)
    extra = (
        f'<rect x="{x0}" y="{y0}" width="{ancho * escala}" height="{alto * escala}" rx="{escala}" fill="#ffffff"/>'
        f'<image x="{x0 + (ancho * escala - w) / 2:g}" y="{y0 + (alto * escala - h) / 2:g}" '
        f'width="{w:g}" height="{h:g}" href="{href}" xlink:href="{href}"/>'
    )
    i = svg.rindex("</svg>")
    ruta_svg.write_text(svg[:i] + extra + svg[i:], encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Genera el QR de la colecta (PNG y SVG).")
    ap.add_argument("url", help="URL que abrirá el QR (la de GitHub Pages)")
    ap.add_argument("-o", "--salida", default="qr-colecta",
                    help="ruta base de salida, sin extensión (por defecto: qr-colecta)")
    ap.add_argument("--escala", type=int, default=20,
                    help="píxeles por módulo en el PNG (por defecto: 20)")
    ap.add_argument("--borde", type=int, default=4,
                    help="zona de silencio en módulos (mínimo y por defecto: 4)")
    ap.add_argument("--logo", type=pathlib.Path, default=LOGO_POR_DEFECTO,
                    help="imagen PNG o JPG para el centro (por defecto: logo-qr.png)")
    ap.add_argument("--logo-area", type=float, default=AREA_POR_DEFECTO,
                    help=f"%% de la superficie del QR que tapa el logo (3 a {AREA_MAX:g}; por defecto {AREA_POR_DEFECTO:g})")
    ap.add_argument("--sin-logo", action="store_true", help="genera el QR sin imagen al centro")
    args = ap.parse_args()

    url = args.url.strip()
    if not url.lower().startswith(("https://", "http://")):
        ap.error("la URL debe empezar con https:// (o http://)")
    if args.borde < 4:
        ap.error("la zona de silencio debe ser de al menos 4 módulos")
    if args.escala < 4:
        ap.error("la escala debe ser 4 o más")
    if not 3 <= args.logo_area <= AREA_MAX:
        ap.error(f"--logo-area debe estar entre 3 y {AREA_MAX:g}")

    con_logo = not args.sin_logo
    if con_logo:
        if not args.logo.is_file():
            ap.error(f"no encuentro la imagen {args.logo} (usa --logo RUTA o --sin-logo)")
        if args.logo.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            ap.error("el logo debe ser PNG o JPG")

    faltan = []
    try:
        import segno
    except ImportError:
        faltan.append("segno")
    if con_logo:
        try:
            import PIL  # noqa: F401
        except ImportError:
            faltan.append("pillow")
    if faltan:
        print("Faltan paquetes. Instálalos con:\n    pip install " + " ".join(faltan), file=sys.stderr)
        sys.exit(1)

    # make_qr fuerza un QR normal (no Micro QR); boost_error=False mantiene el nivel H exacto.
    qr = segno.make_qr(url, error="h", boost_error=False)
    modulos = qr.symbol_size(scale=1, border=0)[0]

    base = pathlib.Path(args.salida)
    base.parent.mkdir(parents=True, exist_ok=True)
    png = base.with_suffix(".png")
    svg = base.with_suffix(".svg")
    escala_svg = 10
    colores = dict(dark="#000000", light="#ffffff")
    qr.save(str(png), scale=args.escala, border=args.borde, **colores)
    qr.save(str(svg), scale=escala_svg, border=args.borde, xmldecl=False, svgclass=None, lineclass=None,
            title="Lista de la colecta", **colores)

    if con_logo:
        logo = cargar_logo(args.logo)
        caja = caja_logo(modulos, args.logo_area, logo.width / logo.height)
        logo_en_png(png, logo, caja, args.escala, args.borde)
        logo_en_svg(svg, logo, caja, escala_svg, args.borde)

    total = qr.symbol_size(scale=args.escala, border=args.borde)[0]
    print(f"URL:        {url}")
    print(f"QR:         versión {qr.version}, nivel {qr.error.upper()}, {modulos}×{modulos} módulos + borde de {args.borde}")
    if con_logo:
        _, _, ancho, alto = caja
        print(f"Logo:       {args.logo.name}, recuadro de {ancho}×{alto} módulos "
              f"({ancho * alto / modulos ** 2:.1%} de la superficie, {ancho / modulos:.0%} del ancho)")
    print(f"PNG:        {png} ({total}×{total} px)")
    print(f"SVG:        {svg} (vectorial, ideal para imprimir)")
    print("Imprime el QR de al menos 3 × 3 cm y pruébalo con dos celulares antes de imprimir en cantidad.")


if __name__ == "__main__":
    main()
