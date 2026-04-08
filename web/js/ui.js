const uploadBtn = document.getElementById("upload-btn");
const archiveList = document.getElementById("archive-list");
const archiveFilterSelect = document.getElementById("archive-filter-select");
const categoryManageBtn = document.getElementById("category-manage-btn");
const toast = document.getElementById("toast");
const operatorList = document.getElementById("operator-list");
const chatLog = document.getElementById("chat-log");
const chatInput = document.getElementById("chat-input");
const chatBtn = document.getElementById("chat-btn");
const chatOperatorName = document.getElementById("chat-operator-name");
const chatTypingStatus = document.getElementById("chat-typing-status");
const mainLayout = document.getElementById("main-layout");
const leftToggleBtn = document.getElementById("left-toggle-btn");

const modalUploadBackdrop = document.getElementById("modal-upload-backdrop");
const modalFileInput = document.getElementById("modal-file-input");
const modalUploadCategories = document.getElementById("modal-upload-categories");
const modalUploadCancel = document.getElementById("modal-upload-cancel");
const modalUploadSubmit = document.getElementById("modal-upload-submit");

const modalCategoriesBackdrop = document.getElementById("modal-categories-backdrop");
const modalCategoryRows = document.getElementById("modal-category-rows");
const modalCategoryNewInput = document.getElementById("modal-category-new-input");
const modalCategoryAddBtn = document.getElementById("modal-category-add-btn");
const modalCategoriesClose = document.getElementById("modal-categories-close");

let currentOperatorId = "";
const operatorsById = {};
const chatHistoryByOperator = {};
const lastPreviewByOperator = {};
let categories = ["未分类"];
let archives = [];
let focusedDocIds = [];

/** 理智：上限 180；按本轮聊天内容判定脑力消耗或休息恢复（不超过上限） */
const SANITY_MAX = 180;
let sanityCurrent = SANITY_MAX;
const sanityWidget = document.getElementById("sanity-widget");
const sanityCurrentEl = document.getElementById("sanity-current");

function clampSanity(n) {
  return Math.max(0, Math.min(SANITY_MAX, n));
}

function randomSanityStep(min, max) {
  return min + Math.floor(Math.random() * (max - min + 1));
}

/** 脑力消耗：基础 5~20，随问题变长略增 */
function deltaDrainForPaperQuestion(question) {
  const base = randomSanityStep(5, 20);
  const len = (question || "").length;
  const load = Math.min(12, Math.floor(len / 35));
  return base + load;
}

/** 恢复：基础 5~20，理智越低略多回；长一点的放松话略多回 */
function deltaRestoreForCasual(question) {
  let base = randomSanityStep(5, 20);
  const ratio = sanityCurrent / SANITY_MAX;
  if (ratio < 0.35) base += randomSanityStep(3, 10);
  else if (ratio < 0.6) base += randomSanityStep(0, 6);
  const len = (question || "").length;
  if (len > 80) base += Math.min(6, Math.floor(len / 90));
  return base;
}

function updateSanityDisplay() {
  if (sanityCurrentEl) sanityCurrentEl.textContent = String(sanityCurrent);
  if (sanityWidget) sanityWidget.classList.toggle("sanity-widget--low", sanityCurrent <= 45);
}

function triggerSanityPulse(direction) {
  if (!sanityWidget) return;
  sanityWidget.classList.remove("sanity-pulse--down", "sanity-pulse--up");
  const cls = direction === "down" ? "sanity-pulse--down" : "sanity-pulse--up";
  void sanityWidget.offsetWidth;
  sanityWidget.classList.add(cls);
  setTimeout(() => sanityWidget.classList.remove(cls), 480);
}

function showSanityFloat(delta) {
  const anchor = sanityWidget?.querySelector(".sanity-anim-anchor");
  if (!anchor || delta === 0) return;
  const el = document.createElement("span");
  el.className = `sanity-float sanity-float--${delta > 0 ? "up" : "down"}`;
  el.textContent = (delta > 0 ? "+" : "") + delta;
  anchor.appendChild(el);
  requestAnimationFrame(() => el.classList.add("sanity-float--show"));
  setTimeout(() => el.remove(), 960);
}

function applySanityDelta(delta) {
  const prev = sanityCurrent;
  const next = clampSanity(prev + delta);
  const actual = next - prev;
  sanityCurrent = next;
  updateSanityDisplay();
  if (actual !== 0) {
    showSanityFloat(actual);
    triggerSanityPulse(actual < 0 ? "down" : "up");
  }
}

function sanitizeRenderedHtml(rawHtml) {
  const doc = new DOMParser().parseFromString(`<div>${rawHtml}</div>`, "text/html");
  doc.querySelectorAll("script,iframe,object,embed,link,style").forEach((el) => el.remove());
  doc.querySelectorAll("*").forEach((el) => {
    [...el.attributes].forEach((attr) => {
      const name = attr.name.toLowerCase();
      const value = (attr.value || "").toLowerCase();
      if (name.startsWith("on")) el.removeAttribute(attr.name);
      if ((name === "href" || name === "src") && value.startsWith("javascript:")) el.removeAttribute(attr.name);
    });
  });
  return doc.body.firstElementChild?.innerHTML || "";
}

function setTypingStatus(active) {
  if (!chatTypingStatus) return;
  chatTypingStatus.textContent = active ? "对方正在输入..." : "";
  chatTypingStatus.classList.toggle("chat-typing-status--show", Boolean(active));
}

function latexToHtml(latex, displayMode) {
  if (!window.katex) return escapeHtml(latex);
  try {
    return window.katex.renderToString(latex, {
      throwOnError: false,
      displayMode,
      strict: "ignore",
      output: "html",
    });
  } catch (_) {
    return escapeHtml(latex);
  }
}

function renderMathBeforeMarkdown(text) {
  const slots = [];
  const put = (html) => {
    const key = `@@MATH_SLOT_${slots.length}@@`;
    slots.push(html);
    return key;
  };

  let out = String(text || "");
  out = out.replace(/\$\$([\s\S]+?)\$\$/g, (_, expr) => put(latexToHtml(expr.trim(), true)));
  out = out.replace(/\\\[([\s\S]+?)\\\]/g, (_, expr) => put(latexToHtml(expr.trim(), true)));
  out = out.replace(/\\\(([\s\S]+?)\\\)/g, (_, expr) => put(latexToHtml(expr.trim(), false)));
  out = out.replace(/(^|[^\$])\$([^\n$][^$]*?)\$(?!\$)/g, (m, p1, expr) => `${p1}${put(latexToHtml(expr.trim(), false))}`);

  return { text: out, slots };
}

function renderAssistantRichText(raw) {
  const text = String(raw || "");
  const { text: safeMathText, slots } = renderMathBeforeMarkdown(text);
  if (!window.marked) return escapeHtml(safeMathText).replace(/\n/g, "<br />");
  marked.setOptions({ gfm: true, breaks: true });
  const html = marked.parse(safeMathText);
  let clean = sanitizeRenderedHtml(html);
  clean = clean.replace(/@@MATH_SLOT_(\d+)@@/g, (_, i) => slots[Number(i)] || "");
  return clean;
}

function renderLatexInBubble(el) {
  if (!window.renderMathInElement) return;
  try {
    window.renderMathInElement(el, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false },
      ],
      throwOnError: false,
      strict: "ignore",
    });
  } catch (_) {}
}

/** 已废弃的历史分类名，界面与数据中一律剔除 */
const REMOVED_CATEGORY_NAMES = new Set(["默认分类"]);

function normalizeCategoriesList() {
  categories = [
    ...new Set(
      categories.map((c) => String(c || "").trim()).filter((c) => c && !REMOVED_CATEGORY_NAMES.has(c))
    )
  ];
  if (!categories.includes("未分类")) categories.unshift("未分类");
}

/** 规范化档案上的分类（多标签）；兼容旧数据 category 字符串 */
function archiveCategoriesOf(a) {
  const fromArr = Array.isArray(a.categories) && a.categories.length ? a.categories : [];
  const fromLegacy = a.category ? [a.category] : [];
  let raw = fromArr.length ? fromArr : fromLegacy;
  raw = [
    ...new Set(
      raw
        .map((c) => String(c || "").trim())
        .filter((c) => c && !REMOVED_CATEGORY_NAMES.has(c))
    )
  ];
  if (!raw.length) return ["未分类"];
  return raw;
}

function syncArchiveCategoryFields() {
  for (const a of archives) {
    const next = archiveCategoriesOf(a);
    a.categories = next;
    delete a.category;
  }
}

function setArchiveCategories(a, cats) {
  const next = [...new Set(cats.map(String).filter(Boolean).filter((c) => !REMOVED_CATEGORY_NAMES.has(c)))];
  a.categories = next.length ? next : ["未分类"];
  delete a.category;
}

function selectedModalUploadCategories() {
  return [...modalUploadCategories.querySelectorAll('input[type="checkbox"]:checked')]
    .map((cb) => cb.value)
    .filter(Boolean);
}

function categoryDocCount(c) {
  return archives.reduce((n, a) => n + (archiveCategoriesOf(a).includes(c) ? 1 : 0), 0);
}

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 1800);
}

function errText(err, fallback = "未知错误") {
  if (!err) return fallback;
  if (typeof err === "string") return err;
  if (typeof err.message === "string" && err.message.trim()) return err.message;
  try {
    return JSON.stringify(err);
  } catch (_) {
    return fallback;
  }
}

async function fetchArchiveStateSafe() {
  if (typeof fetchArchiveState === "function") return fetchArchiveState();
  const resp = await fetch("/api/archive-state");
  if (!resp.ok) throw new Error("读取档案状态失败");
  return resp.json();
}

async function saveArchiveStateSafe(cats, ars) {
  if (typeof saveArchiveState === "function") return saveArchiveState(cats, ars);
  const resp = await fetch("/api/archive-state", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ categories: cats, archives: ars }),
  });
  if (!resp.ok) throw new Error("保存档案状态失败");
  return resp.json();
}

async function persistArchiveState() {
  try {
    const state = await saveArchiveStateSafe(categories, archives);
    categories = Array.isArray(state.categories) && state.categories.length ? state.categories : ["未分类"];
    archives = Array.isArray(state.archives) ? state.archives : archives;
  } catch (err) {
    showToast(`保存状态失败：${errText(err)}`);
  }
}

async function initArchiveState() {
  try {
    const state = await fetchArchiveStateSafe();
    categories = Array.isArray(state.categories) && state.categories.length ? state.categories : ["未分类"];
    archives = Array.isArray(state.archives) ? state.archives : [];
  } catch (err) {
    // Fallback to local defaults
    categories = ["未分类"];
    archives = [];
    showToast(`读取档案状态失败：${errText(err)}`);
  }
}

function openModal(backdrop) {
  if (!backdrop) return;
  backdrop.classList.add("modal-backdrop--open");
  backdrop.setAttribute("aria-hidden", "false");
}

function closeModal(backdrop) {
  if (!backdrop) return;
  backdrop.classList.remove("modal-backdrop--open");
  backdrop.setAttribute("aria-hidden", "true");
}

function fillModalUploadCategoryOptions() {
  const prev = selectedModalUploadCategories().filter((v) => categories.includes(v));
  modalUploadCategories.innerHTML = "";
  for (const c of categories) {
    const label = document.createElement("label");
    label.className = "modal-cat-chip";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = c;
    cb.checked = prev.length ? prev.includes(c) : c === "未分类";
    const span = document.createElement("span");
    span.textContent = c;
    label.appendChild(cb);
    label.appendChild(span);
    modalUploadCategories.appendChild(label);
  }
}

function openUploadModal() {
  normalizeCategoriesList();
  syncArchiveCategoryFields();
  modalFileInput.value = "";
  fillModalUploadCategoryOptions();
  openModal(modalUploadBackdrop);
  modalFileInput.focus();
}

function renameCategory(oldName, newName) {
  const o = String(oldName || "").trim();
  const n = String(newName || "").trim();
  if (!n || o === n) return;
  if (o === "未分类") {
    showToast("「未分类」不能改名");
    return;
  }
  if (REMOVED_CATEGORY_NAMES.has(n)) return;
  if (categories.includes(n)) {
    showToast("已存在同名分类");
    return;
  }
  const idx = categories.indexOf(o);
  if (idx < 0) return;
  categories[idx] = n;
  for (const a of archives) {
    const cats = archiveCategoriesOf(a);
    if (!cats.includes(o)) continue;
    const next = cats.map((c) => (c === o ? n : c));
    setArchiveCategories(a, next);
  }
  if (archiveFilterSelect.value === o) archiveFilterSelect.value = n;
  renderCategories();
  renderArchiveList();
  renderCategoryManageModal();
  showToast("已重命名分类");
  void persistArchiveState();
}

function deleteCategory(name) {
  const c = String(name || "").trim();
  if (c === "未分类") {
    showToast("不能删除「未分类」");
    return;
  }
  if (!categories.includes(c)) return;
  const nDocs = categoryDocCount(c);
  if (!window.confirm(`确定删除分类「${c}」？${nDocs ? `将影响 ${nDocs} 个档案的标签。` : ""}`)) return;
  categories = categories.filter((x) => x !== c);
  for (const a of archives) {
    const cats = archiveCategoriesOf(a).filter((x) => x !== c);
    setArchiveCategories(a, cats);
  }
  if (archiveFilterSelect.value === c) archiveFilterSelect.value = "__all__";
  normalizeCategoriesList();
  renderCategories();
  renderArchiveList();
  renderCategoryManageModal();
  showToast("已删除分类");
  void persistArchiveState();
}

function renderCategoryManageModal() {
  if (!modalCategoryRows) return;
  modalCategoryRows.innerHTML = "";
  for (const c of categories) {
    const row = document.createElement("div");
    row.className = "cat-manage-row" + (c === "未分类" ? " cat-manage-row--locked" : "");
    const cnt = categoryDocCount(c);
    if (c === "未分类") {
      row.innerHTML = `
        <div class="cat-manage-main">
          <span class="cat-manage-name">未分类</span>
          <span class="cat-manage-meta">${cnt} 个档案</span>
        </div>
        <span class="cat-manage-locked-hint">系统分类</span>`;
    } else {
      row.innerHTML = `
        <div class="cat-manage-main">
          <input type="text" class="cat-manage-input" value="${escapeHtml(c)}" aria-label="分类名称" />
          <span class="cat-manage-meta">${cnt} 个档案</span>
        </div>
        <div class="cat-manage-actions">
          <button type="button" class="secondary-btn cat-manage-save-btn">保存改名</button>
          <button type="button" class="secondary-btn cat-manage-del-btn">删除</button>
        </div>`;
      const input = row.querySelector(".cat-manage-input");
      row.querySelector(".cat-manage-save-btn").addEventListener("click", () => {
        renameCategory(c, input.value.trim());
      });
      row.querySelector(".cat-manage-del-btn").addEventListener("click", () => deleteCategory(c));
    }
    modalCategoryRows.appendChild(row);
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function openCategoriesModal() {
  normalizeCategoriesList();
  syncArchiveCategoryFields();
  renderCategoryManageModal();
  openModal(modalCategoriesBackdrop);
  modalCategoryNewInput.value = "";
  modalCategoryNewInput.focus();
}

function resolveOperatorAvatar(op) {
  if (op && op.avatar) return op.avatar;
  return `/assets/img/operators/${op.id}.png`;
}

function appendChat(role, content, operatorName = "助手") {
  const row = document.createElement("div");
  row.className = `msg-row ${role}`;
  const avatar = document.createElement("img");
  avatar.className = "msg-avatar";
  if (role === "user") {
    avatar.src = "/assets/img/doctor.png";
  } else {
    const op = operatorsById[currentOperatorId];
    avatar.src = op ? resolveOperatorAvatar(op) : "/assets/img/operators/amiya.png";
    avatar.onerror = () => {
      if (avatar.dataset.fallbackDone) return;
      avatar.dataset.fallbackDone = "1";
      avatar.src = "/assets/img/operators/amiya.png";
    };
  }
  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  if (role === "assistant") {
    bubble.innerHTML = renderAssistantRichText(content);
    renderLatexInBubble(bubble);
  } else {
    bubble.textContent = content;
  }
  row.appendChild(avatar);
  row.appendChild(bubble);
  chatLog.appendChild(row);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderOperatorHeader(op) {
  if (chatOperatorName) chatOperatorName.textContent = op.name;
}

function renderOperatorList() {
  operatorList.innerHTML = "";
  for (const opId of Object.keys(operatorsById)) {
    const op = operatorsById[opId];
    const item = document.createElement("div");
    item.className = `operator-item${opId === currentOperatorId ? " active" : ""}`;
    item.innerHTML = `
      <img class="operator-avatar" src="${resolveOperatorAvatar(op)}" alt="${op.name}" />
      <div class="operator-main">
        <div class="operator-topline"><div class="operator-name">${op.name}</div><span class="status-dot"></span></div>
        <div class="operator-catch">${op.catchphrase || ""}</div>
        <div class="operator-preview">${lastPreviewByOperator[opId] || "暂无回复记录"}</div>
      </div>`;
    item.addEventListener("click", () => {
      currentOperatorId = opId;
      renderOperatorList();
      renderOperatorHeader(op);
      redrawChatByOperator(opId);
    });
    operatorList.appendChild(item);
  }
}

function redrawChatByOperator(operatorId) {
  chatLog.innerHTML = "";
  const turns = chatHistoryByOperator[operatorId] || [];
  for (const t of turns) appendChat(t.role, t.content, t.operator_name || "助手");
}

function renderCategories() {
  normalizeCategoriesList();
  syncArchiveCategoryFields();
  archiveFilterSelect.innerHTML = [
    `<option value="__all__">全部分类</option>`,
    ...categories.map((c) => `<option value="${c}">${c}</option>`)
  ].join("");
}

function renderArchiveList() {
  archiveList.innerHTML = "";
  const filter = archiveFilterSelect.value || "__all__";
  const view =
    filter === "__all__"
      ? archives
      : archives.filter((a) => archiveCategoriesOf(a).includes(filter));

  if (view.length === 0) {
    const empty = document.createElement("div");
    empty.className = "archive-list-empty";
    if (archives.length === 0) empty.textContent = "暂无档案";
    else empty.textContent = "该分类下暂无档案";
    archiveList.appendChild(empty);
    return;
  }

  for (const a of view) {
    const row = document.createElement("div");
    row.className = "archive-item";
    const checked = focusedDocIds.includes(a.doc_id) ? "checked" : "";
    row.innerHTML = `
      <div class="archive-item-top">
        <input type="checkbox" class="archive-item-check" data-doc-id="${a.doc_id}" ${checked} />
        <div class="archive-item-main">
          <div class="archive-title">${a.title || a.filename}</div>
          <div class="archive-meta">${a.doc_id}</div>
        </div>
      </div>
      <div class="archive-cat-row">
        <span class="archive-cat-hint">标签</span>
        <div class="archive-cat-tags" data-doc-id="${a.doc_id}"></div>
      </div>`;
    archiveList.appendChild(row);
    const tagsWrap = row.querySelector(".archive-cat-tags");
    const current = archiveCategoriesOf(a);
    for (const c of categories) {
      const tag = document.createElement("button");
      tag.type = "button";
      tag.className = "archive-cat-tag" + (current.includes(c) ? " archive-cat-tag--on" : "");
      if (c === "未分类") tag.classList.add("archive-cat-tag--system");
      tag.textContent = c;
      tag.title = current.includes(c) ? "点击移除此标签" : "点击添加此标签";
      tag.addEventListener("click", () => {
        let next = [...archiveCategoriesOf(a)];
        if (next.includes(c)) next = next.filter((x) => x !== c);
        else next.push(c);
        setArchiveCategories(a, next);
        renderCategories();
        renderArchiveList();
        if (modalCategoriesBackdrop.classList.contains("modal-backdrop--open")) renderCategoryManageModal();
        showToast("已更新分类");
        void persistArchiveState();
      });
      tagsWrap.appendChild(tag);
    }
  }
  archiveList.querySelectorAll(".archive-item-check").forEach((cb) => {
    cb.addEventListener("change", () => {
      const id = cb.dataset.docId;
      if (cb.checked) {
        if (!focusedDocIds.includes(id)) focusedDocIds.push(id);
      } else {
        focusedDocIds = focusedDocIds.filter((x) => x !== id);
      }
      showToast(`当前关注档案：${focusedDocIds.length} 个`);
    });
  });
}

uploadBtn.addEventListener("click", () => openUploadModal());
modalUploadCancel.addEventListener("click", () => closeModal(modalUploadBackdrop));
modalUploadBackdrop.addEventListener("click", (e) => {
  if (e.target === modalUploadBackdrop) closeModal(modalUploadBackdrop);
});
modalUploadSubmit.addEventListener("click", async () => {
  const file = modalFileInput.files?.[0];
  if (!file) {
    showToast("请先选择文件");
    return;
  }
  let catList = selectedModalUploadCategories();
  if (!catList.length) catList = ["未分类"];
  modalUploadSubmit.disabled = true;
  modalUploadCancel.disabled = true;
  modalUploadBackdrop.classList.add("modal-backdrop--uploading");
  modalUploadSubmit.classList.add("is-uploading");
  try {
    const data = await uploadDocument(file);
    archives.unshift({
      doc_id: data.doc_id,
      filename: data.filename,
      title: data.title_candidate || data.filename,
      categories: [...catList],
      text_length: data.text_length
    });
    if (!focusedDocIds.includes(data.doc_id)) focusedDocIds.unshift(data.doc_id);
    closeModal(modalUploadBackdrop);
    renderArchiveList();
    renderCategories();
    showToast(`上传成功：${data.title_candidate || data.filename}`);
    void persistArchiveState();
  } catch (err) {
    showToast(`上传失败：${err.message}`);
  } finally {
    modalUploadSubmit.disabled = false;
    modalUploadCancel.disabled = false;
    modalUploadBackdrop.classList.remove("modal-backdrop--uploading");
    modalUploadSubmit.classList.remove("is-uploading");
    modalFileInput.value = "";
  }
});

categoryManageBtn.addEventListener("click", () => openCategoriesModal());
modalCategoriesClose.addEventListener("click", () => closeModal(modalCategoriesBackdrop));
modalCategoriesBackdrop.addEventListener("click", (e) => {
  if (e.target === modalCategoriesBackdrop) closeModal(modalCategoriesBackdrop);
});

modalCategoryAddBtn.addEventListener("click", () => {
  const name = (modalCategoryNewInput.value || "").trim();
  if (!name || categories.includes(name)) {
    if (name) showToast("分类已存在");
    return;
  }
  if (REMOVED_CATEGORY_NAMES.has(name)) return;
  categories.push(name);
  modalCategoryNewInput.value = "";
  renderCategories();
  renderArchiveList();
  renderCategoryManageModal();
  showToast("已添加分类");
  void persistArchiveState();
});

document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (modalUploadBackdrop.classList.contains("modal-backdrop--open")) {
    closeModal(modalUploadBackdrop);
    e.preventDefault();
  } else if (modalCategoriesBackdrop.classList.contains("modal-backdrop--open")) {
    closeModal(modalCategoriesBackdrop);
    e.preventDefault();
  }
});

chatBtn.addEventListener("click", async () => {
  const question = (chatInput.value || "").trim();
  if (!question) return;
  chatInput.value = "";
  chatBtn.disabled = true;
  setTypingStatus(true);
  const operatorId = currentOperatorId;
  appendChat("user", question);
  chatHistoryByOperator[operatorId].push({ role: "user", content: question });
  try {
    const data = await askPaperQuestion(
      focusedDocIds,
      question,
      operatorId,
      chatHistoryByOperator[operatorId]
    );
    appendChat("assistant", data.answer, data.operator_name || "助手");
    lastPreviewByOperator[operatorId] = `${data.operator_name || "干员"}：${(data.answer || "").slice(0, 24)}...`;
    chatHistoryByOperator[operatorId].push({
      role: "assistant",
      content: data.answer,
      operator_name: data.operator_name || "助手"
    });
    renderOperatorList();
    if (Number.isFinite(data.sanity_delta) && data.sanity_delta !== 0) {
      applySanityDelta(data.sanity_delta);
    } else if (data.sanity_effect === "drain") {
      applySanityDelta(-deltaDrainForPaperQuestion(question));
    } else {
      applySanityDelta(deltaRestoreForCasual(question));
    }
  } catch (err) {
    appendChat("assistant", `问答失败: ${err.message}`);
  } finally {
    setTypingStatus(false);
    chatBtn.disabled = false;
  }
});

archiveFilterSelect.addEventListener("change", renderArchiveList);

function setLeftCollapsed(collapsed) {
  if (!mainLayout) return;
  mainLayout.classList.toggle("left-collapsed", collapsed);
  leftToggleBtn.textContent = collapsed ? "▶" : "◀";
}
if (leftToggleBtn) {
  leftToggleBtn.addEventListener("click", () => {
    setLeftCollapsed(!mainLayout.classList.contains("left-collapsed"));
  });
}
if (chatInput) {
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatBtn.click();
    }
  });
}

async function initOperators() {
  const data = await fetchOperators();
  for (const op of data.items || []) {
    operatorsById[op.id] = op;
    if (!chatHistoryByOperator[op.id]) chatHistoryByOperator[op.id] = [];
    if (!lastPreviewByOperator[op.id]) lastPreviewByOperator[op.id] = "";
  }
  const first = (data.items || [])[0];
  if (!first) return;
  currentOperatorId = first.id;
  renderOperatorList();
  renderOperatorHeader(first);
  redrawChatByOperator(first.id);
}

function initActivityCarousel() {
  const track = document.getElementById("planner-activity-track");
  if (!track || track.children.length === 0) return;
  const n = track.children.length;
  let i = 0;
  const step = () => {
    i = (i + 1) % n;
    const offset = (i * 100) / n;
    track.style.transform = `translateX(-${offset}%)`;
  };
  setInterval(step, 4800);

  track.querySelectorAll("img").forEach((img) => {
    img.addEventListener("error", () => {
      img.closest(".planner-carousel-slide")?.classList.add("planner-carousel-slide--broken");
    });
  });
}

initActivityCarousel();
initOperators();
initArchiveState().then(() => {
  renderCategories();
  renderArchiveList();
});

const doctorAvatar = document.getElementById("doctor-avatar");
if (doctorAvatar) doctorAvatar.onerror = () => (doctorAvatar.src = "/assets/img/operators/amiya.png");
