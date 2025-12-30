const BASE = "http://127.0.0.1:8000/api";

function getToken() {
  return localStorage.getItem("access_token"); // ✅ FIXED
}

function authHeaders() {
  const token = getToken();
  return {
    "Authorization": `Bearer ${token}` // ✅ FIXED
  };
}

// ============================
// GET request
// ============================
async function apiGet(path) {
  const token = getToken();

  if (!token) {
    window.location.replace("login.html");
    return;
  }

  const res = await fetch(BASE + path, {
    headers: authHeaders()
  });

  if (res.status === 401) {
    localStorage.removeItem("access_token");
    window.location.replace("login.html");
    return;
  }

  return res.json();
}

// ============================
// POST request
// ============================
async function apiPost(path, data) {
  const token = getToken();

  if (!token) {
    window.location.replace("login.html");
    return;
  }

  const res = await fetch(BASE + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(data)
  });

  if (res.status === 401) {
    localStorage.removeItem("access_token");
    window.location.replace("login.html");
    return;
  }

  return res.json();
}
