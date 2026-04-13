(function () {
  function resolveElement(target) {
    if (!target) return null;
    if (typeof target === "string") {
      return document.querySelector(target);
    }
    return target;
  }

  function createTablePaginator(options) {
    const tbody = resolveElement(options.tbody);
    const prevButton = resolveElement(options.prevButton);
    const nextButton = resolveElement(options.nextButton);
    const statusNode = resolveElement(options.statusNode);
    const metaNode = resolveElement(options.metaNode);
    const pageSize = Math.max(1, Number(options.pageSize) || 10);
    const defaultEmptyMessage = options.emptyMessage || "No records found.";

    const state = {
      page: 1,
      rows: [],
      emptyMessage: defaultEmptyMessage,
    };

    function getTotalPages() {
      return Math.max(1, Math.ceil(state.rows.length / pageSize));
    }

    function clampPage() {
      state.page = Math.min(Math.max(state.page, 1), getTotalPages());
    }

    function setMeta(total, start, end) {
      if (!metaNode) return;
      metaNode.textContent = total === 0
        ? "Showing 0-0 of 0"
        : `Showing ${start}-${end} of ${total}`;
    }

    function setStatus(totalPages) {
      if (!statusNode) return;
      statusNode.textContent = `Page ${state.page} of ${totalPages}`;
    }

    function setButtons(totalPages) {
      if (prevButton) prevButton.disabled = state.page <= 1;
      if (nextButton) nextButton.disabled = state.page >= totalPages;
    }

    function render() {
      if (!tbody) return;

      clampPage();
      const totalPages = getTotalPages();
      const totalRows = state.rows.length;

      if (totalRows === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="${options.colspan}" style="text-align:center;">${state.emptyMessage}</td>
          </tr>
        `;
        setMeta(0, 0, 0);
        setStatus(1);
        setButtons(1);
        return;
      }

      const startIndex = (state.page - 1) * pageSize;
      const pageRows = state.rows.slice(startIndex, startIndex + pageSize);
      const html = pageRows
        .map((row, index) => options.renderRow(row, startIndex + index))
        .join("");

      tbody.innerHTML = html;
      setMeta(totalRows, startIndex + 1, startIndex + pageRows.length);
      setStatus(totalPages);
      setButtons(totalPages);
    }

    function setRows(rows, settings = {}) {
      state.rows = Array.isArray(rows) ? rows : [];
      state.emptyMessage = settings.emptyMessage || defaultEmptyMessage;

      if (settings.resetPage) {
        state.page = 1;
      }

      clampPage();
      render();
    }

    function setPage(page) {
      state.page = page;
      render();
    }

    if (prevButton) {
      prevButton.addEventListener("click", () => setPage(state.page - 1));
    }

    if (nextButton) {
      nextButton.addEventListener("click", () => setPage(state.page + 1));
    }

    render();

    return {
      render,
      setPage,
      setRows,
      getPage() {
        return state.page;
      },
      getRows() {
        return state.rows.slice();
      },
    };
  }

  window.createTablePaginator = createTablePaginator;
})();
