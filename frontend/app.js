const API_BASE = "http://127.0.0.1:5000";

function qs(sel) {
  return document.querySelector(sel);
}

function setStatus(_text, _isError = false) {}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "include",
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = body?.error ? String(body.error) : `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return body;
}

async function refreshStatus() {
  try {
    await api("/api/me");
  } catch (e) {
    // If a user hits /app or /admin without a session, go to login silently.
    window.location.href = "/";
  }
}

async function loadFarmerDashboard() {
  // Tasks
  const tasksTbody = qs("#tasksTable tbody");
  if (tasksTbody) {
    const tasks = await api("/api/farmer/tasks");
    tasksTbody.innerHTML =
      tasks.length === 0
        ? `<tr><td colspan="5" class="muted">No tasks yet.</td></tr>`
        : tasks
            .map(
              (t) => `<tr>
  <td>
    <input type="checkbox" data-task-done="${escapeHtml(t.id)}" ${t.status === "done" ? "checked" : ""} />
  </td>
  <td>${escapeHtml(t.title)}</td>
  <td>${escapeHtml(t.status)}</td>
  <td>${escapeHtml(t.assigned_at || "-")}</td>
  <td>${escapeHtml(t.description || "")}</td>
</tr>`
            )
            .join("");
  }

  // Requests list
  const reqTbody = qs("#requestsTable tbody");
  if (reqTbody) {
    const reqs = await api("/api/farmer/requests");
    reqTbody.innerHTML =
      reqs.length === 0
        ? `<tr><td colspan="4" class="muted">No requests yet.</td></tr>`
        : reqs
            .map(
              (r) => `<tr>
  <td>${escapeHtml(r.subject)}</td>
  <td>${escapeHtml(r.status)}</td>
  <td>${escapeHtml(r.created_at)}</td>
  <td>${escapeHtml(r.message)}</td>
</tr>`
            )
            .join("");
  }

  // Inventory list
  const invTbody = qs("#inventoryTable tbody");
  if (invTbody) {
    const inv = await api("/api/farmer/inventory");
    invTbody.innerHTML =
      inv.length === 0
        ? `<tr><td colspan="4" class="muted">No inventory yet.</td></tr>`
        : inv
            .map(
              (i) => `<tr>
  <td>${escapeHtml(i.seed_type)}</td>
  <td>
    <input
      data-inv-qty
      data-inv-id="${escapeHtml(i.id)}"
      type="number"
      min="0"
      step="1"
      value="${escapeHtml(i.quantity)}"
      style="width: 120px"
    />
  </td>
  <td>${escapeHtml(i.updated_at)}</td>
  <td class="row">
    <button class="btn secondary" type="button" data-inv-save="${escapeHtml(i.id)}">Save</button>
    <button class="btn secondary" type="button" data-inv-del="${escapeHtml(i.id)}">Delete</button>
  </td>
</tr>`
            )
            .join("");
  }

  // Farm status form values
  const fsForm = qs("#farmStatusForm");
  if (fsForm) {
    const status = await api("/api/farmer/farm-status");
    fsForm.elements.health.value = status.health || "good";
    fsForm.elements.crop_type.value = status.crop_type || "";
    fsForm.elements.moisture_percent.value = status.moisture_percent ?? 0;
  }
}

async function loadAdminDashboard() {
  const farmers = await api("/api/admin/farmers");

  const farmerSelect = qs("#farmerSelect");
  if (farmerSelect) {
    farmerSelect.innerHTML =
      farmers.length === 0
        ? `<option value="">No farmers yet</option>`
        : farmers
            .map((f) => `<option value="${escapeHtml(f.id)}">${escapeHtml(f.name)} (${escapeHtml(f.email)})</option>`)
            .join("");
  }

  const farmersTbody = qs("#farmersTable tbody");
  if (farmersTbody) {
    farmersTbody.innerHTML =
      farmers.length === 0
        ? `<tr><td colspan="3" class="muted">No farmers yet.</td></tr>`
        : farmers
            .map(
              (f) => `<tr>
  <td>${escapeHtml(f.name)}</td>
  <td>${escapeHtml(f.email)}</td>
  <td>${escapeHtml(f.created_at)}</td>
</tr>`
            )
            .join("");
  }

  const reqTbody = qs("#adminRequestsTable tbody");
  if (reqTbody) {
    const reqs = await api("/api/admin/requests");
    reqTbody.innerHTML =
      reqs.length === 0
        ? `<tr><td colspan="6" class="muted">No requests yet.</td></tr>`
        : reqs
            .map(
              (r) => `<tr>
  <td><input type="checkbox" data-req-done="${escapeHtml(r.id)}" /></td>
  <td>${escapeHtml(r.farmer_name)} (${escapeHtml(r.farmer_email)})</td>
  <td>${escapeHtml(r.subject)}</td>
  <td>${escapeHtml(r.status)}</td>
  <td>${escapeHtml(r.created_at)}</td>
  <td>${escapeHtml(r.message)}</td>
</tr>`
            )
            .join("");
  }

  const fsTbody = qs("#farmStatusTable tbody");
  if (fsTbody) {
    const statuses = await api("/api/admin/farm-status");
    fsTbody.innerHTML =
      statuses.length === 0
        ? `<tr><td colspan="5" class="muted">No farmers yet.</td></tr>`
        : statuses
            .map(
              (s) => `<tr>
  <td>${escapeHtml(s.farmer_name)} (${escapeHtml(s.farmer_email)})</td>
  <td>${escapeHtml(s.health || "-")}</td>
  <td>${escapeHtml(s.crop_type || "")}</td>
  <td>${escapeHtml(s.moisture_percent != null ? `${s.moisture_percent}%` : "-")}</td>
  <td>${escapeHtml(s.updated_at || "-")}</td>
</tr>`
            )
            .join("");
  }
}

async function init() {
  // Health check
  try {
    await api("/api/health", { method: "GET" });
  } catch (e) {
    // no notifications
    return;
  }

  const registerForm = qs("#registerForm");
  if (registerForm) {
    registerForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(registerForm);
      try {
        const user = await api("/api/register", {
          method: "POST",
          body: JSON.stringify({
            name: fd.get("name"),
            email: fd.get("email"),
            password: fd.get("password"),
          }),
        });
      } catch (e) {
        // no notifications
      }
    });
  }

  const loginForm = qs("#loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(loginForm);
      const loginError = qs("#loginError");
      if (loginError) loginError.textContent = "";
      try {
        const user = await api("/api/login", {
          method: "POST",
          body: JSON.stringify({
            email: fd.get("email"),
            password: fd.get("password"),
          }),
        });
        // Redirect based on server-side role from DB
        if (user?.role === "admin") {
          window.location.href = "/admin";
        } else {
          window.location.href = "/app";
        }
      } catch (e) {
        if (loginError) loginError.textContent = "there is no user with this passsword";
      }
    });
  }

  const meBtn = qs("#meBtn");
  if (meBtn) meBtn.addEventListener("click", refreshStatus);

  const logoutBtn = qs("#logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await api("/api/logout", { method: "POST", body: JSON.stringify({}) });
        window.location.href = "/";
      } catch (e) {
        // no notifications
      }
    });
  }

  if (qs("#me")) {
    await refreshStatus();
  }

  // Farmer dashboard interactions
  const requestForm = qs("#requestForm");
  if (requestForm) {
    requestForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(requestForm);
      await api("/api/farmer/requests", {
        method: "POST",
        body: JSON.stringify({ subject: fd.get("subject"), message: fd.get("message") }),
      });
      requestForm.reset();
      await loadFarmerDashboard();
    });
  }

  const inventoryForm = qs("#inventoryForm");
  if (inventoryForm) {
    inventoryForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(inventoryForm);
      await api("/api/farmer/inventory", {
        method: "POST",
        body: JSON.stringify({
          seed_type: fd.get("seed_type"),
          quantity: Number(fd.get("quantity")),
        }),
      });
      inventoryForm.reset();
      await loadFarmerDashboard();
    });
  }

  const farmStatusForm = qs("#farmStatusForm");
  if (farmStatusForm) {
    farmStatusForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(farmStatusForm);
      const btn = farmStatusForm.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
      try {
        await api("/api/farmer/farm-status", {
          method: "PUT",
          body: JSON.stringify({
            health: fd.get("health"),
            crop_type: fd.get("crop_type"),
            moisture_percent: Number(fd.get("moisture_percent")),
          }),
        });
        await loadFarmerDashboard();
      } catch (e) {
        // no notifications
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }

  if (qs("#tasksTable") || qs("#inventoryTable") || qs("#requestsTable") || qs("#farmStatusForm")) {
    await loadFarmerDashboard();
  }

  // Farmer: mark task done
  const tasksTable = qs("#tasksTable");
  if (tasksTable) {
    tasksTable.addEventListener("change", async (ev) => {
      const t = ev.target;
      if (!(t instanceof HTMLInputElement)) return;
      const taskId = t.getAttribute("data-task-done");
      if (!taskId) return;
      if (!t.checked) {
        // Keep it simple: only support marking done, not un-done.
        t.checked = true;
        return;
      }
      await api(`/api/farmer/tasks/${taskId}/done`, { method: "POST", body: JSON.stringify({}) });
      await loadFarmerDashboard();
    });
  }

  // Inventory actions (edit/delete)
  const inventoryTable = qs("#inventoryTable");
  if (inventoryTable) {
    inventoryTable.addEventListener("click", async (ev) => {
      const t = ev.target;
      if (!(t instanceof HTMLElement)) return;

      const saveId = t.getAttribute("data-inv-save");
      if (saveId) {
        const input = inventoryTable.querySelector(`input[data-inv-qty][data-inv-id="${CSS.escape(saveId)}"]`);
        const qty = input ? Number(input.value) : NaN;
        await api(`/api/farmer/inventory/${saveId}`, {
          method: "PUT",
          body: JSON.stringify({ quantity: qty }),
        });
        await loadFarmerDashboard();
        return;
      }

      const delId = t.getAttribute("data-inv-del");
      if (delId) {
        if (!window.confirm("Delete this inventory item?")) return;
        await api(`/api/farmer/inventory/${delId}`, { method: "DELETE" });
        await loadFarmerDashboard();
      }
    });
  }

  const assignTaskForm = qs("#assignTaskForm");
  if (assignTaskForm) {
    assignTaskForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(assignTaskForm);
      await api("/api/admin/tasks", {
        method: "POST",
        body: JSON.stringify({
          farmer_id: Number(fd.get("farmer_id")),
          title: fd.get("title"),
          description: fd.get("description"),
        }),
      });
      assignTaskForm.reset();
      await loadAdminDashboard();
    });
  }

  if (qs("#farmersTable") || qs("#adminRequestsTable") || qs("#farmStatusTable")) {
    await loadAdminDashboard();
  }

  // Admin: mark request done (checkbox)
  const adminRequestsTable = qs("#adminRequestsTable");
  if (adminRequestsTable) {
    adminRequestsTable.addEventListener("change", async (ev) => {
      const t = ev.target;
      if (!(t instanceof HTMLInputElement)) return;
      const reqId = t.getAttribute("data-req-done");
      if (!reqId) return;
      if (!t.checked) return;
      await api(`/api/admin/requests/${reqId}/done`, { method: "POST", body: JSON.stringify({}) });
      await loadAdminDashboard();
    });
  }
}

init();
