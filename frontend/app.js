const API_BASE = "http://127.0.0.1:5000";

function qs(sel) {
  return document.querySelector(sel);
}

function setStatus(text, isError = false) {
  const el = qs("#status") || qs("#me");
  if (!el) return;
  el.textContent = text;
  el.classList.toggle("error", isError);
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
    const me = await api("/api/me");
    setStatus(JSON.stringify({ authenticated: true, me }, null, 2));
  } catch (e) {
    setStatus(JSON.stringify({ authenticated: false, error: e.message }, null, 2), true);
  }
}

async function init() {
  // Health check
  try {
    await api("/api/health", { method: "GET" });
  } catch (e) {
    setStatus(
      `Backend not reachable.\n\n- Start Flask at ${API_BASE}\n- Then refresh\n\nError: ${e.message}`,
      true
    );
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
        setStatus(JSON.stringify({ registered: true, user }, null, 2));
      } catch (e) {
        setStatus(JSON.stringify({ registered: false, error: e.message }, null, 2), true);
      }
    });
  }

  const loginForm = qs("#loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(loginForm);
      try {
        const user = await api("/api/login", {
          method: "POST",
          body: JSON.stringify({
            email: fd.get("email"),
            password: fd.get("password"),
          }),
        });
        setStatus(JSON.stringify({ loggedIn: true, user }, null, 2));
      } catch (e) {
        setStatus(JSON.stringify({ loggedIn: false, error: e.message }, null, 2), true);
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
        setStatus(JSON.stringify({ loggedOut: true }, null, 2));
      } catch (e) {
        setStatus(JSON.stringify({ loggedOut: false, error: e.message }, null, 2), true);
      }
    });
  }

  await refreshStatus();
}

init();
