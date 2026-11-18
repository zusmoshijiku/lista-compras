/*
 * Configuración de la página. Es el único archivo que hay que editar.
 *
 * CSV_ITEMS_URL  → URL del CSV publicado de la pestaña "Items".
 *                  Si queda vacío, la página muestra los datos de ejemplo
 *                  (carpeta datos-ejemplo/), útil para probar en local.
 * CSV_CONFIG_URL → URL del CSV publicado de la pestaña "Config" (opcional).
 * REFRESH_SECONDS → cada cuántos segundos se vuelve a leer la planilla
 *                  mientras la página está abierta (mínimo 30).
 * NOMBRE_CAMPAÑA → título que se usa si la pestaña Config no trae "titulo".
 *
 * Las URLs se ven así:
 * https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?gid=0&single=true&output=csv
 */
window.APP_CONFIG = {
  CSV_ITEMS_URL: "https://docs.google.com/spreadsheets/d/e/2PACX-1vSYjZ2DjnzOM6Zn_8aI-BO822BRl0gPzhwbrr0whm8DxsxQ0_agC0LjkW3Pslz7vVnaN0dDpq3FcUP6/pub?gid=192444426&single=true&output=csv",
  CSV_CONFIG_URL: "https://docs.google.com/spreadsheets/d/e/2PACX-1vSYjZ2DjnzOM6Zn_8aI-BO822BRl0gPzhwbrr0whm8DxsxQ0_agC0LjkW3Pslz7vVnaN0dDpq3FcUP6/pub?gid=739723525&single=true&output=csv",
  REFRESH_SECONDS: 120,
  NOMBRE_CAMPAÑA: "Colecta de Insumos TDI"
};
