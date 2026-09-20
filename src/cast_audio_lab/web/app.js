"use strict";
const $ = id => document.getElementById(id);
const node = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
const message = text => { $("message").textContent = text; };
let renderedConfig = "";
const configKey = routes => JSON.stringify(routes.map(({process, ...route}) => route));
async function api(path, method = "GET", body) {
  // HA Ingress needs its same-origin session cookie. Direct LAN access still
  // requires no login; never send credentials to a different origin.
  const response = await fetch(path.replace(/^\//, ""), {method, headers: {"Content-Type": "application/json"}, body: body === undefined ? undefined : JSON.stringify(body), credentials: "same-origin", cache: "no-store"});
  if (response.status === 401 || response.status === 403) throw new Error("Zugriff fehlgeschlagen. In Home Assistant bitte die App-Ansicht erneut öffnen.");
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Anfrage fehlgeschlagen");
  return data;
}
function action(label, fn, secondary = false) {
  const button = node("button", label, secondary ? "secondary" : "");
  button.onclick = async () => { button.disabled = true; message(""); try { await fn(); } catch (e) { message(e.message); } finally { button.disabled = false; } };
  return button;
}
function status(route) {
  const labels = {running:"Prozess läuft", disabled:"Deaktiviert", starting:"Startet", backoff:"Neustart wird versucht"};
  return `${labels[route.process.state] || route.process.state} · Neustarts: ${route.process.restarts || 0}`;
}
function renderRoutes(data) {
  renderedConfig = configKey(data.routes);
  const localExists = data.routes.some(route => route.backend === "mpv");
  $("add-local").disabled = localExists;
  $("local-name").disabled = localExists;
  $("local-hint").textContent = localExists ? "Die lokale Ausgabe ist bereits eingerichtet. Du kannst sie oben verwalten." : "Spielt auf diesem Linux-Rechner. Neue Ausgaben bleiben zunächst deaktiviert.";
  $("version").textContent = "Version " + data.version;
  $("routes").replaceChildren();
  if (!data.routes.length) $("routes").append(node("p", "Noch keine Ausgaben konfiguriert."));
  for (const route of data.routes) {
    const card = node("div", "", "route"), input = document.createElement("input");
    input.value = route.name; input.maxLength = 80; input.setAttribute("aria-label", "Cast-Name");
    const state = node("div", status(route), "state"); state.dataset.state = route.id;
    card.append(input, action("Name speichern", async () => {
      if (input.value === route.name) return;
      if (route.enabled && !confirm("Diese Ausgabe wird neu gestartet. Laufende Wiedergabe wird unterbrochen. Fortfahren?")) return;
      await api("/api/routes/"+route.id, "PATCH", {name: input.value}); await refresh();
    }, true), action(route.enabled ? "Deaktivieren" : "Aktivieren", async () => {
      if (!confirm(route.enabled ? "Wiedergabe auf dieser Ausgabe beenden?" : "Diese Ausgabe als Cast-Speaker starten?")) return;
      await api("/api/routes/"+route.id, "PATCH", {enabled: !route.enabled}); await refresh();
    }), action("Löschen", async () => {
      if (!confirm(`Speaker „${route.name}“ löschen? Laufende Wiedergabe wird beendet.`)) return;
      await api("/api/routes/"+route.id, "DELETE", {}); await refresh();
    }, true), state, node("div", `${route.backend} · ID ${route.id}`, "meta"));
    if (route.target) card.append(node("div", `${route.target.host}:${route.target.port} · ${route.target.protocol}`, "meta"));
    if (route.backend === "dlna") {
      const address = document.createElement("input");
      address.value = route.target.description_url || "";
      address.setAttribute("aria-label", "DLNA-Gerätebeschreibungs-URL");
      card.append(address, action("DLNA-Adresse speichern", async () => {
        if (route.enabled && !confirm("Diese Ausgabe wird neu gestartet. Fortfahren?")) return;
        await api("/api/routes/" + route.id, "PATCH", {target: {description_url: address.value}});
        await refresh();
      }, true), node("p", "Vollständige UPnP-Gerätebeschreibungs-URL inklusive Port und Pfad, nicht nur die IP-Adresse.", "meta"));
    }
    $("routes").append(card);
  }
}
async function refresh() { renderRoutes(await api("/api/routes")); }
refresh().catch(e => message(e.message));
$("refresh").onclick = () => refresh().catch(e => message(e.message));
$("add-local").onclick = async () => { try { await api("/api/routes", "POST", {name: $("local-name").value, backend: "mpv"}); await refresh(); message("Ausgabe hinzugefügt; noch deaktiviert."); } catch (e) { message(e.message); } };
async function addNetwork(backend, name, target) {
  await api("/api/routes", "POST", {name, backend, target});
  await refresh(); message("Experimentelle Ausgabe hinzugefügt; noch deaktiviert.");
}
$("add-dlna").onclick = async () => { try { await addNetwork("dlna", $("dlna-name").value, {description_url: $("dlna-url").value}); } catch (e) { message(e.message); } };
$("add-sonos").onclick = async () => { try { await addNetwork("sonos", $("sonos-name").value, {host: $("sonos-host").value}); } catch (e) { message(e.message); } };
async function scanTargets(buttonId, containerId, endpoint, label) {
  $(buttonId).disabled = true; message(`Suche ${label}-Ziele …`);
  try {
    const result = await api(endpoint, "POST", {}); $(containerId).replaceChildren();
    for (const candidate of result.candidates) {
      const card = node("div", "", "route"), name = document.createElement("input");
      name.value = candidate.name; name.maxLength = 80; name.setAttribute("aria-label", "Name für importierten Speaker");
      const button = action(candidate.already_imported ? "Bereits importiert" : "Deaktiviert importieren", async () => {
        await api("/api/routes", "POST", {name: name.value, candidate_id: candidate.candidate_id});
        await refresh(); $(containerId).replaceChildren(); message("Importiert. Zum Aktivieren die konfigurierte Ausgabe verwenden.");
      }); button.disabled = candidate.already_imported;
      card.append(name, node("div", `${candidate.target.host}:${candidate.target.port} · ${candidate.target.protocol}`, "meta"), button);
      $(containerId).append(card);
    }
    message(`${result.candidates.length} Endpunkte gefunden. Auswahl ist 3 Minuten gültig.`);
  } catch (e) { message(e.message); } finally { $(buttonId).disabled = false; }
}
$("scan").onclick = () => scanTargets("scan", "candidates", "/api/scan", "AirPlay");
$("scan-dlna").onclick = () => scanTargets("scan-dlna", "dlna-candidates", "/api/scan/dlna", "DLNA");
setInterval(async () => {
  try { const data = await api("/api/routes");
    if (configKey(data.routes) !== renderedConfig && !$("routes").contains(document.activeElement)) renderRoutes(data);
    for (const route of data.routes) { const state = document.querySelector(`[data-state="${route.id}"]`); if (state) state.textContent = status(route); } }
  catch (e) { message(e.message); }
}, 5000);
