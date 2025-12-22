const BASE = "http://127.0.0.1:8000/api";


function token() {
    return localStorage.getItem("token");
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + localStorage.getItem("token")
  };
}

// GET request
async function apiGet(path) {
  const res = await fetch(BASE + path, { headers: authHeaders() });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.replace("login.html");
    return;
  }
  return res.json();
}

// POST request
async function apiPost(path, data) {
    const res = await fetch(BASE + path, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(data)
    });

    if (res.status === 401) {
        localStorage.removeItem("token");
        window.location.href = "login.html";
        return;
    }

    return res.json();
}
