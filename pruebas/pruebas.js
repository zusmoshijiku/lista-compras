/* Pruebas de las funciones puras de app.js.  Uso: node pruebas/pruebas.js */
"use strict";
var assert = require("assert");
var fs = require("fs");
var path = require("path");
var A = require("../app.js");

var ok = 0;
function prueba(nombre, fn) {
  try { fn(); ok++; console.log("  ✓ " + nombre); }
  catch (e) { console.error("  ✗ " + nombre + "\n    " + e.message); process.exitCode = 1; }
}

console.log("Parser CSV");
prueba("campos simples y salto final", function () {
  assert.deepStrictEqual(A.parseCSV("a,b,c\n1,2,3\n"), [["a", "b", "c"], ["1", "2", "3"]]);
});
prueba("comas dentro de comillas", function () {
  assert.deepStrictEqual(A.parseCSV('x,"uno, dos",y'), [["x", "uno, dos", "y"]]);
});
prueba("comillas escapadas", function () {
  assert.deepStrictEqual(A.parseCSV('"dijo ""hola""",fin'), [['dijo "hola"', "fin"]]);
});
prueba("salto de línea dentro de un campo (LF y CRLF)", function () {
  assert.deepStrictEqual(A.parseCSV('a,"línea 1\nlínea 2"\r\nb,"x\r\ny"'), [["a", "línea 1\nlínea 2"], ["b", "x\r\ny"]]);
});
prueba("CRLF, CR solo y BOM", function () {
  assert.deepStrictEqual(A.parseCSV("﻿a,b\r\n1,2\r3,4"), [["a", "b"], ["1", "2"], ["3", "4"]]);
});
prueba("campos vacíos y fila vacía", function () {
  assert.deepStrictEqual(A.parseCSV(",,\n\na,,"), [["", "", ""], [""], ["a", "", ""]]);
});
prueba("campo entre comillas vacío y comillas con coma y salto juntos", function () {
  assert.deepStrictEqual(A.parseCSV('"",",\n""",z'), [["", ',\n"', "z"]]);
});
prueba("texto vacío o nulo", function () {
  assert.deepStrictEqual(A.parseCSV(""), []);
  assert.deepStrictEqual(A.parseCSV(null), []);
});
prueba("comilla suelta dentro de un campo sin comillas se mantiene", function () {
  assert.deepStrictEqual(A.parseCSV('5" pulgadas,b'), [['5" pulgadas', "b"]]);
});

console.log("Normalización");
prueba("estado con mayúsculas y espacios", function () {
  assert.strictEqual(A.normEstado(" cubierto "), "cubierto");
  assert.strictEqual(A.normEstado("CUBIERTO"), "cubierto");
  assert.strictEqual(A.normEstado("FALTA  POCO"), "poco");
  assert.strictEqual(A.normEstado("falta mucho"), "mucho");
  assert.strictEqual(A.normEstado("\tFalta Mucho "), "mucho");
});
prueba("estado desconocido o vacío → otro", function () {
  assert.strictEqual(A.normEstado("Por revisar"), "otro");
  assert.strictEqual(A.normEstado(""), "otro");
  assert.strictEqual(A.normEstado(undefined), "otro");
});
prueba("números", function () {
  assert.strictEqual(A.parseNum("12"), 12);
  assert.strictEqual(A.parseNum(" 1.500 "), 1500);
  assert.strictEqual(A.parseNum("2,5"), 2.5);
  assert.strictEqual(A.parseNum("1.5"), 1.5);
  assert.strictEqual(A.parseNum("12 kg"), null);
  assert.strictEqual(A.parseNum(""), null);
});

console.log("Items");
var csvRaro = [
  "Visible,Ítem,Categoría,ESTADO,orden,meta,recibido,supermercado,detalle",
  'si,"Arroz, grado 1",Abarrotes, cubierto ,2,10,10,,"bolsa ""1 kg"""',
  "SI,Aceite,Abarrotes,Falta poco,1,,,,",
  "NO,Oculto,Abarrotes,Falta mucho,3,,,,",
  "SI,Solo Líder,Aseo,urgente!!,1,5,1,Lider-Centro; jumbo-sur,",
  ",,,,,,,,",
  "SI,Cloro,Aseo,Cubierto,2,,,,"
].join("\r\n");
var items = A.parseItems(A.parseCSV(csvRaro));
prueba("encabezados en otro orden, con tildes y mayúsculas", function () {
  assert.strictEqual(items.length, 5);
  assert.strictEqual(items[0].item, "Arroz, grado 1");
  assert.strictEqual(items[0].detalle, 'bolsa "1 kg"');
  assert.strictEqual(items[0].estado, "cubierto");
  assert.strictEqual(items[0].meta, 10);
});
prueba("visible NO se filtra; supermercado exige ?s=", function () {
  assert.deepStrictEqual(A.filtrar(items, "").map(function (i) { return i.item; }), ["Arroz, grado 1", "Aceite", "Cloro"]);
  assert.deepStrictEqual(A.filtrar(items, "lider-centro").map(function (i) { return i.item; }), ["Arroz, grado 1", "Aceite", "Solo Líder", "Cloro"]);
  assert.deepStrictEqual(A.filtrar(items, "JUMBO-SUR").length, 4);
  assert.deepStrictEqual(A.filtrar(items, "otro").length, 3);
});
prueba("agrupar: cubiertos al final y categorías completas al final", function () {
  var cats = A.agrupar(A.filtrar(items, "lider-centro"));
  assert.deepStrictEqual(cats.map(function (c) { return c.nombre; }), ["Abarrotes", "Aseo"]);
  assert.deepStrictEqual(cats[0].items.map(function (i) { return i.item; }), ["Aceite", "Arroz, grado 1"]);
  var soloCubiertos = A.agrupar(A.filtrar(items, "")).map(function (c) { return c.nombre + ":" + c.pendientes; });
  assert.deepStrictEqual(soloCubiertos, ["Abarrotes:1", "Aseo:0"]);
});
prueba("estado desconocido no rompe y cuenta como pendiente", function () {
  var x = items.filter(function (i) { return i.item === "Solo Líder"; })[0];
  assert.strictEqual(x.estado, "otro");
  assert.strictEqual(A.agrupar([x])[0].pendientes, 1);
});
prueba("sin columna item → error de formato", function () {
  assert.throws(function () { A.parseItems(A.parseCSV("<html>hola</html>")); }, /columna "item"/);
});
prueba("progreso global", function () {
  var g = A.progresoGlobal(A.filtrar(items, "lider-centro"));
  assert.strictEqual(g.pct, 60); // (100% + 20%) / 2
  assert.strictEqual(g.cubiertos, 2);
  assert.strictEqual(g.total, 4);
});

console.log("Config y fechas");
prueba("config clave/valor con comas y comillas", function () {
  var c = A.parseConfig(A.parseCSV('clave,valor\nTitulo,"Colecta, ""invierno"""\nactualizado,\n'));
  assert.deepStrictEqual(c, { titulo: 'Colecta, "invierno"', actualizado: "" });
});
prueba("fechas en varios formatos", function () {
  var hoy = new Date(2026, 10, 17, 18, 0);
  var f1 = A.parseFecha("2026-11-17 14:35", hoy);
  assert.deepStrictEqual(A.cuando(f1, hoy), { hoy: true, hora: "14:35", fecha: "17/11" });
  var f2 = A.parseFecha("16/11/2026 9:05:00", hoy);
  assert.deepStrictEqual(A.cuando(f2, hoy), { hoy: false, hora: "09:05", fecha: "16/11" });
  var f3 = A.parseFecha("8:30", hoy);
  assert.deepStrictEqual(A.cuando(f3, hoy), { hoy: true, hora: "08:30", fecha: "17/11" });
  assert.strictEqual(A.parseFecha("", hoy), null);
  assert.strictEqual(A.parseFecha("ayer en la tarde", hoy), null);
});

console.log("Datos de ejemplo");
prueba("items.csv de ejemplo se lee completo y cubre todos los estados", function () {
  var txt = fs.readFileSync(path.join(__dirname, "..", "datos-ejemplo", "items.csv"), "utf8");
  var its = A.parseItems(A.parseCSV(txt));
  assert.strictEqual(its.length, 19);
  var estados = {};
  its.forEach(function (i) { estados[i.estado] = true; });
  assert.deepStrictEqual(Object.keys(estados).sort(), ["cubierto", "mucho", "otro", "poco"]);
  var panales = its.filter(function (i) { return i.item === "Pañales"; })[0];
  assert.ok(panales.detalle.indexOf("\n") > 0, "detalle multilínea");
});
prueba("ejemplo.js está sincronizado con los CSV", function () {
  var js = fs.readFileSync(path.join(__dirname, "..", "datos-ejemplo", "ejemplo.js"), "utf8");
  var sandbox = {};
  new Function("window", js)(sandbox);
  var dir = path.join(__dirname, "..", "datos-ejemplo");
  function lf(s) { return s.replace(/\r\n/g, "\n"); } // git en Windows puede cambiar los saltos de línea
  assert.strictEqual(lf(sandbox.DATOS_EJEMPLO.items), lf(fs.readFileSync(path.join(dir, "items.csv"), "utf8")));
  assert.strictEqual(lf(sandbox.DATOS_EJEMPLO.config), lf(fs.readFileSync(path.join(dir, "config.csv"), "utf8")));
});

console.log("\n" + ok + " pruebas OK" + (process.exitCode ? ", con fallas" : ""));
