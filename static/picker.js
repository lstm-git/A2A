// Entra ID people picker. Attaches to any [data-picker] container holding a
// .picker-input (visible text box) and a hidden input (the value submitted).
document.querySelectorAll("[data-picker]").forEach(initPicker);

function initPicker(root) {
  const input = root.querySelector(".picker-input");
  const hidden = root.querySelector('input[type="hidden"]');
  const chipBox = root.querySelector(".picker-chip");
  const results = root.querySelector(".picker-results");
  let timer;

  function selectUser(name, email) {
    hidden.value = email;
    chipBox.innerHTML = "";
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = name;
    const x = document.createElement("span");
    x.className = "x";
    x.textContent = "×";
    x.title = "Remove";
    x.setAttribute("role", "button");
    x.onclick = clearSelection;
    chip.appendChild(x);
    chipBox.appendChild(chip);
    chipBox.hidden = false;
    input.hidden = true;
    results.hidden = true;
  }

  function clearSelection() {
    hidden.value = "";
    chipBox.hidden = true;
    chipBox.innerHTML = "";
    input.hidden = false;
    input.value = "";
    input.focus();
  }

  // Restore a previously selected value (e.g. after a validation error).
  if (hidden.value) {
    selectUser(hidden.value, hidden.value);
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    const q = input.value.trim();
    hidden.value = q; // fallback: allow manual entry, validated server-side
    if (q.length < 2) {
      results.hidden = true;
      results.innerHTML = "";
      return;
    }
    timer = setTimeout(() => search(q), 250);
  });

  async function search(q) {
    results.hidden = false;
    results.innerHTML = '<div class="picker-msg">Searching…</div>';
    try {
      const r = await fetch("/api/users/search?q=" + encodeURIComponent(q));
      render(await r.json());
    } catch (e) {
      results.innerHTML = '<div class="picker-msg">Search failed.</div>';
    }
  }

  function render(data) {
    results.innerHTML = "";
    if (data.configured === false) {
      results.innerHTML =
        '<div class="picker-msg">Directory search not configured — type a full email manually.</div>';
      return;
    }
    if (!data.results || !data.results.length) {
      results.innerHTML = '<div class="picker-msg">No matching users.</div>';
      return;
    }
    data.results.forEach((u) => {
      const item = document.createElement("div");
      item.className = "picker-item";
      const n = document.createElement("span");
      n.className = "pi-name";
      n.textContent = u.name;
      const e = document.createElement("span");
      e.className = "pi-email";
      e.textContent = u.email;
      item.append(n, e);
      item.onclick = () => selectUser(u.name, u.email);
      results.appendChild(item);
    });
  }

  document.addEventListener("click", (e) => {
    if (!root.contains(e.target)) results.hidden = true;
  });
}
