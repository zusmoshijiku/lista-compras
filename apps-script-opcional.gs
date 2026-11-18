/**
 * Opcional. Escribe en Config!B2 la fecha y hora de la última edición,
 * para que la página muestre "Actualizado a las HH:MM".
 * Pegar en Extensiones → Apps Script (ver README).
 */
function onEdit(e) {
  var hoja = e.range.getSheet().getName();
  if (hoja !== 'Items' && hoja !== 'Config') return;
  if (hoja === 'Config' && e.range.getA1Notation() === 'B2') return;
  var celda = e.source.getSheetByName('Config').getRange('B2');
  celda.setValue(new Date()).setNumberFormat('yyyy-mm-dd hh:mm');
}
