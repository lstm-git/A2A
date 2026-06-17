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

// Selects flagged with data-fulltext echo the full chosen option text below the
// dropdown (for long options that the select box itself truncates).
document.querySelectorAll("select[data-fulltext]").forEach((sel) => {
  const note = sel.parentElement.querySelector(".select-fulltext");
  if (!note) return;
  function sync() {
    note.textContent = sel.value;
    note.classList.toggle("empty", sel.value === "");
  }
  sel.addEventListener("change", sync);
  sync();
});

// Position classification -> code auto-fill. Authoritative mapping lives in
// steps.py (CLASSIFICATION_CODES); this copy only drives the live display.
const CLASSIFICATION_CODES = {
  "Teaching Only": "40",
  "Research Only": "41",
  "Teaching & Research": "42",
  Other: "43",
};
document.querySelectorAll('select[name$="_classification"]').forEach((sel) => {
  const codeInput = document.querySelector('input[name="' + sel.name + '_code"]');
  const codeDisplay = document.getElementById(sel.name + "_code_display");
  function sync() {
    const code = CLASSIFICATION_CODES[sel.value] || "";
    if (codeInput) codeInput.value = code;
    if (codeDisplay) codeDisplay.textContent = code || "—";
  }
  sel.addEventListener("change", sync);
  sync();
});

// Generic conditional follow-up rows: show a wrapped row only when its trigger
// field (radio group or select) currently holds one of the configured values
// (data-show-value may list several, joined by "||"). When a row becomes hidden
// its inputs are cleared so nested conditionals collapse with it.
document.querySelectorAll("[data-show-when]").forEach((wrap) => {
  const name = wrap.dataset.showWhen;
  const values = (wrap.dataset.showValue || "").split("||");
  const controls = document.querySelectorAll('[name="' + name + '"]');
  function current() {
    const radios = [...controls].filter((c) => c.type === "radio");
    if (radios.length) {
      const checked = radios.find((r) => r.checked);
      return checked ? checked.value : "";
    }
    return controls[0] ? controls[0].value : "";
  }
  function sync() {
    const show = values.includes(current());
    if (wrap.hidden === !show) return; // no change since last sync
    wrap.hidden = !show;
    if (!show) {
      // Reset contained inputs (radios fall back to their default, if any) and
      // notify dependents so they collapse too.
      wrap.querySelectorAll("input, select, textarea").forEach((el) => {
        if (el.type === "radio" || el.type === "checkbox") {
          el.checked = el.hasAttribute("data-default");
        } else {
          el.value = "";
        }
        el.dispatchEvent(new Event("change", { bubbles: true }));
        el.dispatchEvent(new Event("input", { bubbles: true }));
      });
    }
  }
  controls.forEach((c) => c.addEventListener("change", sync));
  sync();
});

// Working pattern: live total. The pattern is required and must add up to the
// weekly target before the form can be submitted. The target is taken from a
// contract-basis select (Full-time -> the number in its label, e.g. 35) plus an
// optional part-time hours field; falling back to a named weekly-hours field.
document.querySelectorAll("[data-workpattern]").forEach((wrap) => {
  const dayInputs = wrap.querySelectorAll('input[type="number"]');
  const note = wrap.querySelector(".wp-total");
  const byName = (n) => (n ? document.querySelector('[name="' + n + '"]') : null);
  const perWeek = byName(wrap.dataset.perweek);
  const basis = byName(wrap.dataset.basis);
  const ptHours = byName(wrap.dataset.pthours);

  // Effective weekly hours to check against, or null if not yet known.
  function targetHours() {
    if (basis) {
      if (/part-time/i.test(basis.value)) {
        return ptHours && ptHours.value !== "" ? parseFloat(ptHours.value) : null;
      }
      const m = basis.value.match(/[\d.]+/); // Full-time: number in the label (35)
      return m ? parseFloat(m[0]) : null;
    }
    if (perWeek) return perWeek.value !== "" ? parseFloat(perWeek.value) : null;
    return null;
  }

  function update() {
    let total = 0;
    dayInputs.forEach((i) => (total += parseFloat(i.value) || 0));
    const rounded = Math.round(total * 100) / 100;
    const target = targetHours();
    let msg = "Total: " + rounded + " hrs";
    let bad = false;
    let validity = "";
    if (rounded === 0) {
      bad = true;
      validity = "Please enter the working pattern.";
    } else if (target != null && rounded !== target) {
      msg += " — must equal the weekly hours (" + target + ")";
      bad = true;
      validity = "Working pattern must add up to the weekly hours.";
    } else if (target != null) {
      msg += " — matches weekly hours";
    }
    if (note) {
      note.textContent = msg;
      note.classList.toggle("mismatch", bad);
    }
    dayInputs.forEach((i) => i.setCustomValidity(validity));
  }

  dayInputs.forEach((i) => i.addEventListener("input", update));
  if (perWeek) perWeek.addEventListener("input", update);
  if (basis) basis.addEventListener("change", update);
  if (ptHours) ptHours.addEventListener("input", update);
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
      const root = window.A2A_ROOT || "";
      const r = await fetch(root + "/api/users/search?q=" + encodeURIComponent(q));
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
