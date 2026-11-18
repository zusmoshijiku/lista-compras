/**
 * Opcional, para el Excel/Sheet MAESTRO de operaciones (no para la planilla de la página).
 * Guarda en la pestaña "Web", celda A1, la fecha y hora de la última edición del maestro.
 * La planilla de la página la lee en Config!B2 con:  =IMPORTRANGE("URL del maestro"; "Web!A1")
 * Antes de pegarlo, crea en el maestro una pestaña vacía llamada Web.
 * Si el maestro ya tiene una función onEdit, copia estas líneas dentro de ella en vez de pegar otra.
 */
function onEdit(e) {
  var web = e.source.getSheetByName('Web');
  if (!web || e.range.getSheet().getName() === 'Web') return;
  web.getRange('A1').setValue(new Date()).setNumberFormat('yyyy-mm-dd hh:mm');
}
