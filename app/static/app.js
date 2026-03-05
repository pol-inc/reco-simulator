const state = {
  category: "Student",
  keyword: "",
  searchItems: [],
  selectedItem: null,
  method: "Sum",
  selectedColumns: new Set(),
  allColumns: []
};

const elements = {
  statusMessage: document.getElementById("status-message"),
  keywordInput: document.getElementById("keyword-input"),
  searchButton: document.getElementById("search-button"),
  searchResults: document.getElementById("search-results"),
  goStep3Button: document.getElementById("go-step-3"),
  columnsContainer: document.getElementById("columns-container"),
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

function openDetailsModal(item) {
  const data = item && item.data ? item.data : {};
  elements.detailsContent.innerHTML = "";

  Object.entries(data).forEach(([key, value]) => {
    const row = document.createElement("p");
    row.className = "modal-row";
    row.textContent = `${key}: ${String(value)}`;
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
  state.selectedColumns = new Set();
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
  state.allColumns.forEach((column) => {
    const label = document.createElement("label");
    label.className = "checkbox-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = column;
    checkbox.checked = state.selectedColumns.has(column);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        state.selectedColumns.add(column);
      } else {
        state.selectedColumns.delete(column);
      }
    });

    const text = document.createElement("span");
    text.textContent = column;

    label.appendChild(checkbox);
    label.appendChild(text);
    elements.columnsContainer.appendChild(label);
  });
}

function cardBodyFromItem(item) {
  const wrapper = document.createElement("div");
  wrapper.className = "card-body";

  const title = document.createElement("h3");
  title.textContent = truncateText(item.primaryText || "(no title)");

  const sub = document.createElement("p");
  sub.className = "muted";
  sub.textContent = truncateText(`ID: ${item.secondaryText || item.id}`);

  wrapper.appendChild(title);
  wrapper.appendChild(sub);
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

    card.appendChild(cardBodyFromItem(item));

    const selectItem = () => {
      state.selectedItem = item;
      elements.goStep3Button.disabled = false;
      renderSearchResults();
      setMessage("検索結果を1件選択しました。次へ進めます。", false);
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
    score.textContent = truncateText(`類似スコア (${item.method}): ${item.score}`);
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

  const methodNode = document.querySelector("input[name='method']:checked");
  state.method = methodNode ? methodNode.value : "Sum";

  try {
    setMessage("類似度を計算中...", false);
    const response = await fetch("/api/similarity", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        category: state.category,
        method: state.method,
        columns: Array.from(state.selectedColumns),
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

  document.querySelectorAll("input[name='method']").forEach((radio) => {
    radio.addEventListener("change", (event) => {
      state.method = event.target.value;
    });
  });

  elements.searchButton.addEventListener("click", onSearch);
  elements.keywordInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      onSearch();
    }
  });

  elements.goStep3Button.addEventListener("click", () => {
    showUntilStep(3);
    setMessage("計算方式と比較カラムを選択してください。", false);
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
