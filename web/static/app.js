/* GhostTrack frontend. All data is assigned via DOM text nodes (never innerHTML). */
"use strict";
(() => {
  const mode = document.body.dataset.mode;
  const $ = (selector) => document.querySelector(selector);
  const csrfState = { token: "" };
  const tools = {
    ip: { title: "IP intelligence", number: "01", label: "PUBLIC IP ADDRESS", placeholder: "e.g. 8.8.8.8", desc: "Approximate geographical and network details for globally routable IP addresses." },
    phone: { title: "Phone metadata", number: "02", label: "PHONE NUMBER", placeholder: "e.g. +60123456789", desc: "Regional numbering-plan metadata. This is not live device location." },
    username: { title: "Username discovery", number: "03", label: "PUBLIC USERNAME", placeholder: "e.g. octocat", desc: "Browse public profile links with conservative account-verification statuses." }
  };

  async function api(path, data, protectedAdmin = false) {
    const options = { cache: "no-store", credentials: "same-origin" };
    if (data !== undefined) {
      options.method = "POST";
      options.headers = { "Content-Type": "application/json", "X-GhostTrack-UI": "1" };
      if (protectedAdmin) options.headers["X-CSRF-Token"] = csrfState.token;
      options.body = JSON.stringify(data);
    }
    let response;
    try { response = await fetch(path, options); }
    catch (_) { throw Error("Cannot connect to the GhostTrack server."); }
    let body;
    try { body = await response.json(); }
    catch (_) { throw Error("Server returned an unexpected response."); }
    if (!response.ok) throw Error(typeof body.detail === "string" ? body.detail : "Request failed.");
    return body;
  }

  function clear(node) { node.replaceChildren(); }
  function el(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = String(value);
    return node;
  }
  function readable(key) { return key.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase()); }
  function displayResults(target, result) {
    clear(target);
    target.className = "result-body";
    if (result.profiles) {
      for (const profile of result.profiles) {
        const row = el("div", "result-row");
        row.append(el("span", "result-key", profile.platform));
        const right = el("div", "result-value");
        const link = el("a", "", profile.url);
        // Links originate from server-controlled HTTPS URL templates.
        if (typeof profile.url === "string" && profile.url.startsWith("https://")) {
          link.href = profile.url; link.target = "_blank"; link.rel = "noopener noreferrer";
          right.append(link);
        }
        right.append(el("div", "platform-status " + profile.status, profile.status.replaceAll("_", " ")));
        row.append(right); target.append(row);
      }
      target.append(el("div", "result-note", result.note));
      return;
    }
    function row(key, value) {
      if (value === null || value === undefined || value === "") return;
      if (key === "note") { target.append(el("div", "result-note", value)); return; }
      if (typeof value === "object" && !Array.isArray(value)) {
        for (const [nestedKey, nestedValue] of Object.entries(value)) row(key + " · " + nestedKey, nestedValue);
        return;
      }
      const container = el("div", "result-row"), label = el("span", "result-key", readable(key)), right = el("span", "result-value");
      if (key === "map_url" && typeof value === "string" && value.startsWith("https://www.google.com/maps/")) {
        const anchor = el("a", "", "Open approximate map ↗");
        anchor.href = value; anchor.target = "_blank"; anchor.rel = "noopener noreferrer";
        right.append(anchor);
      } else right.textContent = Array.isArray(value) ? value.join(", ") : String(value);
      container.append(label, right);
      target.append(container);
    }
    for (const [key, value] of Object.entries(result)) row(key, value);
  }
  function showError(target, message) {
    target.className = "empty error-text";
    target.textContent = message;
  }

  if (mode === "public") {
    let selected = "ip";
    function select(tool) {
      selected = tool;
      const current = tools[tool];
      $("#tool-title").textContent = current.title;
      $("#module-number").textContent = current.number;
      $("#tool-desc").textContent = current.desc;
      $("#lookup-label").textContent = current.label;
      $("#lookup-value").placeholder = current.placeholder;
      $("#lookup-value").value = "";
      $("#region-wrap").hidden = tool !== "phone";
      $("#username-wrap").hidden = tool !== "username";
      $("#results-content").className = "empty";
      $("#results-content").textContent = "Enter a value to begin.";
      $("#result-status").textContent = "AWAITING INPUT";
      document.querySelectorAll("[data-tool]").forEach(button => {
        button.classList.toggle("active", button.dataset.tool === tool);
        button.setAttribute("aria-pressed", String(button.dataset.tool === tool));
      });
    }
    document.querySelectorAll("[data-tool]").forEach(b => b.addEventListener("click", () => select(b.dataset.tool)));
    async function checkStatus() {
      const notice = $("#availability");
      try {
        const status = await api("/api/status");
        $("#workspace").hidden = !status.public_enabled;
        notice.className = status.public_enabled ? "notice ok" : "notice";
        notice.textContent = status.public_enabled
          ? "● Public lookups are enabled · 30 requests/minute per client connection"
          : "Public searches are currently disabled by the administrator.";
        $("#system-indicator").textContent = status.public_enabled ? "● ONLINE" : "● DISABLED";
      } catch (err) {
        $("#workspace").hidden = true;
        notice.className = "notice error"; notice.textContent = err.message;
      }
    }
    $("#lookup-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = $("#lookup-submit"), target = $("#results-content");
      button.disabled = true; $("#result-status").textContent = "RUNNING";
      target.className = "empty"; target.textContent = "Fetching public metadata…";
      try {
        const response = await api("/api/lookup/" + selected, {
          value: $("#lookup-value").value.trim(),
          region: $("#region").value,
          check: $("#check-profiles").checked
        });
        displayResults(target, response.result); $("#result-status").textContent = "COMPLETE";
      } catch (err) {
        showError(target, err.message); $("#result-status").textContent = "ERROR";
        if (/disabled/i.test(err.message)) checkStatus();
      } finally { button.disabled = false; }
    });
    select("ip"); checkStatus();
  }

  if (mode === "admin") {
    const loginSection = $("#login-section"), dash = $("#admin-dashboard");
    function showLoggedIn(value) {
      loginSection.hidden = value; dash.hidden = !value; $("#logout").hidden = !value;
      if (!value) csrfState.token = "";
    }
    async function refresh() {
      const summary = await api("/api/admin/summary");
      $("#public-state").textContent = summary.public_enabled ? "Enabled" : "Disabled";
      const toggle = $("#toggle-public");
      toggle.disabled = false; toggle.textContent = summary.public_enabled ? "Disable public lookups" : "Enable public lookups";
      const usage = $("#usage-summary"); clear(usage);
      if (!summary.counts.length) { usage.textContent = "No lookups recorded yet."; return; }
      const aggregates = new Map();
      for (const item of summary.counts) {
        const key = item.interface + " · " + item.tool + " · " + item.outcome;
        aggregates.set(key, (aggregates.get(key) || 0) + item.count);
      }
      const grid = el("div", "usage-list");
      for (const [key, count] of aggregates) {
        const tile = el("div", "usage-stat");
        tile.append(el("strong", "", count), el("span", "", key));
        grid.append(tile);
      }
      usage.append(grid);
    }
    async function restore() {
      try {
        const result = await api("/api/admin/me");
        csrfState.token = result.csrf;
        showLoggedIn(true); await refresh();
      } catch (_) { showLoggedIn(false); }
    }
    $("#login-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      $("#login-message").textContent = "";
      try {
        const result = await api("/api/admin/login", { password: $("#admin-password").value });
        $("#admin-password").value = "";
        csrfState.token = result.csrf; showLoggedIn(true); await refresh();
      } catch (err) { $("#login-message").textContent = err.message; }
    });
    $("#logout").addEventListener("click", async () => {
      try { await api("/api/admin/logout", {}, true); }
      finally { showLoggedIn(false); }
    });
    $("#refresh-summary").addEventListener("click", () => refresh().catch(err => {
      $("#usage-summary").textContent = err.message;
    }));
    $("#toggle-public").addEventListener("click", async () => {
      const enabling = $("#public-state").textContent === "Disabled";
      const question = enabling
        ? "Enable public lookup requests? Only do so after reviewing your network exposure, TLS and rate limits."
        : "Disable all public lookup requests?";
      if (!window.confirm(question)) return;
      const toggle = $("#toggle-public"); toggle.disabled = true;
      try { await api("/api/admin/public-access", { enabled: enabling }, true); await refresh(); }
      catch (err) { window.alert(err.message); toggle.disabled = false; }
    });
    $("#admin-lookup-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const target = $("#admin-results"), tool = $("#admin-tool").value;
      target.textContent = "Running lookup…"; target.className = "empty";
      try {
        const data = await api("/api/lookup/" + tool, {
          value: tool === "my-ip" ? "-" : $("#admin-value").value.trim(),
          region: $("#admin-region").value,
          check: true
        }, true);
        displayResults(target, data.result); refresh().catch(() => {});
      } catch (err) { showError(target, err.message); }
    });
    restore();
  }
})();
