const state = {
  category: "Student",
  keyword: "",
  searchTerms: [],
  searchItems: [],
  selectedItem: null,
  columnWeights: {},
  rowNormalized: true,
  allColumns: []
};

const elements = {
  statusMessage: document.getElementById("status-message"),
  keywordInput: document.getElementById("keyword-input"),
  searchButton: document.getElementById("search-button"),
  searchResults: document.getElementById("search-results"),
  goStep3Button: document.getElementById("go-step-3"),
  columnsContainer: document.getElementById("columns-container"),
  rowNormalized: document.getElementById("row-normalized"),
  runSimilarityButton: document.getElementById("run-similarity"),
  similarityResults: document.getElementById("similarity-results"),
  restartFlowButton: document.getElementById("restart-flow"),
  detailsModal: document.getElementById("details-modal"),
  detailsCloseButton: document.getElementById("details-close"),
  detailsContent: document.getElementById("details-content"),
  step1: document.getElementById("step-1"),
  step2: document.getElementById("step-2"),
  step3: document.getElementById("step-3"),
  step4: document.getElementById("step-4")
};

function truncateText(value, maxLength = 50) {
  const text = String(value ?? "");
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 3)}...`;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function parseSearchTerms(value) {
  return String(value ?? "")
    .trim()
    .split(/[\s\u3000]+/)
    .filter(Boolean);
}

function appendHighlightedText(container, text, keyword) {
  const rawText = String(text ?? "");
  const terms = parseSearchTerms(keyword);
  if (terms.length === 0) {
    container.textContent = rawText;
    return;
  }

  const uniqueTerms = [...new Set(terms.map((term) => term.toLowerCase()))];
  const pattern = new RegExp(
    `(${uniqueTerms
      .sort((left, right) => right.length - left.length)
      .map((term) => escapeRegExp(term))
      .join("|")})`,
    "ig"
  );
  const parts = rawText.split(pattern);

  parts.forEach((part) => {
    if (!part) {
      return;
    }

    if (uniqueTerms.includes(part.toLowerCase())) {
      const mark = document.createElement("mark");
      mark.textContent = part;
      container.appendChild(mark);
      return;
    }

    container.appendChild(document.createTextNode(part));
  });
}

function buildMatchedRows(item, keyword) {
  const terms = parseSearchTerms(keyword).map((term) => term.toLowerCase());
  if (terms.length === 0) {
    return [];
  }

  return Object.entries(item.data || {})
    .filter(([, value]) => {
      const text = String(value ?? "").toLowerCase();
      return terms.some((term) => text.includes(term));
    })
    .slice(0, 2);
}

function setRowNormalizedState(isEnabled) {
  state.rowNormalized = Boolean(isEnabled);
  elements.rowNormalized.checked = state.rowNormalized;
}

function openDetailsModal(item) {
  const data = item && item.data ? item.data : {};
  elements.detailsContent.innerHTML = "";

  Object.entries(data).forEach(([key, value]) => {
    const row = document.createElement("p");
    row.className = "modal-row";
    appendHighlightedText(row, `${key}: ${String(value)}`, state.keyword);
    elements.detailsContent.appendChild(row);
  });

  if (Object.keys(data).length === 0) {
    const empty = document.createElement("p");
    empty.className = "modal-row";
    empty.textContent = "詳細データがありません。";
    elements.detailsContent.appendChild(empty);
  }

  elements.detailsModal.classList.remove("is-hidden");
}

function closeDetailsModal() {
  elements.detailsModal.classList.add("is-hidden");
}

function createExpandIcon(item) {
  const icon = document.createElement("button");
  icon.type = "button";
  icon.className = "expand-icon";
  icon.textContent = "+";
  icon.title = "詳細を表示";
  icon.setAttribute("aria-label", "詳細を表示");
  icon.addEventListener("click", (event) => {
    event.stopPropagation();
    openDetailsModal(item);
  });
  return icon;
}

function setMessage(text, isError = false) {
  elements.statusMessage.textContent = text;
  elements.statusMessage.classList.toggle("is-error", isError);
}

function showUntilStep(stepNumber) {
  [elements.step1, elements.step2, elements.step3, elements.step4].forEach((section, index) => {
    section.classList.toggle("is-hidden", index + 1 > stepNumber);
  });
}

function resetDownstreamState() {
  state.searchItems = [];
  state.selectedItem = null;
  state.columnWeights = {};
  setRowNormalizedState(true);
  elements.searchResults.innerHTML = "";
  elements.columnsContainer.innerHTML = "";
  elements.similarityResults.innerHTML = "";
  elements.goStep3Button.disabled = true;
  showUntilStep(1);
}

async function fetchColumns() {
  const response = await fetch(`/api/columns?category=${encodeURIComponent(state.category)}`);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Failed to fetch columns");
  }
  state.allColumns = payload.columns;
  renderColumns();
}

function renderColumns() {
  elements.columnsContainer.innerHTML = "";
  state.allColumns.forEach((columnDefinition) => {
    const columnName = columnDefinition.name;
    const item = document.createElement("div");
    item.className = "slider-item";

    const text = document.createElement("span");
    text.className = "col-name";
    text.textContent = columnDefinition.label;

    const slider = document.createElement("input");
    slider.type = "range";
    slider.className = "weight-slider";
    slider.min = String(columnDefinition.min);
    slider.max = String(columnDefinition.max);
    slider.step = String(columnDefinition.step);
    slider.value = String(
      state.columnWeights[columnName] ?? columnDefinition.defaultWeight
    );

    const weightInput = document.createElement("input");
    weightInput.type = "number";
    weightInput.className = "weight-input";
    weightInput.min = String(columnDefinition.min);
    weightInput.max = String(columnDefinition.max);
    weightInput.step = String(columnDefinition.step);
    weightInput.value = String(
      state.columnWeights[columnName] ?? columnDefinition.defaultWeight
    );
    weightInput.title = `${columnDefinition.label} の係数`;

    const syncWeight = (nextValue) => {
      const parsed = Number.parseFloat(nextValue);
      const fallbackValue = Number(columnDefinition.defaultWeight);
      const safeValue = Number.isFinite(parsed)
        ? Math.min(columnDefinition.max, Math.max(columnDefinition.min, parsed))
        : fallbackValue;
      state.columnWeights[columnName] = safeValue;
      slider.value = String(safeValue);
      weightInput.value = String(safeValue);
    };

    syncWeight(state.columnWeights[columnName] ?? columnDefinition.defaultWeight);
    slider.addEventListener("input", () => syncWeight(slider.value));
    weightInput.addEventListener("input", () => syncWeight(weightInput.value));

    item.appendChild(text);
    item.appendChild(slider);
    item.appendChild(weightInput);
    elements.columnsContainer.appendChild(item);
  });
}

function cardBodyFromItem(item, options = {}) {
  const wrapper = document.createElement("div");
  wrapper.className = "card-body";
  const keyword = options.keyword ?? "";

  const title = document.createElement("h3");
  appendHighlightedText(title, truncateText(item.primaryText || "(no title)"), keyword);

  const sub = document.createElement("p");
  sub.className = "muted";
  appendHighlightedText(sub, truncateText(`ID: ${item.secondaryText || item.id}`), keyword);

  wrapper.appendChild(title);
  wrapper.appendChild(sub);

  if (options.includeMatches) {
    buildMatchedRows(item, keyword).forEach(([key, value]) => {
      const row = document.createElement("p");
      row.className = "match-row";
      appendHighlightedText(row, truncateText(`${key}: ${String(value)}`, 90), keyword);
      wrapper.appendChild(row);
    });
  }

  return wrapper;
}

function renderSearchResults() {
  elements.searchResults.innerHTML = "";

  if (state.searchItems.length === 0) {
    setMessage("検索結果がありません。", false);
    return;
  }

  state.searchItems.forEach((item) => {
    const card = document.createElement("article");
    card.className = "card selectable";
    card.setAttribute("tabindex", "0");
    card.setAttribute("role", "button");
    if (state.selectedItem && state.selectedItem.id === item.id) {
      card.classList.add("is-selected");
    }

    card.appendChild(createExpandIcon(item));

    card.appendChild(cardBodyFromItem(item, { keyword: state.keyword, includeMatches: true }));

    const selectItem = () => {
      state.selectedItem = item;
      elements.goStep3Button.disabled = false;
      renderSearchResults();
      setMessage("検索結果を 1 件選択しました。", false);
    };

    card.addEventListener("click", selectItem);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectItem();
      }
    });

    elements.searchResults.appendChild(card);
  });
}

function renderSimilarityResults(items) {
  elements.similarityResults.innerHTML = "";

  if (items.length === 0) {
    setMessage("類似結果がありません。", false);
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "card";

    card.appendChild(createExpandIcon(item));

    const body = cardBodyFromItem(item);
    card.appendChild(body);

    const score = document.createElement("p");
    score.className = "score";
    score.textContent = truncateText(`類似スコア: ${item.score}`);
    card.appendChild(score);

    const selectedValues = document.createElement("div");
    selectedValues.className = "selected-values";

    const entries = Object.entries(item.selectedValues || {});
    if (entries.length === 0) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "比較カラム未選択";
      selectedValues.appendChild(empty);
    } else {
      entries.forEach(([key, value]) => {
        const row = document.createElement("p");
        row.textContent = truncateText(`${key}: ${String(value)}`);
        selectedValues.appendChild(row);
      });
    }

    card.appendChild(selectedValues);
    elements.similarityResults.appendChild(card);
  });
}

async function onSearch() {
  state.keyword = elements.keywordInput.value.trim();
  state.searchTerms = parseSearchTerms(state.keyword);
  state.selectedItem = null;
  elements.goStep3Button.disabled = true;

  try {
    setMessage("検索中...", false);
    const response = await fetch(
      `/api/search?category=${encodeURIComponent(state.category)}&q=${encodeURIComponent(state.keyword)}`
    );
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Search failed");
    }

    state.searchItems = payload.items;
    renderSearchResults();
    showUntilStep(2);
    setMessage(`${payload.count} 件の検索結果を表示しました。`, false);
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function onRunSimilarity() {
  if (!state.selectedItem) {
    setMessage("先に検索結果を1件選択してください。", true);
    return;
  }

  const selectedColumns = state.allColumns
    .map((columnDefinition) => ({
      name: columnDefinition.name,
      weight:
        state.columnWeights[columnDefinition.name] ?? columnDefinition.defaultWeight
    }))
    .filter((item) => item.weight > 0);

  if (selectedColumns.length === 0) {
    setMessage("係数が 0 より大きいカラムを 1 つ以上指定してください。", true);
    return;
  }

  try {
    setMessage("類似度を計算中...", false);
    const response = await fetch("/api/similarity", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        category: state.category,
        columns: selectedColumns,
        rowNormalized: state.rowNormalized,
        selectedItemId: state.selectedItem.id
      })
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Similarity request failed");
    }

    renderSimilarityResults(payload.items);
    showUntilStep(4);
    setMessage(`${payload.count} 件の類似アイテムを表示しました。`, false);
  } catch (error) {
    setMessage(error.message, true);
  }
}

function bindEvents() {
  document.querySelectorAll("input[name='category']").forEach((radio) => {
    radio.addEventListener("change", async (event) => {
      state.category = event.target.value;
      resetDownstreamState();
      try {
        await fetchColumns();
        setMessage(`${state.category} のカラムを読み込みました。`, false);
      } catch (error) {
        setMessage(error.message, true);
      }
    });
  });

  elements.searchButton.addEventListener("click", onSearch);
  elements.keywordInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      onSearch();
    }
  });

  elements.rowNormalized.addEventListener("change", (event) => {
    setRowNormalizedState(event.target.checked);
  });

  elements.goStep3Button.addEventListener("click", () => {
    showUntilStep(3);
    setMessage("行正規化とカラム係数を調整してください。", false);
  });

  elements.runSimilarityButton.addEventListener("click", onRunSimilarity);

  elements.restartFlowButton.addEventListener("click", async () => {
    resetDownstreamState();
    try {
      await fetchColumns();
      setMessage("最初のステップに戻りました。", false);
    } catch (error) {
      setMessage(error.message, true);
    }
  });

  elements.detailsCloseButton.addEventListener("click", closeDetailsModal);
  elements.detailsModal.addEventListener("click", (event) => {
    if (event.target === elements.detailsModal) {
      closeDetailsModal();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeDetailsModal();
    }
  });
}

async function init() {
  bindEvents();
  resetDownstreamState();
  try {
    await fetchColumns();
    setMessage("カテゴリとキーワードを選んで検索してください。", false);
  } catch (error) {
    setMessage(error.message, true);
  }
}

init();
