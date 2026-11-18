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
  CSV_ITEMS_URL: "",
  CSV_CONFIG_URL: "",
  REFRESH_SECONDS: 120,
  NOMBRE_CAMPAÑA: "Colecta solidaria"
};
