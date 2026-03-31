(function () {
  const STORAGE_KEY = "sidebar_collapsed";

  function syncActiveNav() {
    const currentPage = window.location.pathname.split("/").pop() || "dashboard.html";
    document.querySelectorAll(".nav-menu .nav-item").forEach((link) => {
      const href = link.getAttribute("href");
      const isCurrent = !!href && href === currentPage;
      link.classList.toggle("active", isCurrent);
      if (isCurrent) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  }

  async function syncAdminLink() {
    const adminLink = document.getElementById("adminLink");
    if (!adminLink) {
      return;
    }

    const token = sessionStorage.getItem("access_token") || localStorage.getItem("access_token");
    if (!token || typeof window.apiGet !== "function") {
      adminLink.style.display = "none";
      return;
    }

    try {
      const me = await window.apiGet("/auth/me");
      adminLink.style.display = me?.role === "admin" ? "flex" : "none";
    } catch (error) {
      adminLink.style.display = "none";
    } finally {
      syncActiveNav();
    }
  }

  function applySidebarState(collapsed) {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    document.querySelectorAll(".sidebar-toggle").forEach((button) => {
      button.setAttribute("aria-expanded", String(!collapsed));
      button.setAttribute("title", collapsed ? "Expand sidebar" : "Collapse sidebar");
    });
  }

  function initSidebar() {
    syncActiveNav();
    const collapsed = localStorage.getItem(STORAGE_KEY) === "1";
    applySidebarState(collapsed);

    document.querySelectorAll(".sidebar-toggle").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const next = !document.body.classList.contains("sidebar-collapsed");
        localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
        applySidebarState(next);
      });
    });

    void syncAdminLink();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSidebar);
  } else {
    initSidebar();
  }
})();
