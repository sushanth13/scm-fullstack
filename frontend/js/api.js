const BASE = "http://127.0.0.1:8000/api";

function getToken() {
  return localStorage.getItem("access_token");
}

async function apiGet(path) {
  const token = getToken();

  if (!token) {
    window.location.href = "login.html";
    return null;
  }

  const res = await fetch(BASE + path, {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });

  if (res.status === 401) {
    localStorage.removeItem("access_token");
    window.location.href = "login.html";
    return null;
  }

  return res.json();
}

async function apiPost(path, data) {
  const token = getToken();

  if (!token) {
    window.location.href = "login.html";
    return null;
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
    window.location.href = "login.html";
    return null;
  }

  return res.json();
}


