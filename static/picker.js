// Entra ID people picker. Attaches to any [data-picker] container holding a
// .picker-input (visible text box) and a hidden input (the value submitted).
document.querySelectorAll("[data-picker]").forEach(initPicker);

// Positive-numbers-only enforcement for hours/number fields on A2A forms:
// block sign and exponent characters, and strip any minus that gets pasted in.
document.querySelectorAll('.a2a-form input[type="number"]').forEach((el) => {
  el.addEventListener("keydown", (e) => {
    if (["-", "+", "e", "E"].includes(e.key)) e.preventDefault();
  });
  el.addEventListener("input", () => {
    if (el.value.includes("-")) el.value = el.value.replace(/-/g, "");
  });
});

// Position classification -> code auto-fill, plus the "Other" clinical-duties
// follow-up. Authoritative mapping lives in steps.py (CLASSIFICATION_CODES); this
// copy only drives the live display before submit.
const CLASSIFICATION_CODES = {
  "Teaching Only": "40",
  "Research Only": "41",
  "Teaching & Research": "42",
  Other: "43",
};
document.querySelectorAll('select[name$="_classification"]').forEach((sel) => {
  const codeInput = document.querySelector('input[name="' + sel.name + '_code"]');
  const codeDisplay = document.getElementById(sel.name + "_code_display");
  const clinicalRow = document.getElementById(sel.name + "_clinical_row");
  function sync() {
    const code = CLASSIFICATION_CODES[sel.value] || "";
    if (codeInput) codeInput.value = code;
    if (codeDisplay) codeDisplay.textContent = code || "—";
    if (clinicalRow) clinicalRow.hidden = sel.value !== "Other";
  }
  sel.addEventListener("change", sync);
  sync();
});

// Working pattern: live total, and (where a weekly-hours field is named) require an
// entered pattern to add up to that weekly total before the form can be submitted.
document.querySelectorAll("[data-workpattern]").forEach((wrap) => {
  const dayInputs = wrap.querySelectorAll('input[type="number"]');
  const perWeekName = wrap.dataset.perweek;
  const perWeek = perWeekName
    ? document.querySelector('[name="' + perWeekName + '"]')
    : null;
  const note = wrap.querySelector(".wp-total");

  function update() {
    let total = 0;
    let anyFilled = false;
    dayInputs.forEach((i) => {
      if (i.value !== "") anyFilled = true;
      total += parseFloat(i.value) || 0;
    });
    const rounded = Math.round(total * 100) / 100;
    let msg = "Total: " + rounded + " hrs";
    let bad = false;
    if (perWeek && perWeek.value !== "" && anyFilled) {
      const target = parseFloat(perWeek.value) || 0;
      if (rounded !== target) {
        msg += " — must equal the weekly hours (" + target + ")";
        bad = true;
      } else {
        msg += " — matches weekly hours";
      }
    }
    if (note) {
      note.textContent = msg;
      note.classList.toggle("mismatch", bad);
    }
    // Block submit while the entered pattern doesn't match the weekly total.
    dayInputs.forEach((i) =>
      i.setCustomValidity(
        bad ? "Working pattern must add up to the weekly hours." : ""
      )
    );
  }

  dayInputs.forEach((i) => i.addEventListener("input", update));
  if (perWeek) perWeek.addEventListener("input", update);
  update();
});

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
