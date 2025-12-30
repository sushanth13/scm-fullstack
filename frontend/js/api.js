const BASE = "http://127.0.0.1:8000/api";

/* Always read the correct key */
function getToken() {
    return localStorage.getItem("access_token");
}

function authHeaders() {
    const token = getToken();
    return {
        "Content-Type": "application/json",
        "Authorization": token ? `Bearer ${token}` : ""
    };
}

// ---------- GET ----------
async function apiGet(path) {
    const res = await fetch(BASE + path, {
        headers: authHeaders()
    });

    if (res.status === 401) {
        localStorage.removeItem("access_token");
        window.location.href = "login.html";
        return null;
    }

    return res.json();
}

// ---------- POST ----------
async function apiPost(path, data) {
    const res = await fetch(BASE + path, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(data)
    });

    if (res.status === 401) {
        localStorage.removeItem("access_token");
        window.location.href = "login.html";
        return null;
    }

    return res.json();
}


