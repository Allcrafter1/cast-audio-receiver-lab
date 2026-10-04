// SPDX-License-Identifier: MPL-2.0
"use strict";
const translations = {
  de: {
    page_title: "Audio Lab · Speaker", language: "Sprache", title: "Deine Speaker.", subtitle: "Ausgaben verwalten. Feste Identitäten behalten.",
    outputs: "Konfigurierte Ausgaben", refresh: "Aktualisieren", outputs_hint: "Umbenennen oder Deaktivieren startet nur die betroffene Ausgabe neu bzw. beendet sie. Laufende Musik wird dabei unterbrochen.",
    local: "Lokale Ausgabe", local_loading: "Lokale Ausgabe wird geladen …", cast_name: "Cast-Name", add: "Hinzufügen",
    airplay: "AirPlay-Ziele", scan: "Netzwerk durchsuchen", airplay_hint: "Nur ausdrücklich ausgewählte Ziele werden importiert. Wähle den gewünschten Protokoll-Endpunkt; unbekannte Reverse-Bridges können nicht zuverlässig erkannt werden.",
    network: "Experimentelle Netzwerk-Ausgaben", network_hint: "DLNA und Sonos sind experimentell. Die Kompatibilität hängt vom Gerät ab. Neue Ausgaben bleiben zunächst deaktiviert.",
    dlna_devices: "DLNA-Geräte suchen", scan_dlna: "DLNA-Netzwerk durchsuchen", dlna_manual: "DLNA manuell", dlna_name: "DLNA-Name", description_url: "Gerätebeschreibung (URL, nicht nur IP)", add_dlna: "DLNA hinzufügen",
    sonos_name: "Sonos-Name", sonos_host: "Sonos-IP/Hostname", add_sonos: "Sonos hinzufügen",
    footer: "Experimentelle Software · „Prozess läuft“ ist noch keine Bestätigung für eine Cast-Verbindung oder hörbaren Ton. Pairing-Geheimnisse und Logs sind hier nicht abrufbar.",
    access_error: "Zugriff fehlgeschlagen. In Home Assistant bitte die App-Ansicht erneut öffnen.", request_error: "Anfrage fehlgeschlagen.", network_error: "Verbindung fehlgeschlagen. Bitte Netzwerk prüfen und erneut versuchen.",
    invalid_request: "Ungültige Konfiguration oder Anfrage.", operation_failed: "Vorgang fehlgeschlagen. Private Diagnosedaten sind nur lokal verfügbar.", not_found: "Die Ausgabe wurde nicht gefunden. Bitte aktualisieren.",
    discovery_expired: "Suchergebnis abgelaufen. Bitte erneut suchen.", scan_running: "Eine Suche läuft bereits.", scan_timeout: "Die Netzwerksuche hat zu lange gedauert. Bitte erneut versuchen.", dlna_unavailable: "Die DLNA-Unterstützung ist nicht verfügbar.", local_exists_error: "Diese lokale Ausgabe existiert bereits. Bitte die vorhandene Ausgabe verwenden.",
    state_running: "Prozess läuft", state_disabled: "Deaktiviert", state_starting: "Startet", state_backoff: "Neustart wird versucht", state_unknown: "Status unbekannt", process_status: "{state} · Neustarts: {count}",
    local_exists: "Die lokale Ausgabe ist bereits eingerichtet. Du kannst sie oben verwalten.", local_available: "Spielt auf diesem Linux-Rechner. Neue Ausgaben bleiben zunächst deaktiviert.", version: "Version {version}", no_routes: "Noch keine Ausgaben konfiguriert.",
    save_name: "Name speichern", restart_confirm: "Diese Ausgabe wird neu gestartet. Laufende Wiedergabe wird unterbrochen. Fortfahren?", disable: "Deaktivieren", enable: "Aktivieren", disable_confirm: "Wiedergabe auf dieser Ausgabe beenden?", enable_confirm: "Diese Ausgabe als Cast-Speaker starten?", delete: "Löschen", delete_confirm: "Speaker „{name}“ löschen? Laufende Wiedergabe wird beendet.",
    dlna_url_label: "DLNA-Gerätebeschreibungs-URL", save_dlna: "DLNA-Adresse speichern", dlna_url_hint: "Vollständige UPnP-Gerätebeschreibungs-URL inklusive Port und Pfad, nicht nur die IP-Adresse.",
    added: "Ausgabe hinzugefügt; noch deaktiviert.", network_added: "Experimentelle Ausgabe hinzugefügt; noch deaktiviert.", searching: "Suche {protocol}-Ziele …", import_name: "Name für importierten Speaker", imported: "Bereits importiert", import_disabled: "Deaktiviert importieren", import_done: "Importiert. Zum Aktivieren die konfigurierte Ausgabe verwenden.", found: "{count} Endpunkte gefunden. Auswahl ist 3 Minuten gültig."
  },
  en: {
    page_title: "Audio Lab · Speakers", language: "Language", title: "Your speakers.", subtitle: "Manage outputs. Keep their identities.",
    outputs: "Configured outputs", refresh: "Refresh", outputs_hint: "Renaming or disabling restarts or stops only that output. Its playback will be interrupted.",
    local: "Local output", local_loading: "Loading local output …", cast_name: "Cast name", add: "Add",
    airplay: "AirPlay targets", scan: "Scan network", airplay_hint: "Only explicitly selected targets are imported. Choose the protocol endpoint; unknown reverse bridges cannot be reliably detected.",
    network: "Experimental network outputs", network_hint: "DLNA and Sonos support is experimental. Compatibility depends on the device. New outputs start disabled.",
    dlna_devices: "Find DLNA devices", scan_dlna: "Scan DLNA network", dlna_manual: "Manual DLNA setup", dlna_name: "DLNA name", description_url: "Device description (URL, not just IP)", add_dlna: "Add DLNA",
    sonos_name: "Sonos name", sonos_host: "Sonos IP/hostname", add_sonos: "Add Sonos",
    footer: "Experimental software · A running process does not confirm a Cast connection or audible sound. Pairing secrets and logs are not available here.",
    access_error: "Access failed. In Home Assistant, please reopen the app view.", request_error: "Request failed.", network_error: "Connection failed. Please check your network and try again.",
    invalid_request: "Invalid configuration or request.", operation_failed: "Operation failed. Private diagnostics require local access.", not_found: "The output was not found. Please refresh.",
    discovery_expired: "Discovery expired. Please scan again.", scan_running: "A scan is already running.", scan_timeout: "Network discovery timed out. Please try again.", dlna_unavailable: "DLNA support is unavailable.", local_exists_error: "This local output already exists. Please use the existing output.",
    state_running: "Process running", state_disabled: "Disabled", state_starting: "Starting", state_backoff: "Retrying restart", state_unknown: "Unknown status", process_status: "{state} · Restarts: {count}",
    local_exists: "The local output is already configured. You can manage it above.", local_available: "Plays on this Linux machine. New outputs start disabled.", version: "Version {version}", no_routes: "No outputs configured yet.",
    save_name: "Save name", restart_confirm: "This output will restart and interrupt playback. Continue?", disable: "Disable", enable: "Enable", disable_confirm: "Stop playback on this output?", enable_confirm: "Start this output as a Cast speaker?", delete: "Delete", delete_confirm: "Delete speaker “{name}”? Playback will stop.",
    dlna_url_label: "DLNA device description URL", save_dlna: "Save DLNA address", dlna_url_hint: "Full UPnP device description URL including port and path, not just the IP address.",
    added: "Output added; still disabled.", network_added: "Experimental output added; still disabled.", searching: "Searching for {protocol} targets …", import_name: "Name for imported speaker", imported: "Already imported", import_disabled: "Import disabled", import_done: "Imported. Enable it in the configured outputs.", found: "{count} endpoints found. Selection is valid for 3 minutes."
  }
};
const languageKey = "cast-audio-language";
function initialLanguage() {
  try { const saved = localStorage.getItem(languageKey); if (saved === "de" || saved === "en") return saved; } catch (_) { /* Storage may be blocked in an iframe. */ }
  return (navigator.language || "en").toLowerCase().startsWith("de") ? "de" : "en";
}
let language = initialLanguage();
const t = (key, params = {}) => (translations[language][key] || translations.en[key] || translations[language].request_error).replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? ""));
const $ = id => document.getElementById(id);
const node = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
function text(n, key, params = {}) { n.dataset.i18n = key; n.dataset.i18nParams = JSON.stringify(params); n.textContent = t(key, params); return n; }
function label(n, key) { n.dataset.i18nAria = key; n.setAttribute("aria-label", t(key)); }
let notice = null;
function message(key, params = {}) { notice = key ? {key, params} : null; $("message").textContent = key ? t(key, params) : ""; }
class UiError extends Error { constructor(key) { super(t(key)); this.key = key; } }
const showError = error => message(error instanceof UiError ? error.key : "network_error");
function updateState(n, process) { n.dataset.process = JSON.stringify(process); n.textContent = status({process}); }
function applyLanguage() {
  document.documentElement.lang = language;
  document.title = t("page_title");
  document.querySelectorAll("[data-i18n]").forEach(n => { n.textContent = t(n.dataset.i18n, JSON.parse(n.dataset.i18nParams || "{}")); });
  document.querySelectorAll("[data-i18n-aria]").forEach(n => n.setAttribute("aria-label", t(n.dataset.i18nAria)));
  document.querySelectorAll("[data-process]").forEach(n => updateState(n, JSON.parse(n.dataset.process)));
  document.querySelectorAll("[data-language]").forEach(n => n.setAttribute("aria-pressed", String(n.dataset.language === language)));
  if (notice) message(notice.key, notice.params);
}
function setLanguage(value) {
  if (value !== "de" && value !== "en") return;
  language = value;
  try { localStorage.setItem(languageKey, value); } catch (_) { /* Switching still works without persistence. */ }
  applyLanguage();
}
let renderedConfig = "";
const configKey = routes => JSON.stringify(routes.map(({process, ...route}) => route));
async function api(path, method = "GET", body) {
  // HA Ingress needs its same-origin session cookie. Direct LAN access still
  // requires no login; never send credentials to a different origin.
  const response = await fetch(path.replace(/^\//, ""), {method, headers: {"Content-Type": "application/json"}, body: body === undefined ? undefined : JSON.stringify(body), credentials: "same-origin", cache: "no-store"});
  if (response.status === 401 || response.status === 403) throw new UiError("access_error");
  const data = await response.json();
  if (!response.ok) {
    const errors = {"Discovery expired; scan again": "discovery_expired", "Scan already running": "scan_running", "Discovery timed out": "scan_timeout", "DLNA discovery timed out": "scan_timeout", "DLNA dependency unavailable": "dlna_unavailable", "Diese lokale Ausgabe existiert bereits. Bitte die vorhandene Ausgabe verwenden.": "local_exists_error"};
    const statuses = {400: "invalid_request", 404: "not_found", 503: "operation_failed", 504: "scan_timeout"};
    throw new UiError(errors[data.error] || statuses[response.status] || "request_error");
  }
  return data;
}
function action(key, fn, secondary = false) {
  const button = text(node("button", "", secondary ? "secondary" : ""), key);
  button.onclick = async () => { button.disabled = true; message(""); try { await fn(); } catch (e) { showError(e); } finally { button.disabled = false; } };
  return button;
}
function status(route) {
  const key = "state_" + route.process.state;
  return t("process_status", {state: t(Object.hasOwn(translations.en, key) ? key : "state_unknown"), count: route.process.restarts || 0});
}
function renderRoutes(data) {
  renderedConfig = configKey(data.routes);
  const localExists = data.routes.some(route => route.backend === "mpv");
  $("add-local").disabled = localExists;
  $("local-name").disabled = localExists;
  text($("local-hint"), localExists ? "local_exists" : "local_available");
  text($("version"), "version", {version: data.version});
  $("routes").replaceChildren();
  if (!data.routes.length) $("routes").append(text(node("p", ""), "no_routes"));
  for (const route of data.routes) {
    const card = node("div", "", "route"), input = document.createElement("input");
    input.value = route.name; input.maxLength = 80; label(input, "cast_name");
    const state = node("div", "", "state"); state.dataset.state = route.id; updateState(state, route.process);
    card.append(input, action("save_name", async () => {
      if (input.value === route.name) return;
      if (route.enabled && !confirm(t("restart_confirm"))) return;
      await api("/api/routes/"+route.id, "PATCH", {name: input.value}); await refresh();
    }, true), action(route.enabled ? "disable" : "enable", async () => {
      if (!confirm(t(route.enabled ? "disable_confirm" : "enable_confirm"))) return;
      await api("/api/routes/"+route.id, "PATCH", {enabled: !route.enabled}); await refresh();
    }), action("delete", async () => {
      if (!confirm(t("delete_confirm", {name: route.name}))) return;
      await api("/api/routes/"+route.id, "DELETE", {}); await refresh();
    }, true), state, node("div", `${route.backend} · ID ${route.id}`, "meta"));
    if (route.target) card.append(node("div", `${route.target.host}:${route.target.port} · ${route.target.protocol}`, "meta"));
    if (route.backend === "dlna") {
      const address = document.createElement("input");
      address.value = route.target.description_url || "";
      label(address, "dlna_url_label");
      card.append(address, action("save_dlna", async () => {
        if (route.enabled && !confirm(t("restart_confirm"))) return;
        await api("/api/routes/" + route.id, "PATCH", {target: {description_url: address.value}});
        await refresh();
      }, true), text(node("p", "", "meta"), "dlna_url_hint"));
    }
    $("routes").append(card);
  }
}
async function refresh() { renderRoutes(await api("/api/routes")); }
document.querySelectorAll("[data-language]").forEach(button => { button.onclick = () => setLanguage(button.dataset.language); });
applyLanguage();
refresh().catch(showError);
$("refresh").onclick = () => refresh().catch(showError);
$("add-local").onclick = async () => { try { await api("/api/routes", "POST", {name: $("local-name").value, backend: "mpv"}); await refresh(); message("added"); } catch (e) { showError(e); } };
async function addNetwork(backend, name, target) {
  await api("/api/routes", "POST", {name, backend, target});
  await refresh(); message("network_added");
}
$("add-dlna").onclick = async () => { try { await addNetwork("dlna", $("dlna-name").value, {description_url: $("dlna-url").value}); } catch (e) { showError(e); } };
$("add-sonos").onclick = async () => { try { await addNetwork("sonos", $("sonos-name").value, {host: $("sonos-host").value}); } catch (e) { showError(e); } };
async function scanTargets(buttonId, containerId, endpoint, protocol) {
  $(buttonId).disabled = true; message("searching", {protocol});
  try {
    const result = await api(endpoint, "POST", {}); $(containerId).replaceChildren();
    for (const candidate of result.candidates) {
      const card = node("div", "", "route"), name = document.createElement("input");
      name.value = candidate.name; name.maxLength = 80; label(name, "import_name");
      const button = action(candidate.already_imported ? "imported" : "import_disabled", async () => {
        await api("/api/routes", "POST", {name: name.value, candidate_id: candidate.candidate_id});
        await refresh(); $(containerId).replaceChildren(); message("import_done");
      }); button.disabled = candidate.already_imported;
      card.append(name, node("div", `${candidate.target.host}:${candidate.target.port} · ${candidate.target.protocol}`, "meta"), button);
      $(containerId).append(card);
    }
    message("found", {count: result.candidates.length});
  } catch (e) { showError(e); } finally { $(buttonId).disabled = false; }
}
$("scan").onclick = () => scanTargets("scan", "candidates", "/api/scan", "AirPlay");
$("scan-dlna").onclick = () => scanTargets("scan-dlna", "dlna-candidates", "/api/scan/dlna", "DLNA");
setInterval(async () => {
  try { const data = await api("/api/routes");
    if (configKey(data.routes) !== renderedConfig && !$("routes").contains(document.activeElement)) renderRoutes(data);
    for (const route of data.routes) { const state = document.querySelector(`[data-state="${route.id}"]`); if (state) updateState(state, route.process); } }
  catch (e) { showError(e); }
}, 5000);
