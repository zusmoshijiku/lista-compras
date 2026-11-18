/*
 * Lista de la colecta: lee el CSV publicado desde Google Sheets y lo muestra.
 * JavaScript vanilla, sin dependencias. Todo el contenido de la planilla se
 * pinta con textContent (nunca innerHTML).
 *
 * La primera mitad son funciones puras (se prueban con: node pruebas/pruebas.js).
 * La segunda mitad maneja la página.
 */
(function (global) {
  "use strict";

  /* =====================================================================
   * Funciones puras
   * ===================================================================== */

  /**
   * Parser CSV (RFC 4180, tolerante). Maneja comillas, comillas dobles
   * escapadas (""), comas y saltos de línea dentro de campos, CRLF/LF/CR y BOM.
   * Devuelve un arreglo de filas; cada fila es un arreglo de strings.
   */
  function parseCSV(text) {
    if (text == null) return [];
    text = String(text);
    if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);

    var rows = [];
    var row = [];
    var field = "";
    var inQuotes = false;
    var i = 0;
    var n = text.length;

    while (i < n) {
      var c = text.charAt(i);
      if (inQuotes) {
        if (c === '"') {
          if (text.charAt(i + 1) === '"') { field += '"'; i += 2; continue; }
          inQuotes = false; i++; continue;
        }
        field += c; i++; continue;
      }
      if (c === '"' && field === "") { inQuotes = true; i++; continue; }
      if (c === ",") { row.push(field); field = ""; i++; continue; }
      if (c === "\r" || c === "\n") {
        row.push(field); rows.push(row);
        row = []; field = "";
        if (c === "\r" && text.charAt(i + 1) === "\n") i++;
        i++; continue;
      }
      field += c; i++;
    }
    if (field !== "" || row.length) { row.push(field); rows.push(row); }
    return rows;
  }

  /** Minúsculas, sin tildes, espacios colapsados y recortados. */
  function norm(s) {
    var v = String(s == null ? "" : s);
    if (v.normalize) v = v.normalize("NFD").replace(/[̀-ͯ]/g, "");
    return v.replace(/\s+/g, " ").trim().toLowerCase();
  }

  /** "Falta mucho" → mucho, "Falta poco" → poco, "Cubierto" → cubierto, otro → otro. */
  function normEstado(s) {
    var v = norm(s);
    if (v.indexOf("cubiert") >= 0) return "cubierto";
    if (v.indexOf("poco") >= 0) return "poco";
    if (v.indexOf("mucho") >= 0) return "mucho";
    return "otro";
  }

  /** Número desde texto: "12", "1.500" (miles), "2,5", "2.5". Si no es número, null. */
  function parseNum(s) {
    var v = String(s == null ? "" : s).replace(/\s/g, "");
    if (!v) return null;
    if (/^-?\d{1,3}(\.\d{3})+$/.test(v)) v = v.replace(/\./g, "");
    else v = v.replace(",", ".");
    if (!/^-?\d+(\.\d+)?$/.test(v)) return null;
    return parseFloat(v);
  }

  function celda(row, idx) {
    return idx >= 0 && row[idx] != null ? String(row[idx]).trim() : "";
  }

  var COLUMNAS = ["orden", "categoria", "item", "detalle", "estado", "meta", "recibido", "supermercado", "visible"];

  /** Filas del CSV de Items → arreglo de ítems. Lanza error si falta la columna "item". */
  function parseItems(rows) {
    if (!rows || !rows.length) return [];
    var head = rows[0].map(norm);
    var ix = {};
    COLUMNAS.forEach(function (c) { ix[c] = head.indexOf(c); });
    if (ix.item < 0) {
      var e = new Error("La planilla no tiene la columna \"item\" en la primera fila.");
      e.formato = true;
      throw e;
    }
    var out = [];
    for (var r = 1; r < rows.length; r++) {
      var row = rows[r];
      var nombre = celda(row, ix.item);
      if (!nombre) continue;
      var supersRaw = celda(row, ix.supermercado).split(/[,;]/).map(function (x) { return x.trim(); }).filter(Boolean);
      out.push({
        fila: r,
        orden: parseNum(celda(row, ix.orden)),
        categoria: celda(row, ix.categoria) || "Otros",
        item: nombre,
        detalle: celda(row, ix.detalle),
        estado: normEstado(celda(row, ix.estado)),
        meta: parseNum(celda(row, ix.meta)),
        recibido: parseNum(celda(row, ix.recibido)),
        supers: supersRaw.map(norm),
        supersRaw: supersRaw,
        visible: norm(celda(row, ix.visible)) !== "no"
      });
    }
    return out;
  }

  /** Filas del CSV de Config (clave en A, valor en B) → objeto. */
  function parseConfig(rows) {
    var cfg = {};
    (rows || []).forEach(function (r) {
      var k = norm(r[0]);
      if (k && k !== "clave") cfg[k] = celda(r, 1);
    });
    return cfg;
  }

  /** Visibles y que aplican al supermercado pedido (?s=). */
  function filtrar(items, superParam) {
    var s = norm(superParam);
    return items.filter(function (it) {
      if (!it.visible) return false;
      if (!it.supers.length) return true;
      return !!s && it.supers.indexOf(s) >= 0;
    });
  }

  function cmpItems(a, b) {
    var ca = a.estado === "cubierto", cb = b.estado === "cubierto";
    if (ca !== cb) return ca ? 1 : -1;
    var oa = a.orden == null ? Infinity : a.orden;
    var ob = b.orden == null ? Infinity : b.orden;
    if (oa !== ob) return oa < ob ? -1 : 1;
    return a.fila - b.fila;
  }

  /**
   * Agrupa por categoría (en el orden en que aparecen en la planilla).
   * Dentro de cada una: pendientes por "orden" y cubiertos al final.
   * Las categorías que ya están completas van al final de la página.
   */
  function agrupar(items) {
    var cats = [], mapa = {};
    items.forEach(function (it) {
      var k = norm(it.categoria);
      if (!mapa[k]) { mapa[k] = { nombre: it.categoria, items: [], primera: it.fila }; cats.push(mapa[k]); }
      mapa[k].items.push(it);
    });
    cats.forEach(function (c) {
      c.items.sort(cmpItems);
      c.pendientes = c.items.filter(function (it) { return it.estado !== "cubierto"; }).length;
    });
    cats.sort(function (a, b) {
      var pa = a.pendientes > 0, pb = b.pendientes > 0;
      if (pa !== pb) return pa ? -1 : 1;
      return a.primera - b.primera;
    });
    return cats;
  }

  /** Avance global: promedio del % de cada ítem con meta y recibido numéricos. */
  function progresoGlobal(items) {
    var suma = 0, n = 0, cubiertos = 0;
    items.forEach(function (it) {
      if (it.estado === "cubierto") cubiertos++;
      if (it.meta != null && it.meta > 0 && it.recibido != null) {
        suma += Math.max(0, Math.min(1, it.recibido / it.meta));
        n++;
      }
    });
    return {
      pct: n ? Math.round((suma / n) * 100) : null,
      cubiertos: cubiertos,
      total: items.length
    };
  }

  /**
   * Fecha desde texto: "2026-11-17 14:35", "17/11/2026 14:35:00", "17-11-26 14:35"
   * o solo "14:35" (se asume hoy). Devuelve Date o null.
   */
  function parseFecha(s, ahora) {
    var v = String(s == null ? "" : s).trim();
    if (!v) return null;
    ahora = ahora || new Date();
    var m = v.match(/^(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{2})/);
    if (m) return valida(new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]));
    m = v.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2}|\d{4}),?\s+(\d{1,2}):(\d{2})/);
    if (m) {
      var y = +m[3]; if (y < 100) y += 2000;
      return valida(new Date(y, +m[2] - 1, +m[1], +m[4], +m[5]));
    }
    m = v.match(/^(\d{1,2}):(\d{2})(:\d{2})?$/);
    if (m) return valida(new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate(), +m[1], +m[2]));
    return null;
  }

  function valida(d) { return isNaN(d.getTime()) ? null : d; }

  function dos(n) { return (n < 10 ? "0" : "") + n; }

  /** {hoy, hora: "14:35", fecha: "16/11"} */
  function cuando(d, ahora) {
    ahora = ahora || new Date();
    return {
      hoy: d.toDateString() === ahora.toDateString(),
      hora: dos(d.getHours()) + ":" + dos(d.getMinutes()),
      fecha: dos(d.getDate()) + "/" + dos(d.getMonth() + 1)
    };
  }

  var puras = {
    parseCSV: parseCSV, norm: norm, normEstado: normEstado, parseNum: parseNum,
    parseItems: parseItems, parseConfig: parseConfig, filtrar: filtrar,
    agrupar: agrupar, progresoGlobal: progresoGlobal, parseFecha: parseFecha, cuando: cuando
  };

  if (typeof document === "undefined") {
    if (typeof module !== "undefined" && module.exports) module.exports = puras;
    return;
  }

  /* =====================================================================
   * Página
   * ===================================================================== */

  var CFG = global.APP_CONFIG || {};
  var ITEMS_URL = String(CFG.CSV_ITEMS_URL || "").trim();
  var CONFIG_URL = String(CFG.CSV_CONFIG_URL || "").trim();
  var DEMO = !ITEMS_URL;
  if (DEMO) {
    ITEMS_URL = "datos-ejemplo/items.csv";
    if (!CONFIG_URL) CONFIG_URL = "datos-ejemplo/config.csv";
  }
  var REFRESH_MS = Math.max(30, Number(CFG.REFRESH_SECONDS) || 120) * 1000;
  var TIMEOUT_MS = 12000;
  var params = new URLSearchParams(location.search);
  var SUPER = (params.get("s") || "").trim();
  var SIMULAR_SIN_RED = params.get("prueba") === "sin-conexion";
  var CLAVE = "colecta:v1:" + ITEMS_URL;

  var TEXTO_ESTADO = { mucho: "Falta mucho", poco: "Falta poco", cubierto: "Cubierto", otro: "Se necesita" };

  function $(id) { return document.getElementById(id); }
  var ui = {
    titulo: $("titulo"), mensaje: $("mensaje"), super: $("super"),
    actualizado: $("actualizado"), btn: $("btn-actualizar"),
    demo: $("demo"), aviso: $("aviso"),
    global: $("global"), globalTexto: $("global-texto"), globalBarra: $("global-barra"), globalSub: $("global-sub"),
    lista: $("lista"), contacto: $("contacto")
  };

  var cargando = false;
  var hayLista = false;
  var ultimoIntento = 0;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function vaciar(nodo) { while (nodo.firstChild) nodo.removeChild(nodo.firstChild); }

  function setTexto(nodo, texto) {
    nodo.textContent = texto || "";
    nodo.hidden = !texto;
  }

  function fmtNum(n) {
    try { return n.toLocaleString("es-CL", { maximumFractionDigits: 1 }); }
    catch (e) { return String(n); }
  }

  function barra(pct, nombre) {
    var b = el("div", "barra");
    b.setAttribute("role", "progressbar");
    b.setAttribute("aria-valuemin", "0");
    b.setAttribute("aria-valuemax", "100");
    b.setAttribute("aria-valuenow", String(pct));
    b.setAttribute("aria-label", nombre);
    var f = el("span", "barra-relleno");
    f.style.width = pct + "%";
    b.appendChild(f);
    return b;
  }

  function renderItem(it) {
    var li = el("li", "item item--" + it.estado);
    var fila = el("div", "item-fila");
    fila.appendChild(el("span", "item-nombre", it.item));
    var tag = el("span", "etiqueta etiqueta--" + it.estado);
    if (it.estado === "cubierto") {
      var chk = el("span", null, "✓ ");
      chk.setAttribute("aria-hidden", "true");
      tag.appendChild(chk);
    }
    tag.appendChild(document.createTextNode(TEXTO_ESTADO[it.estado]));
    fila.appendChild(tag);
    li.appendChild(fila);

    if (it.detalle) li.appendChild(el("p", "item-detalle", it.detalle));

    if (it.meta != null && it.meta > 0 && it.recibido != null) {
      var pct = Math.max(0, Math.min(100, Math.round((it.recibido / it.meta) * 100)));
      var p = el("div", "progreso");
      p.appendChild(barra(pct, "Avance de " + it.item));
      p.appendChild(el("span", "progreso-texto", fmtNum(it.recibido) + " de " + fmtNum(it.meta)));
      li.appendChild(p);
    }
    return li;
  }

  function procesar(itemsTxt, cfgTxt) {
    return {
      items: parseItems(parseCSV(itemsTxt)),
      config: cfgTxt ? parseConfig(parseCSV(cfgTxt)) : {}
    };
  }

  function mostrar(datos) {
    hayLista = true;
    var cfg = datos.config;

    var titulo = cfg.titulo || CFG["NOMBRE_CAMPAÑA"] || "Lista de la colecta";
    ui.titulo.textContent = titulo;
    document.title = titulo;
    setTexto(ui.mensaje, cfg.mensaje);
    setTexto(ui.contacto, cfg.contacto);

    // "Actualizado a las HH:MM": solo con el dato de la planilla, nunca la hora de carga.
    var f = parseFecha(cfg.actualizado);
    if (f) {
      var c = cuando(f);
      setTexto(ui.actualizado, c.hoy ? "Actualizado a las " + c.hora : "Actualizado el " + c.fecha + " a las " + c.hora);
    } else {
      setTexto(ui.actualizado, cfg.actualizado ? "Actualizado: " + cfg.actualizado : "");
    }

    var visibles = filtrar(datos.items, SUPER);

    if (SUPER) {
      var nombreSuper = SUPER;
      datos.items.some(function (it) {
        var i = it.supers.indexOf(norm(SUPER));
        if (i >= 0) { nombreSuper = it.supersRaw[i]; return true; }
        return false;
      });
      setTexto(ui.super, "Lista para: " + nombreSuper);
    }

    var g = progresoGlobal(visibles);
    if (g.total) {
      ui.global.hidden = false;
      vaciar(ui.globalBarra);
      if (g.pct != null) {
        ui.globalTexto.textContent = "Llevamos " + g.pct + "% de la meta";
        ui.globalBarra.appendChild(barra(g.pct, "Avance total de la colecta"));
      } else {
        ui.globalTexto.textContent = "Así vamos";
      }
      ui.globalSub.textContent = g.cubiertos === 1
        ? "1 de " + g.total + " productos ya está cubierto."
        : g.cubiertos + " de " + g.total + " productos ya están cubiertos.";
    } else {
      ui.global.hidden = true;
    }

    var frag = document.createDocumentFragment();
    if (g.cubiertos === g.total) {
      frag.appendChild(el("p", "vacio", "Por ahora no hay ítems pendientes. ¡Gracias!"));
    }
    agrupar(visibles).forEach(function (cat) {
      var sec = el("section", "categoria");
      var h = el("h2", null, cat.nombre);
      h.appendChild(el("span", "categoria-cuenta",
        cat.pendientes === 0 ? "Todo cubierto" : cat.pendientes === 1 ? "1 por cubrir" : cat.pendientes + " por cubrir"));
      sec.appendChild(h);
      var ul = el("ul", "items");
      cat.items.forEach(function (it) { ul.appendChild(renderItem(it)); });
      sec.appendChild(ul);
      frag.appendChild(sec);
    });
    vaciar(ui.lista);
    ui.lista.appendChild(frag);
    ui.lista.setAttribute("aria-busy", "false");
  }

  function mostrarError() {
    var box = el("div", "error");
    box.setAttribute("role", "alert");
    var p1 = el("p");
    p1.appendChild(el("strong", null, "No pudimos cargar la lista."));
    box.appendChild(p1);
    box.appendChild(el("p", null, "Revisa tu señal e intenta de nuevo. Si no carga, pregúntale a alguien del equipo de la colecta."));
    var b = el("button", "btn", "Reintentar");
    b.type = "button";
    b.addEventListener("click", function () { cargar(); });
    box.appendChild(b);
    vaciar(ui.lista);
    ui.lista.appendChild(box);
    ui.lista.setAttribute("aria-busy", "false");
  }

  function avisar(texto) { setTexto(ui.aviso, texto); }

  /* ---------- Almacenamiento local ---------- */
  function leerGuardado() {
    try {
      var c = JSON.parse(localStorage.getItem(CLAVE) || "null");
      return c && typeof c.items === "string" ? c : null;
    } catch (e) { return null; }
  }
  function guardar(obj) {
    try { localStorage.setItem(CLAVE, JSON.stringify(obj)); } catch (e) { /* sin espacio o bloqueado */ }
  }

  /* ---------- Red ---------- */
  function conCacheBusting(url) {
    return url + (url.indexOf("?") >= 0 ? "&" : "?") + "_=" + Date.now();
  }

  function traer(url) {
    if (SIMULAR_SIN_RED) return Promise.reject(new TypeError("Sin conexión (simulado)"));
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, TIMEOUT_MS) : null;
    return fetch(conCacheBusting(url), { cache: "no-store", credentials: "omit", signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status + " al leer " + url);
        return r.text();
      })
      .then(function (txt) {
        // Si la planilla no está publicada, Google responde una página HTML.
        if (/^\s*</.test(txt)) {
          var e = new Error("La URL no devolvió un CSV (¿la pestaña está publicada como CSV?): " + url);
          e.formato = true;
          throw e;
        }
        return txt;
      })
      .then(function (txt) { clearTimeout(timer); return txt; },
            function (err) { clearTimeout(timer); throw err; });
  }

  // Al abrir index.html con doble clic (file://) el navegador bloquea fetch;
  // en modo de prueba se usa una copia de los CSV de ejemplo en ejemplo.js.
  var promesaEjemplo = null;
  function traerEjemplo() {
    if (!promesaEjemplo) {
      promesaEjemplo = new Promise(function (ok, mal) {
        var s = document.createElement("script");
        s.src = "datos-ejemplo/ejemplo.js";
        s.onload = function () { global.DATOS_EJEMPLO ? ok(global.DATOS_EJEMPLO) : mal(new Error("ejemplo.js vacío")); };
        s.onerror = function () { mal(new Error("No se pudo cargar ejemplo.js")); };
        document.head.appendChild(s);
      });
      promesaEjemplo.catch(function () { promesaEjemplo = null; });
    }
    return promesaEjemplo.then(function (d) { return [d.items, d.config]; });
  }

  function etiquetaGuardado(ms) {
    var c = cuando(new Date(ms));
    return c.hoy ? "de las " + c.hora : "del " + c.fecha + " a las " + c.hora;
  }

  function cargar() {
    if (cargando) return;
    cargando = true;
    ultimoIntento = Date.now();
    ui.btn.disabled = true;
    ui.btn.textContent = "Actualizando…";

    var pCfg = CONFIG_URL
      ? traer(CONFIG_URL).catch(function (e) { console.warn(e); return null; })
      : Promise.resolve(null);

    Promise.all([traer(ITEMS_URL), pCfg])
      .catch(function (err) {
        if (DEMO && !SIMULAR_SIN_RED && location.protocol === "file:") return traerEjemplo();
        throw err;
      })
      .then(function (res) {
        var anterior = leerGuardado();
        var cfgTxt = res[1] != null ? res[1] : (anterior ? anterior.config : null);
        var datos = procesar(res[0], cfgTxt);
        guardar({ items: res[0], config: cfgTxt, savedAt: Date.now() });
        mostrar(datos);
        avisar("");
      })
      .catch(function (err) {
        console.error(err);
        var guardado = leerGuardado();
        var sinRed = !navigator.onLine || err.name === "TypeError" || err.name === "AbortError";
        var causa = sinRed ? "Sin conexión" : "No pudimos actualizar la lista";
        if (guardado) {
          try {
            mostrar(procesar(guardado.items, guardado.config));
            avisar(causa + ", mostrando la última lista guardada " + etiquetaGuardado(guardado.savedAt) + ".");
            return;
          } catch (e) { console.error(e); }
        }
        if (hayLista) {
          avisar(causa + ". Intenta de nuevo en un rato.");
        } else {
          avisar("");
          mostrarError();
        }
      })
      .then(function () {
        cargando = false;
        ui.btn.disabled = false;
        ui.btn.textContent = "Actualizar";
      });
  }

  /* ---------- Inicio ---------- */
  ui.demo.hidden = !DEMO;
  if (CFG["NOMBRE_CAMPAÑA"]) ui.titulo.textContent = document.title = CFG["NOMBRE_CAMPAÑA"];
  ui.btn.addEventListener("click", function () { cargar(); });

  // Con mala señal, mostrar de inmediato lo último guardado mientras llega lo nuevo.
  var previo = leerGuardado();
  if (previo) {
    try { mostrar(procesar(previo.items, previo.config)); ui.lista.setAttribute("aria-busy", "true"); }
    catch (e) { /* datos guardados inválidos: se ignoran */ }
  }
  cargar();

  setInterval(function () {
    if (document.visibilityState === "visible") cargar();
  }, REFRESH_MS);

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && Date.now() - ultimoIntento >= REFRESH_MS) cargar();
  });
  global.addEventListener("online", function () { cargar(); });

  if ("serviceWorker" in navigator && /^https?:$/.test(location.protocol)) {
    global.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function (e) { console.warn("Service worker:", e); });
    });
  }
})(typeof window !== "undefined" ? window : globalThis);
