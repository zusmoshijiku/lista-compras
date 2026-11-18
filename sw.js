/*
 * Service worker mínimo: permite que la página abra sin señal.
 * Estrategia "primero la red": siempre intenta traer lo más nuevo y, si no hay
 * conexión, usa la última copia guardada. Solo guarda archivos de este mismo
 * sitio; el CSV de Google lo maneja app.js con localStorage.
 */
var CACHE = "colecta-v1";
var BASE = ["./", "index.html", "style.css", "app.js", "config.js"];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(BASE); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (keys) { return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); })); })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  var url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  // Los CSV no se guardan aquí: app.js decide si mostrar la copia guardada y avisa.
  if (/\.csv$/i.test(url.pathname)) return;
  // Se guarda sin parámetros (?s=, ?_=) para no llenar el caché de copias.
  var clave = url.origin + url.pathname;
  e.respondWith(
    fetch(req)
      .then(function (res) {
        if (res.ok) {
          var copia = res.clone();
          caches.open(CACHE).then(function (c) { return c.put(clave, copia); });
        }
        return res;
      })
      .catch(function () {
        return caches.match(clave).then(function (r) {
          return r || (req.mode === "navigate" ? caches.match("./") : Response.error());
        });
      })
  );
});
