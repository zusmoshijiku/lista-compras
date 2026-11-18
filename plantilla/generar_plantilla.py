"""Genera las plantillas de la planilla para subir a Google Drive.

    python plantilla/generar_plantilla.py

Crea dos archivos:
  plantilla/plantilla-sheet.xlsx          Items se escribe a mano (filas de datos-ejemplo/items.csv).
  plantilla/plantilla-sheet-maestro.xlsx  Items se calcula solo desde la pestaña Maestro, que trae
                                          el Excel maestro de operaciones con IMPORTRANGE.

Para revisar la plantilla del maestro con datos reales sin subirlos a ningún lado:
    python plantilla/generar_plantilla.py --maestro-xlsx "Maestro.xlsx" --hoja "Meta (con JUNA)" -o prueba.xlsx
(pega los valores de esa hoja en la pestaña Maestro; no subas ese archivo al repositorio).

Requiere openpyxl (pip install openpyxl).
"""
import argparse
import csv
import pathlib

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "datos-ejemplo" / "items.csv"
SALIDA = RAIZ / "plantilla" / "plantilla-sheet.xlsx"
SALIDA_MAESTRO = RAIZ / "plantilla" / "plantilla-sheet-maestro.xlsx"

FILAS = 300           # filas con validación y formato (planilla manual)
FILAS_MAESTRO = 250   # filas del maestro que se leen (Maestro!A1:I250)
ESTADOS = ["Falta mucho", "Falta poco", "Cubierto"]
SUPERMERCADOS = ["lider-centro", "jumbo-sur", "unimarc-plaza"]
UMBRAL_MUCHO = 0.5    # avance menor a 50 % → Falta mucho (como la hoja "Público" del año pasado)
UMBRAL_POCO = 1       # avance menor a 100 % → Falta poco; si no, Cubierto

# (encabezado, ancho)
COLUMNAS = [
    ("orden", 8), ("categoria", 16), ("item", 28), ("detalle", 38), ("estado", 15),
    ("meta", 9), ("recibido", 11), ("supermercado", 18), ("visible", 10),
]
ENCABEZADOS_MAESTRO = ["Insumos Comida", "Unidad", "Relevancia", "Meta a Alcanzar", "Colecta 0",
                       "Extra", "Avance (%)", "Falta 🙏🙏", "Total"]

ENCABEZADO_FONT = Font(bold=True, color="FFFFFF")
ENCABEZADO_FILL = PatternFill("solid", start_color="1D5FA8")
CALCULADO_FILL = PatternFill("solid", start_color="EEF2F7")
NOTA_FONT = Font(italic=True, color="5A5F66")


# ---------------------------------------------------------------- utilidades

def estado_canonico(valor):
    v = " ".join(valor.split()).lower()
    if "cubiert" in v:
        return "Cubierto"
    if "poco" in v:
        return "Falta poco"
    return "Falta mucho"


def numero(valor):
    valor = valor.strip()
    if not valor:
        return None
    try:
        return int(valor)
    except ValueError:
        try:
            return float(valor.replace(",", "."))
        except ValueError:
            return valor


def encabezado(ws, titulos):
    for col, titulo in enumerate(titulos, start=1):
        c = ws.cell(row=1, column=col, value=titulo)
        c.font = ENCABEZADO_FONT
        c.fill = ENCABEZADO_FILL
        c.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22


def anchos(ws, anchos_por_columna):
    for letra, ancho in anchos_por_columna.items():
        ws.column_dimensions[letra].width = ancho


def nota(ws, celda, texto):
    c = ws[celda]
    c.value = texto
    c.font = NOTA_FONT
    c.alignment = Alignment(wrap_text=True, vertical="top")


def lista(formula, error, titulo, aviso=False):
    dv = DataValidation(type="list", formula1=formula, allow_blank=True)
    dv.error, dv.errorTitle, dv.showErrorMessage = error, titulo, True
    if aviso:
        dv.errorStyle = "warning"  # deja escribir otros valores, con advertencia
    return dv


def formato_por_estado(ws, rango, col_estado="E", col_visible="I"):
    """Color de la fila según estado; gris si visible = NO."""
    ws.conditional_formatting.add(rango, FormulaRule(
        formula=[f'UPPER(TRIM(${col_visible}2))="NO"'], font=Font(color="9AA0A6", italic=True),
        fill=PatternFill("solid", start_color="F1F3F4", end_color="F1F3F4"), stopIfTrue=True))
    for texto, color, fuente in (("falta mucho", "FAD2C1", None), ("falta poco", "FFF0B3", None),
                                 ("cubierto", "DCEBDD", Font(color="3F5C43"))):
        ws.conditional_formatting.add(rango, FormulaRule(
            formula=[f'LOWER(TRIM(${col_estado}2))="{texto}"'], font=fuente,
            fill=PatternFill("solid", start_color=color, end_color=color)))


# ---------------------------------------------------------------- pestañas comunes

def hoja_config(wb, nota_actualizado):
    ws = wb.create_sheet("Config")
    encabezado(ws, ["clave", "valor", "para qué sirve (esta columna no se muestra)"])
    filas = [
        ("actualizado", None, nota_actualizado),
        ("titulo", "Colecta solidaria", "Título grande de la página."),
        ("mensaje", "¡Gracias por sumarte! Elige uno o más productos de la lista, cómpralos y entrégalos al salir.",
         "Texto breve bajo el título."),
        ("contacto", "", "Opcional: teléfono o forma de contacto. Se muestra al final."),
    ]
    for r, (clave, valor, texto) in enumerate(filas, start=2):
        ws.cell(row=r, column=1, value=clave).font = Font(bold=True)
        ws.cell(row=r, column=2, value=valor).alignment = Alignment(wrap_text=True, vertical="top")
        nota(ws, f"C{r}", texto)
    ws["B2"].number_format = "yyyy-mm-dd hh:mm"
    anchos(ws, {"A": 14, "B": 55, "C": 60})


def hoja_listas(wb, donde):
    ws = wb.create_sheet("Listas")
    encabezado(ws, ["supermercados", "nota"])
    for r, s in enumerate(SUPERMERCADOS, start=2):
        ws.cell(row=r, column=1, value=s)
    nota(ws, "B2", "Códigos cortos, sin espacios. El QR de cada supermercado termina en ?s=<código>. "
                   f"Agrega o cambia los códigos aquí y aparecen en la lista desplegable de {donde}.")
    anchos(ws, {"A": 20, "B": 70})


def hoja_instrucciones(wb, lineas):
    ws = wb.create_sheet("Instrucciones")
    ws["A1"] = "Cómo usar esta planilla"
    ws["A1"].font = Font(bold=True, size=14)
    for r, texto in enumerate(lineas, start=3):
        c = ws.cell(row=r, column=1, value=f"{r - 2}. {texto}")
        c.alignment = Alignment(wrap_text=True, vertical="top")
    anchos(ws, {"A": 110})


# ---------------------------------------------------------------- planilla manual

def hoja_items_manual(wb):
    ws = wb.active
    ws.title = "Items"
    encabezado(ws, [c for c, _ in COLUMNAS])
    anchos(ws, {chr(64 + i): ancho for i, (_, ancho) in enumerate(COLUMNAS, start=1)})

    with EJEMPLO.open(encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    for r, fila in enumerate(filas, start=2):
        valores = [
            numero(fila["orden"]), fila["categoria"].strip(), fila["item"].strip(),
            fila["detalle"].strip() or None, estado_canonico(fila["estado"]),
            numero(fila["meta"]), numero(fila["recibido"]),
            fila["supermercado"].strip() or None, fila["visible"].strip().upper() or "SI",
        ]
        for c, v in enumerate(valores, start=1):
            ws.cell(row=r, column=c, value=v).alignment = Alignment(vertical="top", wrap_text=(c == 4))

    ultima = FILAS + 1
    ws.auto_filter.ref = f"A1:I{ultima}"

    dv_estado = lista('"' + ",".join(ESTADOS) + '"', "Elige: Falta mucho, Falta poco o Cubierto.", "Estado no válido")
    dv_estado.add(f"E2:E{ultima}")
    dv_visible = lista('"SI,NO"', "Escribe SI o NO.", "Valor no válido")
    dv_visible.add(f"I2:I{ultima}")
    dv_super = lista("Listas!$A$2:$A$50", "Ese supermercado no está en la pestaña Listas. Vacío = todos los supermercados.",
                     "Supermercado", aviso=True)
    dv_super.add(f"H2:H{ultima}")
    dv_num = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
    dv_num.errorStyle, dv_num.error, dv_num.errorTitle, dv_num.showErrorMessage = (
        "warning", "Debería ser un número (sin unidades).", "Número", True)
    dv_num.add(f"A2:A{ultima}")
    dv_num.add(f"F2:G{ultima}")
    for dv in (dv_estado, dv_visible, dv_super, dv_num):
        ws.add_data_validation(dv)

    formato_por_estado(ws, f"A2:I{ultima}")


def plantilla_manual():
    wb = Workbook()
    hoja_items_manual(wb)
    hoja_config(wb, "Fecha y hora de la última edición. La llena el Apps Script (o escríbela a mano, ej. 14:30). "
                    "Debe quedar en B2.")
    hoja_listas(wb, "Items")
    hoja_instrucciones(wb, [
        "Edita la pestaña Items durante el día: cambia «estado», suma «recibido» o pon «visible» en NO para ocultar un producto.",
        "No cambies los nombres de las pestañas ni la fila 1 (encabezados): la página los usa para leer la lista.",
        "«supermercado» vacío = el producto se muestra en todos lados. Con un código (ej. lider-centro) solo aparece "
        "en el QR de ese supermercado.",
        "«meta» y «recibido» son números sin unidades; si están los dos, la página muestra una barra de avance.",
        "Los cambios pueden tardar unos minutos en verse en la página (Google actualiza la versión publicada cada pocos minutos).",
    ])
    return wb


# ---------------------------------------------------------------- planilla conectada al maestro

def formulas_item(r):
    """Fórmulas de la fila r de Items, que lee la fila m = r - 1 de la pestaña Maestro.

    Maestro (igual que las hojas "Meta" del maestro): A insumo, B unidad, D meta, I total.
    Las filas cuyo D dice "Meta a Alcanzar" son encabezados de sección ("Insumos Comida",
    "Insumos Limpieza"…) y definen la categoría de las filas que siguen. (No sirve mirar B = "Unidad":
    muchos productos tienen "Unidad" como unidad de medida.) Ajustes permite forzar valores por nombre.
    """
    m = r - 1
    aj = f"IFERROR(VLOOKUP($C{r},Ajustes!$A$2:$E$500,{{col}},FALSE)&\"\",\"\")"
    es_encabezado = f'IFERROR(TRIM(Maestro!$D{m}&"")="{ENCABEZADOS_MAESTRO[3]}",FALSE)'
    cat_previa = f"B{r - 1}" if r > 2 else '"Otros"'
    auto_estado = (f'IF(N($F{r})<=0,"Cubierto",IF(N($G{r})/$F{r}<{UMBRAL_MUCHO},"Falta mucho",'
                   f'IF(N($G{r})/$F{r}<{UMBRAL_POCO},"Falta poco","Cubierto")))')
    unidad = f'TRIM(Maestro!$B{m}&"")'
    auto_detalle = f'IFERROR(IF(OR({unidad}="",LOWER({unidad})="unidad"),"","Medida: "&{unidad}),"")'
    return [
        f'=IF($C{r}="","",ROW()-1)',
        f'=IF({es_encabezado},IFERROR(TRIM(SUBSTITUTE(Maestro!$A{m},"Insumos","")),"Otros"),{cat_previa})',
        f'=IF({es_encabezado},"",IFERROR(TRIM(Maestro!$A{m}&""),""))',
        f'=IF($C{r}="","",IF({aj.format(col=5)}<>"",{aj.format(col=5)},{auto_detalle}))',
        f'=IF($C{r}="","",IF({aj.format(col=2)}<>"",{aj.format(col=2)},{auto_estado}))',
        f'=IF($C{r}="","",IFERROR(ROUND(Maestro!$D{m}*1,2),""))',
        f'=IF($C{r}="","",IFERROR(ROUND(Maestro!$I{m}*1,2),""))',
        f'=IF($C{r}="","",{aj.format(col=4)})',
        f'=IF($C{r}="","",IF({aj.format(col=3)}<>"",UPPER({aj.format(col=3)}),IF(N($F{r})>0,"SI","NO")))',
    ]


def hoja_items_maestro(wb):
    ws = wb.active
    ws.title = "Items"
    encabezado(ws, [c for c, _ in COLUMNAS])
    anchos(ws, {chr(64 + i): ancho for i, (_, ancho) in enumerate(COLUMNAS, start=1)})
    ultima = FILAS_MAESTRO + 1
    for r in range(2, ultima + 1):
        for c, f in enumerate(formulas_item(r), start=1):
            celda = ws.cell(row=r, column=c, value=f)
            celda.fill = CALCULADO_FILL
    formato_por_estado(ws, f"A2:I{ultima}")


def hoja_ajustes(wb):
    ws = wb.create_sheet("Ajustes")
    encabezado(ws, ["item", "estado", "visible", "supermercado", "detalle"])
    anchos(ws, {"A": 28, "B": 15, "C": 10, "D": 18, "E": 40, "G": 70})
    nota(ws, "G1", "Opcional. Escribe aquí un producto (tal como aparece en Items) solo si quieres cambiar lo que "
                   "se calcula desde el maestro. Lo que dejes vacío se sigue calculando solo.")
    nota(ws, "G2", "Ejemplos: estado «Cubierto» para dejar de pedirlo aunque falte; visible «NO» para ocultarlo; "
                   "supermercado «lider-centro» para mostrarlo solo en ese QR; detalle «bolsa 1 kg».")
    dvs = [
        (lista(f"Items!$C$2:$C${FILAS_MAESTRO + 1}", "Elige un producto de la lista (como aparece en Items).",
               "Producto", aviso=True), "A"),
        (lista('"' + ",".join(ESTADOS) + '"', "Elige: Falta mucho, Falta poco o Cubierto.", "Estado no válido"), "B"),
        (lista('"SI,NO"', "Escribe SI o NO.", "Valor no válido"), "C"),
        (lista("Listas!$A$2:$A$50", "Ese supermercado no está en la pestaña Listas.", "Supermercado", aviso=True), "D"),
    ]
    for dv, col in dvs:
        dv.add(f"{col}2:{col}500")
        ws.add_data_validation(dv)


def hoja_maestro(wb, filas=None):
    """Pestaña Maestro. Sin filas: un ejemplo con la misma forma que las hojas "Meta" del maestro."""
    ws = wb.create_sheet("Maestro")
    if filas is None:
        filas = [ENCABEZADOS_MAESTRO]
        ejemplo = [
            ("Aceite ", "Litro", 25, 30), ("Arroz ", "Kilo", 29, 10), ("Fideo", "Bolsa", 76, 50),
            ("Atún ", "Lata", 120, 0), ("Leche en polvo", "Kilo", 0, 0), None,
            ["Insumos Limpieza"] + ENCABEZADOS_MAESTRO[1:],
            ("Bolsa basura (M)", "Unidad", 70, 70), ("Cloro ", "Litro", 3, 2), ("Escoba", "Unidad", 3, 0),
        ]
        for fila in ejemplo:
            if fila is None:
                filas.append([])
            elif isinstance(fila, list):
                filas.append(fila)
            else:
                nombre, unidad, meta, total = fila
                filas.append([nombre, unidad, None, meta, total, None, None, None, total])
    for r, fila in enumerate(filas, start=1):
        for c, v in enumerate(fila[:9], start=1):
            ws.cell(row=r, column=c, value=v)
    anchos(ws, {"A": 24, "B": 12, "C": 11, "D": 15, "E": 11, "F": 11, "G": 11, "H": 11, "I": 11, "K": 80})
    nota(ws, "K1", "Esta pestaña trae el maestro. Borra todo (incluida esta nota) y escribe en A1:\n"
                   '=IMPORTRANGE("URL del maestro"; "Meta (con JUNA)!A1:I250")\n'
                   "Luego haz clic en la celda y en «Permitir acceso». Los datos de ejemplo de abajo son solo una muestra.")


def plantilla_maestro(filas_maestro=None):
    wb = Workbook()
    hoja_items_maestro(wb)
    hoja_config(wb, "Fecha y hora de la última actualización. Opcional: ver README (Apps Script en el maestro). "
                    "Debe quedar en B2.")
    hoja_ajustes(wb)
    hoja_maestro(wb, filas_maestro)
    hoja_listas(wb, "Ajustes")
    hoja_instrucciones(wb, [
        "La pestaña Items se calcula sola desde el maestro (pestaña Maestro). No la edites: los cambios se pierden.",
        "Para actualizar la lista, actualiza el maestro de operaciones (meta y cajas recibidas).",
        f"Estado automático: avance (total ÷ meta) bajo {UMBRAL_MUCHO:.0%} = Falta mucho; bajo {UMBRAL_POCO:.0%} = "
        "Falta poco; si no, Cubierto. Productos con meta 0 no se muestran.",
        "¿Quieres cambiar algo a mano? Usa la pestaña Ajustes: busca el producto por nombre y escribe solo lo que "
        "quieras cambiar (estado, visible, supermercado o detalle).",
        "Las secciones del maestro («Insumos Comida», «Insumos Limpieza»…) pasan a ser las categorías de la página.",
        "Los cambios del maestro tardan en llegar: IMPORTRANGE se refresca cada cierto tiempo y Google actualiza la "
        "versión publicada cada pocos minutos.",
    ])
    return wb


def leer_maestro(ruta, hoja):
    ws = load_workbook(ruta, data_only=True)[hoja]
    filas = []
    for fila in ws.iter_rows(min_row=1, max_row=FILAS_MAESTRO, max_col=9, values_only=True):
        filas.append(list(fila))
    return filas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--maestro-xlsx", type=pathlib.Path, help="Excel maestro para pegar sus valores en Maestro (prueba local)")
    ap.add_argument("--hoja", default="Meta (con JUNA)", help='hoja del maestro (por defecto "Meta (con JUNA)")')
    ap.add_argument("-o", "--salida", type=pathlib.Path, help="ruta de salida para la prueba con --maestro-xlsx")
    args = ap.parse_args()

    if args.maestro_xlsx:
        if not args.salida:
            ap.error("con --maestro-xlsx indica también -o/--salida (fuera del repositorio)")
        plantilla_maestro(leer_maestro(args.maestro_xlsx, args.hoja)).save(args.salida)
        print("Listo:", args.salida)
        return

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    plantilla_manual().save(SALIDA)
    print("Listo:", SALIDA)
    plantilla_maestro().save(SALIDA_MAESTRO)
    print("Listo:", SALIDA_MAESTRO)


if __name__ == "__main__":
    main()
