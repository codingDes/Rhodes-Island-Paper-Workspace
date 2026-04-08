async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const resp = await fetch("/api/upload", {
    method: "POST",
    body: formData
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "上传失败" }));
    throw new Error(err.detail || "上传失败");
  }
  return resp.json();
}

async function fetchOperators() {
  const resp = await fetch("/api/operators");
  if (!resp.ok) throw new Error("读取干员列表失败");
  return resp.json();
}

async function generateSummary(docId) {
  const resp = await fetch(`/api/summary/${encodeURIComponent(docId)}`, {
    method: "POST"
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "总结失败" }));
    throw new Error(err.detail || "总结失败");
  }
  return resp.json();
}

async function askPaperQuestion(focusDocIds, question, operatorId, history) {
  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, operator_id: operatorId, focus_doc_ids: focusDocIds, history })
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "问答失败" }));
    throw new Error(err.detail || "问答失败");
  }
  return resp.json();
}

async function fetchArchiveState() {
  const resp = await fetch("/api/archive-state");
  if (!resp.ok) throw new Error("读取档案状态失败");
  return resp.json();
}

async function saveArchiveState(categories, archives) {
  const resp = await fetch("/api/archive-state", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ categories, archives }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "保存档案状态失败" }));
    throw new Error(err.detail || "保存档案状态失败");
  }
  return resp.json();
}

