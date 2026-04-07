const BASE = "/api";


function getToken() { 
  return sessionStorage.getItem("access_token") || localStorage.getItem("access_token"); 
}

function clearToken() {
  sessionStorage.removeItem("access_token");
  localStorage.removeItem("access_token");
}

function isPrivilegedRole(role) {
  return role === "admin" || role === "super_admin";
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
    clearToken();
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
    clearToken();
    window.location.href = "login.html";
    return null;
  }

  return res.json();
}
