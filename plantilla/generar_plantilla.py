"""Genera plantilla/plantilla-sheet.xlsx para subir a Google Drive.

Uso:  python plantilla/generar_plantilla.py
Requiere openpyxl (pip install openpyxl).

Las filas de ejemplo de la pestaña Items salen de datos-ejemplo/items.csv.
"""
import csv
import pathlib

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "datos-ejemplo" / "items.csv"
SALIDA = RAIZ / "plantilla" / "plantilla-sheet.xlsx"

FILAS = 300  # filas con validación y formato
ESTADOS = ["Falta mucho", "Falta poco", "Cubierto"]
SUPERMERCADOS = ["lider-centro", "jumbo-sur", "unimarc-plaza"]

# (encabezado, ancho)
COLUMNAS = [
    ("orden", 8), ("categoria", 16), ("item", 28), ("detalle", 38), ("estado", 15),
    ("meta", 9), ("recibido", 11), ("supermercado", 18), ("visible", 10),
]

ENCABEZADO_FONT = Font(bold=True, color="FFFFFF")
ENCABEZADO_FILL = PatternFill("solid", start_color="1D5FA8")
NOTA_FONT = Font(italic=True, color="5A5F66")


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


def hoja_items(wb):
    ws = wb.active
    ws.title = "Items"
    encabezado(ws, [c for c, _ in COLUMNAS])
    for i, (_, ancho) in enumerate(COLUMNAS, start=1):
        ws.column_dimensions[chr(64 + i)].width = ancho

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
            celda = ws.cell(row=r, column=c, value=v)
            celda.alignment = Alignment(vertical="top", wrap_text=(c == 4))

    ultima = FILAS + 1
    ws.auto_filter.ref = f"A1:I{ultima}"

    # Listas desplegables
    dv_estado = DataValidation(type="list", formula1='"' + ",".join(ESTADOS) + '"', allow_blank=True)
    dv_estado.error = "Elige: Falta mucho, Falta poco o Cubierto."
    dv_estado.errorTitle = "Estado no válido"
    dv_estado.showErrorMessage = True
    dv_estado.add(f"E2:E{ultima}")

    dv_visible = DataValidation(type="list", formula1='"SI,NO"', allow_blank=True)
    dv_visible.error = "Escribe SI o NO."
    dv_visible.errorTitle = "Valor no válido"
    dv_visible.showErrorMessage = True
    dv_visible.add(f"I2:I{ultima}")

    # Supermercado: lista desde la pestaña Listas; deja escribir otros valores con aviso.
    dv_super = DataValidation(type="list", formula1="Listas!$A$2:$A$50", allow_blank=True)
    dv_super.errorStyle = "warning"
    dv_super.error = "Ese supermercado no está en la pestaña Listas. Vacío = todos los supermercados."
    dv_super.errorTitle = "Supermercado"
    dv_super.showErrorMessage = True
    dv_super.add(f"H2:H{ultima}")

    dv_num = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
    dv_num.errorStyle = "warning"
    dv_num.error = "Debería ser un número (sin unidades)."
    dv_num.errorTitle = "Número"
    dv_num.showErrorMessage = True
    dv_num.add(f"A2:A{ultima}")
    dv_num.add(f"F2:G{ultima}")

    for dv in (dv_estado, dv_visible, dv_super, dv_num):
        ws.add_data_validation(dv)

    # Formato condicional: color de la fila según estado; gris si visible = NO.
    rango = f"A2:I{ultima}"
    ws.conditional_formatting.add(rango, FormulaRule(
        formula=['UPPER(TRIM($I2))="NO"'], font=Font(color="9AA0A6", italic=True),
        fill=PatternFill("solid", start_color="F1F3F4", end_color="F1F3F4"), stopIfTrue=True))
    ws.conditional_formatting.add(rango, FormulaRule(
        formula=['LOWER(TRIM($E2))="falta mucho"'],
        fill=PatternFill("solid", start_color="FAD2C1", end_color="FAD2C1")))
    ws.conditional_formatting.add(rango, FormulaRule(
        formula=['LOWER(TRIM($E2))="falta poco"'],
        fill=PatternFill("solid", start_color="FFF0B3", end_color="FFF0B3")))
    ws.conditional_formatting.add(rango, FormulaRule(
        formula=['LOWER(TRIM($E2))="cubierto"'], font=Font(color="3F5C43"),
        fill=PatternFill("solid", start_color="DCEBDD", end_color="DCEBDD")))


def hoja_config(wb):
    ws = wb.create_sheet("Config")
    encabezado(ws, ["clave", "valor", "para qué sirve (esta columna no se muestra)"])
    filas = [
        ("actualizado", None, "Fecha y hora de la última edición. La llena el Apps Script (o escríbela a mano, ej. 14:30). Debe quedar en B2."),
        ("titulo", "Colecta solidaria", "Título grande de la página."),
        ("mensaje", "¡Gracias por sumarte! Elige uno o más productos de la lista, cómpralos y entrégalos al salir.", "Texto breve bajo el título."),
        ("contacto", "", "Opcional: teléfono o forma de contacto. Se muestra al final."),
    ]
    for r, (clave, valor, nota) in enumerate(filas, start=2):
        ws.cell(row=r, column=1, value=clave).font = Font(bold=True)
        ws.cell(row=r, column=2, value=valor).alignment = Alignment(wrap_text=True, vertical="top")
        n = ws.cell(row=r, column=3, value=nota)
        n.font = NOTA_FONT
        n.alignment = Alignment(wrap_text=True, vertical="top")
    ws["B2"].number_format = "yyyy-mm-dd hh:mm"
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 60


def hoja_listas(wb):
    ws = wb.create_sheet("Listas")
    encabezado(ws, ["supermercados", "nota"])
    for r, s in enumerate(SUPERMERCADOS, start=2):
        ws.cell(row=r, column=1, value=s)
    nota = ws.cell(row=2, column=2, value=(
        "Códigos cortos, sin espacios. El QR de cada supermercado termina en ?s=<código>. "
        "Agrega o cambia los códigos aquí y aparecen en la lista desplegable de Items."))
    nota.font = NOTA_FONT
    nota.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 70


def hoja_instrucciones(wb):
    ws = wb.create_sheet("Instrucciones")
    ws["A1"] = "Cómo usar esta planilla"
    ws["A1"].font = Font(bold=True, size=14)
    lineas = [
        "Edita la pestaña Items durante el día: cambia «estado», suma «recibido» o pon «visible» en NO para ocultar un producto.",
        "No cambies los nombres de las pestañas ni la fila 1 (encabezados): la página los usa para leer la lista.",
        "«supermercado» vacío = el producto se muestra en todos lados. Con un código (ej. lider-centro) solo aparece en el QR de ese supermercado.",
        "«meta» y «recibido» son números sin unidades; si están los dos, la página muestra una barra de avance.",
        "Los cambios pueden tardar unos minutos en verse en la página (Google actualiza la versión publicada cada pocos minutos).",
    ]
    for r, texto in enumerate(lineas, start=3):
        c = ws.cell(row=r, column=1, value=f"{r - 2}. {texto}")
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 110


def main():
    wb = Workbook()
    hoja_items(wb)
    hoja_config(wb)
    hoja_listas(wb)
    hoja_instrucciones(wb)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    wb.save(SALIDA)
    print("Listo:", SALIDA)


if __name__ == "__main__":
    main()
