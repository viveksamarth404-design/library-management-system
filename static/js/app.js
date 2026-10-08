"use strict";

const state = { status: "", query: "", members: [], issuingId: null };
const $ = (sel) => document.querySelector(sel);
const grid = $("#book-grid");
const toastEl = $("#toast");
let toastTimer;

const SPINES = ["#1d2a63", "#0b8a79", "#b8451f", "#7a3fa0", "#a8740a", "#1d6fa5"];
function spine(category) {
  let h = 0;
  for (const ch of category) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return SPINES[h % SPINES.length];
}

function toast(message, isError = false) {
  toastEl.textContent = message;
  toastEl.classList.toggle("error", isError);
  toastEl.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("show"), 3200);
}

function esc(value) {
  const d = document.createElement("div");
  d.textContent = value == null ? "" : String(value);
  return d.innerHTML;
}

async function api(path, options = {}) {
  const init = { headers: { "Content-Type": "application/json" }, ...options };
  if (init.body && typeof init.body !== "string") init.body = JSON.stringify(init.body);
  const res = await fetch(path, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong. Try again.");
  return data;
}

// ---------- Rendering ----------
function renderBooks(books) {
  grid.innerHTML = books.map((b) => {
    const issued = !b.available;
    const note = issued
      ? `<p class="issued-note">With ${esc(b.member_name)} since ${esc(b.issue_date)}</p>` : "";
    const main = issued
      ? `<button type="button" class="btn" data-action="return" data-id="${b.id}">Return</button>`
      : `<button type="button" class="btn primary" data-action="issue" data-id="${b.id}" data-title="${esc(b.title)}">Issue</button>`;
    return `
      <article class="card" style="--spine:${spine(b.category)}">
        <div class="card-body">
          <span class="card-cat">${esc(b.category)}</span>
          <div>
            <h3 class="card-title">${esc(b.title)}</h3>
            <p class="card-author">${esc(b.author)}</p>
          </div>
          <p class="card-isbn">ISBN ${esc(b.isbn)}</p>
          ${note}
        </div>
        <div class="card-foot">
          <span class="status ${issued ? "issued" : "available"}">${issued ? "Issued" : "Available"}</span>
          <div class="card-actions">
            ${main}
            <button type="button" class="btn text-danger" data-action="delete" data-id="${b.id}" data-title="${esc(b.title)}">Delete</button>
          </div>
        </div>
      </article>`;
  }).join("");

  const none = books.length === 0;
  $("#empty").hidden = !none;
  const filtered = state.query || state.status;
  if (none) {
    $("#empty-text").textContent = filtered
      ? `No books match${state.query ? ` "${state.query}"` : ""}. Check the spelling or clear the filters.`
      : "The catalog is empty. Add your first book to get started.";
    $("#empty-add").hidden = Boolean(filtered);
  }
  $("#result-line").textContent = none ? "" :
    `${books.length} ${books.length === 1 ? "book" : "books"}${filtered ? " found" : ""}`;
}

async function loadBooks() {
  const params = new URLSearchParams();
  if (state.query) params.set("q", state.query);
  if (state.status) params.set("status", state.status);
  try {
    renderBooks(await api(`/api/books?${params}`));
  } catch (err) {
    toast(err.message, true);
  }
}

async function loadCounts() {
  try {
    const all = await api("/api/books");
    const issued = all.filter((b) => !b.available).length;
    $("#stat-total").textContent = all.length;
    $("#stat-available").textContent = all.length - issued;
    $("#stat-issued").textContent = issued;
  } catch (_) { /* counts are cosmetic */ }
}

async function loadMembers() {
  state.members = await api("/api/members");
  $("#issue-member").innerHTML = state.members
    .map((m) => `<option value="${m.id}">${esc(m.name)} (${esc(m.email)})</option>`).join("");
  $("#stat-members").textContent = state.members.length;
}

const refresh = () => Promise.all([loadBooks(), loadCounts()]);

// ---------- Search & filter ----------
let debounce;
$("#search").addEventListener("input", (e) => {
  clearTimeout(debounce);
  debounce = setTimeout(() => { state.query = e.target.value.trim(); loadBooks(); }, 200);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach((c) => c.classList.remove("is-on"));
    chip.classList.add("is-on");
    state.status = chip.dataset.status;
    loadBooks();
  });
});

// ---------- Dialogs ----------
document.querySelectorAll("dialog").forEach((d) => {
  d.addEventListener("click", (e) => { if (e.target === d) d.close(); });
  d.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => d.close()));
});
const openBook = () => $("#book-dialog").showModal();
$("#open-book").addEventListener("click", openBook);
$("#empty-add").addEventListener("click", openBook);
$("#open-member").addEventListener("click", () => $("#member-dialog").showModal());

// ---------- Card actions ----------
grid.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  try {
    if (btn.dataset.action === "issue") {
      state.issuingId = id;
      $("#issue-title").textContent = btn.dataset.title;
      $("#issue-dialog").showModal();
    } else if (btn.dataset.action === "return") {
      await api(`/api/books/${id}/return`, { method: "POST" });
      toast("Book returned.");
      refresh();
    } else if (btn.dataset.action === "delete") {
      if (!confirm(`Delete "${btn.dataset.title}"? This cannot be undone.`)) return;
      await api(`/api/books/${id}`, { method: "DELETE" });
      toast("Book deleted.");
      refresh();
    }
  } catch (err) {
    toast(err.message, true);
    refresh();
  }
});

$("#issue-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api(`/api/books/${state.issuingId}/issue`, {
      method: "POST",
      body: { member_id: Number($("#issue-member").value) },
    });
    toast("Book issued.");
  } catch (err) {
    toast(err.message, true);
  }
  $("#issue-dialog").close();
  refresh();
});

// ---------- Forms ----------
function validate(form) {
  let ok = true;
  form.querySelectorAll("input[required]").forEach((input) => {
    const bad = !input.value.trim();
    input.classList.toggle("invalid", bad);
    if (bad) ok = false;
  });
  return ok;
}

$("#book-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  if (!validate(form)) return toast("Fill in title, author and ISBN.", true);
  try {
    await api("/api/books", { method: "POST", body: Object.fromEntries(new FormData(form)) });
    form.reset();
    $("#book-dialog").close();
    toast("Book added.");
    refresh();
  } catch (err) {
    toast(err.message, true);
  }
});

$("#member-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  if (!validate(form)) return toast("Enter a name and email.", true);
  try {
    await api("/api/members", { method: "POST", body: Object.fromEntries(new FormData(form)) });
    form.reset();
    $("#member-dialog").close();
    toast("Member added.");
    loadMembers();
  } catch (err) {
    toast(err.message, true);
  }
});

// ---------- Init ----------
loadMembers().catch((err) => toast(err.message, true));
refresh();
