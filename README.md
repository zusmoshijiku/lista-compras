# Lista de insumos de la colecta

Página para el celular que muestra, siempre actualizada, la lista de productos que necesita la colecta. El papelito que reciben los benefactores lleva un **QR fijo** que abre esta página. El equipo edita una **planilla de Google Sheets** y la página la lee sola cada 2 minutos.

```
Google Sheets (el equipo edita)  →  CSV publicado  →  página en GitHub Pages  ←  QR impreso
```

- Sin servidor, sin claves, sin cuentas para el benefactor.
- Si se cae la señal en el supermercado, muestra la última lista guardada y lo avisa.
- Peso total: ~31 KB.

## Archivos

| Archivo | Para qué |
|---|---|
| `index.html`, `style.css`, `app.js` | La página. |
| `config.js` | **Lo único que hay que editar**: URLs de la planilla, título y cada cuánto se actualiza. |
| `sw.js` | Permite que la página abra sin señal (después de la primera visita). |
| `datos-ejemplo/` | Lista de ejemplo que se usa mientras `config.js` no tiene URL. |
| `plantilla/plantilla-sheet.xlsx` | Plantilla de la planilla, para escribir la lista a mano. |
| `plantilla/plantilla-sheet-maestro.xlsx` | Plantilla que calcula la lista sola desde el Excel maestro de operaciones (sección 1B). |
| `generar_qr.py`, `logo-qr.png` | Genera el QR en PNG y SVG, con `logo-qr.png` al centro. |
| `apps-script-opcional.gs` | Opcional: guarda la hora de la última edición. |
| `apps-script-maestro-opcional.gs` | Opcional: lo mismo, pero en el maestro (sección 1B). |
| `pruebas/pruebas.js` | Pruebas del lector de CSV y de la lógica (`node pruebas/pruebas.js`). |

---

## 1. Crear la planilla desde la plantilla

Hay dos plantillas; elige una:

- **`plantilla-sheet.xlsx`**: el equipo escribe la lista a mano en `Items`. Pasos de esta sección.
- **`plantilla-sheet-maestro.xlsx`**: la lista se calcula sola desde el Excel maestro de operaciones (metas y cajas recibidas). Sigue los pasos de esta sección con ese archivo y después la **sección 1B**.

1. Entra a [Google Drive](https://drive.google.com) → **Nuevo → Subir archivo** → elige la plantilla.
2. Abre el archivo subido con **Hojas de cálculo de Google**.
3. **Archivo → Guardar como Hojas de cálculo de Google.** Esto crea una copia en formato Google (sin este paso no se puede publicar). Trabaja siempre en esa copia; puedes borrar el `.xlsx`.
4. **Archivo → Configuración → Zona horaria**: elige *(GMT-03:00) Santiago* (o la que corresponda). Guarda.
5. Revisa las pestañas:
   - **Items**: borra las filas de ejemplo y escribe tu lista. No cambies la fila 1.
   - **Config**: cambia `titulo`, `mensaje` y `contacto`. Deja `actualizado` en la fila 2 (celda `B2`).
   - **Listas**: códigos de supermercados para la columna `supermercado` (ver más abajo).
   - **Instrucciones**: recordatorio para el equipo.
6. Comparte la planilla (botón **Compartir**) solo con los coordinadores, como **Editor**.

### Formato de la pestaña Items

| columna | qué va |
|---|---|
| `orden` | número; orden dentro de la categoría |
| `categoria` | ej. Abarrotes, Aseo, Higiene |
| `item` | nombre del producto (obligatorio; filas sin `item` se ignoran) |
| `detalle` | presentación o marca sugerida, ej. "bolsa 1 kg" (opcional) |
| `estado` | `Falta mucho` / `Falta poco` / `Cubierto` |
| `meta` | cantidad objetivo, solo el número (opcional) |
| `recibido` | cantidad reunida, solo el número (opcional) |
| `supermercado` | vacío = se muestra en todos lados; con un código, solo en el QR de ese supermercado |
| `visible` | `SI` / `NO`; con `NO` no se muestra |

Si `meta` y `recibido` tienen números y ya llegó algo, el producto muestra una barra de avance, y arriba aparece "Llevamos X % de la meta" (promedio del avance de cada producto). La página nunca muestra las cantidades (ni la meta ni cuánto falta), solo la proporción. Ojo: los números sí están en el CSV publicado, que cualquiera con la URL puede abrir.

La página no se cae con errores de tipeo: `estado` acepta mayúsculas y espacios de más (" cubierto " = "Cubierto"), y un estado desconocido se muestra en gris como "Se necesita".

## 1B. Conectar con el Excel maestro (solo `plantilla-sheet-maestro.xlsx`)

Es lo mismo que hacía la planilla del año pasado: la hoja "Stock" traía el maestro con `IMPORTRANGE` y la hoja "Público" calculaba la prioridad. Aquí la pestaña `Items` queda lista para la página, sin escribir nada a mano.

1. El maestro tiene que estar en Google Sheets. Si es un `.xlsx`, súbelo a Drive y usa **Archivo → Guardar como Hojas de cálculo de Google**. Copia su URL.
2. En la planilla de la página, pestaña **Maestro**: borra todo (lo que trae es solo un ejemplo) y escribe en `A1`:
   ```
   =IMPORTRANGE("URL del maestro"; "Meta (con JUNA)!A1:I250")
   ```
   - Usa `Meta (sin JUNA)` si esa es la hoja que corresponde.
   - Si tu planilla usa coma para separar argumentos, cambia `;` por `,`.
3. Haz clic en `A1` y luego en **Permitir acceso** (solo la primera vez).
4. Revisa la pestaña **Items**: se llena sola, con las secciones del maestro como categorías.

Cómo se arma cada columna de `Items`:

| columna | sale de |
|---|---|
| `categoria` | la fila de encabezado de cada sección del maestro: "Insumos Comida" → **Comida** |
| `item` | columna A del maestro (insumo) |
| `detalle` | columna B (unidad), como "Medida: Kilo"; se omite si la unidad es "Unidad" |
| `meta` | columna D (Meta a Alcanzar) |
| `recibido` | columna I (Total) |
| `estado` | avance = recibido ÷ meta: bajo 50 % **Falta mucho**, bajo 100 % **Falta poco**, desde 100 % **Cubierto** (mismos umbrales que la hoja "Público" del año pasado) |
| `visible` | `SI` si la meta es mayor que 0; los productos con meta 0 no se muestran |

Para que esto funcione, el maestro tiene que mantener su forma: columnas A a I en ese orden y cada sección partiendo con una fila de encabezado que diga "Meta a Alcanzar" en la columna D. Las celdas con error del maestro (`#REF!`, `#DIV/0!`) no rompen la página: sin meta, el producto se oculta; sin total, se cuenta como 0 recibido.

**Cambiar algo a mano:** no escribas en `Items`, porque cada celda es una fórmula y esa fila dejaría de actualizarse. Usa la pestaña **Ajustes**: elige el producto por su nombre y escribe solo lo que quieras cambiar:

- `estado`: por ejemplo "Cubierto", para dejar de pedirlo aunque el maestro diga que falta;
- `visible`: "NO", para ocultarlo;
- `supermercado`: para mostrarlo solo en el QR de un local;
- `detalle`: por ejemplo "bolsa 1 kg".

Lo que dejes vacío se sigue calculando desde el maestro. Como se busca por nombre, sigue funcionando aunque se agreguen filas al maestro.

**Hora de actualización (opcional):** pega `apps-script-maestro-opcional.gs` en el maestro (ver sección 7) y escribe en `Config!B2` de la planilla de la página:

```
=IMPORTRANGE("URL del maestro"; "Web!A1")
```

> Los cambios del maestro no llegan al instante: `IMPORTRANGE` se refresca cada cierto tiempo y, además, Google demora unos minutos en actualizar el CSV publicado.

## 2. Publicar cada pestaña como CSV

Hay que hacerlo **dos veces**: una para `Items` y otra para `Config`.

1. **Archivo → Compartir → Publicar en la web.**
2. En la pestaña **Vínculo**:
   - en el primer menú elige la pestaña **Items** (no "Documento completo");
   - en el segundo elige **Valores separados por comas (.csv)**.
3. Clic en **Publicar** → **Aceptar**. Copia la URL que aparece (termina en `output=csv`).
4. Repite con la pestaña **Config** y copia esa segunda URL.
5. En la misma ventana, abre **Contenido publicado y configuración** y verifica que esté marcado **"Volver a publicar automáticamente cuando se realicen cambios"**.

Para comprobar: pega la URL en el navegador; debería descargar o mostrar un texto con comas, no una página de Google.

> Publicar hace que cualquiera con la URL pueda leer esas pestañas. No pongas datos personales en la planilla.

## 3. Pegar las URLs en `config.js`

Abre `config.js` y completa:

```js
window.APP_CONFIG = {
  CSV_ITEMS_URL: "https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?gid=0&single=true&output=csv",
  CSV_CONFIG_URL: "https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?gid=123456&single=true&output=csv",
  REFRESH_SECONDS: 120,
  NOMBRE_CAMPAÑA: "Colecta solidaria"
};
```

- Mientras `CSV_ITEMS_URL` esté vacío, la página muestra los datos de ejemplo con un aviso azul "Modo de prueba".
- `NOMBRE_CAMPAÑA` se usa como título si la pestaña Config no trae `titulo`.

## 4. Desplegar en GitHub Pages

1. Sube los cambios al repositorio (rama `main`):
   ```powershell
   git add .
   ```
   ```powershell
   git commit -m "Configurar URLs de la planilla"
   ```
   ```powershell
   git push
   ```
2. En GitHub, en el repositorio: **Settings → Pages**.
3. En **Build and deployment → Source** elige **Deploy from a branch**; rama **main**, carpeta **/ (root)** → **Save**.
4. Espera uno o dos minutos. La dirección será:
   `https://<tu-usuario>.github.io/lista-compras/`
5. Ábrela en el celular y revisa que se vea tu lista (sin el aviso "Modo de prueba").

> El repositorio tiene que ser público para usar GitHub Pages gratis.

## 5. Generar el QR e imprimirlo

**El QR se imprime una sola vez: decide la URL definitiva antes.** Si después cambias el nombre del repositorio o tu usuario de GitHub, la URL cambia y los papelitos dejan de funcionar.

1. Instala los paquetes del QR (una sola vez):
   ```powershell
   pip install segno pillow
   ```
2. Genera el QR con la URL de GitHub Pages:
   ```powershell
   python generar_qr.py "https://<tu-usuario>.github.io/lista-compras/"
   ```
   Crea `qr-colecta.png` y `qr-colecta.svg`, con corrección de errores nivel H, borde blanco de 4 módulos y negro sobre blanco. Al centro pone `logo-qr.png`.
   - **El logo:** se recorta a su contenido y va sobre un recuadro blanco con su misma forma. Para cambiarlo, reemplaza `logo-qr.png` (PNG con fondo transparente es lo ideal) o usa `--logo otra-imagen.png`.
   - **Tamaño del logo:** por defecto el recuadro tapa el 12 % de la superficie del QR. Con `--logo-area 15` (el máximo) se ve más grande; con `--logo-area 8`, más chico. Mientras más grande, menos margen queda si el papel se arruga o se mancha.
   - **Sin logo:** usa `--sin-logo`.
3. Para el papelito, usa el **SVG** (no pierde calidad al cambiar de tamaño) o el PNG.
4. Al imprimir:
   - tamaño mínimo **3 × 3 cm**; mejor 4 cm;
   - negro sobre fondo blanco, sin poner el QR sobre fotos o colores;
   - deja el margen blanco alrededor (no lo recortes);
   - agrega una línea de texto bajo el QR, por ejemplo: *"Escanea para ver lo que más falta hoy"*.
5. **Antes de imprimir en cantidad**, imprime uno y escanéalo con al menos dos celulares distintos (uno Android y un iPhone, si se puede), también desde un poco más lejos y con poca luz. Si a alguno le cuesta, genera el QR con un `--logo-area` menor.

### QR distinto por supermercado (opcional)

Si un producto solo hace falta en un local, escribe su código en la columna `supermercado` (ej. `lider-centro`) y genera un QR para ese local agregando `?s=` a la URL:

```powershell
python generar_qr.py "https://<tu-usuario>.github.io/lista-compras/?s=lider-centro" -o qr/lider-centro
```

Ese QR muestra los productos generales más los de `lider-centro`. El QR sin `?s=` no muestra los productos marcados para un supermercado. Usa códigos cortos, en minúscula y sin espacios; puedes mantenerlos en la pestaña **Listas**. Se pueden poner varios códigos en una celda, separados por coma.

## 6. Probar

**En tu computador, sin configurar nada:**

- Doble clic en `index.html`: se ve la lista de ejemplo.
- Con servidor local (más parecido a GitHub Pages; aquí también funcionan la caché y el modo sin conexión):
  ```powershell
  python -m http.server 8000
  ```
  Abre `http://localhost:8000`. En el navegador, abre las herramientas de desarrollo (F12) y activa la vista de celular (Ctrl+Shift+M) con 375 px de ancho.
- Filtro por supermercado: `http://localhost:8000/?s=lider-centro` (aparece "Pasta de dientes").
- Simular que no hay señal: `http://localhost:8000/?prueba=sin-conexion` (muestra la lista guardada con el aviso amarillo; si no hay nada guardado, muestra el mensaje de error).
- Pruebas del lector de CSV (requiere Node.js):
  ```powershell
  node pruebas/pruebas.js
  ```

**Con la planilla real**, después de desplegar:

1. Abre la página en el celular.
2. Cambia el `estado` de un producto en la planilla.
3. Espera unos minutos y toca **Actualizar**: el cambio debería aparecer.
4. Activa el modo avión y recarga: debería verse la lista con el aviso "Sin conexión…".

Si cambias los CSV de `datos-ejemplo/`, regenera la copia que se usa al abrir con doble clic:

```powershell
python datos-ejemplo/generar_ejemplo_js.py
```

Si cambias las filas de ejemplo o el formato de las plantillas, regenéralas (requiere `openpyxl`):

```powershell
python plantilla/generar_plantilla.py
```

Para revisar la plantilla del maestro con los datos reales antes de subirla, puedes crear una copia local con los valores de una hoja del maestro pegados en `Maestro`. Guárdala fuera del repositorio, porque el repositorio es público:

```powershell
python plantilla/generar_plantilla.py --maestro-xlsx "$HOME\Downloads\Maestro Operaciones Verano 2027.xlsx" --hoja "Meta (con JUNA)" -o "$HOME\Downloads\prueba-maestro.xlsx"
```

## 7. Opcional: hora de la última edición

Con este script, cada vez que alguien edita la planilla se guarda la fecha y hora en `Config!B2`, y la página muestra **"Actualizado a las HH:MM"**. Sin el script, esa etiqueta no aparece (o puedes escribir la hora a mano en `B2`, ej. `14:30`).

1. En la planilla: **Extensiones → Apps Script**.
2. Borra lo que aparece en el editor y pega el contenido de `apps-script-opcional.gs`.
3. Clic en **Guardar** (ícono de disquete). Ponle un nombre al proyecto si lo pide.
4. Vuelve a la planilla, cambia cualquier celda de `Items` y revisa que `Config!B2` muestre la fecha y hora.

No hace falta darle permisos ni configurar activadores: `onEdit` corre solo al editar. Asegúrate de que la zona horaria de la planilla esté bien (paso 1.4).

**Con la plantilla del maestro**, este script no sirve: la lista cambia cuando se edita el maestro, no la planilla de la página. En su lugar:

1. En el **maestro**, crea una pestaña vacía llamada `Web`.
2. En el maestro: **Extensiones → Apps Script**, pega `apps-script-maestro-opcional.gs` y guarda. Si el maestro ya tenía una función `onEdit`, copia sus líneas dentro de la existente en vez de pegar otra.
3. En la planilla de la página, escribe en `Config!B2`: `=IMPORTRANGE("URL del maestro"; "Web!A1")`.

---

## Cómo actualizar durante el día (para coordinadores)

**Si usan la plantilla del maestro:** actualicen el maestro como siempre (cajas y metas); la página se pone al día sola. Para excepciones, usen la pestaña **Ajustes**, nunca `Items`. Lo de abajo aplica a la planilla manual.

- **Cambia el `estado`** con la lista desplegable: *Falta mucho* → *Falta poco* → *Cubierto*.
- **Suma lo recibido** en `recibido` (solo el número). La barra se mueve sola.
- **¿Ya no hace falta un producto?** Ponlo en *Cubierto* (se ve atenuado, al final de su categoría) o en `visible` = `NO` para que desaparezca.
- **¿Producto nuevo?** Agrega una fila al final con `item`, `categoria`, `estado` y `visible` = `SI`.
- **Los cambios tardan unos minutos** en verse: Google actualiza la versión publicada cada pocos minutos y la página vuelve a leer cada 2 minutos. No es un error.
- **No cambies** los nombres de las pestañas, los encabezados de la fila 1 ni la celda `A2` de Config.
- **No borres** la publicación en la web: si se despublica, la página mostrará solo la última lista guardada en cada celular.
- Para revisar cómo se ve, escanea tu propio QR y toca **Actualizar**.
