// ThaiBill - common JS

// Dropdown toggles
document.addEventListener('click', (e) => {
  const trig = e.target.closest('[data-dropdown]');
  if (trig) {
    e.preventDefault();
    const dd = trig.closest('.dropdown');
    document.querySelectorAll('.dropdown.open').forEach(d => { if (d !== dd) d.classList.remove('open'); });
    dd.classList.toggle('open');
    return;
  }
  document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
});

// Auto-dismiss flash after 5s
document.querySelectorAll('.flash').forEach(f => {
  setTimeout(() => f.style.opacity = '0.4', 5000);
});

// Confirm delete forms
document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', (e) => {
    if (!confirm(form.dataset.confirm)) e.preventDefault();
  });
});

// Money formatting helper
window.fmtMoney = function(n) {
  if (n === null || n === undefined || isNaN(n)) return '0.00';
  return Number(n).toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// Simple autocomplete factory
window.setupAutocomplete = function(input, endpoint, onSelect) {
  const wrap = input.closest('.ac-wrap') || (() => {
    const w = document.createElement('div');
    w.className = 'ac-wrap';
    w.style.position = 'relative';
    input.parentNode.insertBefore(w, input);
    w.appendChild(input);
    return w;
  })();
  let resultsEl = null;
  let timer = null;

  const close = () => { if (resultsEl) { resultsEl.remove(); resultsEl = null; } };

  const doSearch = () => {
    clearTimeout(timer);
    const q = input.value.trim();
    timer = setTimeout(() => {
      fetch(endpoint + '?q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(items => {
          close();
          if (!items.length) return;
          resultsEl = document.createElement('div');
          resultsEl.className = 'autocomplete-results';
          items.forEach(it => {
            const el = document.createElement('div');
            el.className = 'autocomplete-item';
            el.innerHTML = `<div>${it.name}</div><div class="sub">${it.code || ''} ${it.tax_id ? '· ' + it.tax_id : ''}</div>`;
            el.addEventListener('mousedown', (e) => {
              e.preventDefault();
              onSelect(it);
              close();
            });
            resultsEl.appendChild(el);
          });
          wrap.appendChild(resultsEl);
        })
        .catch(close);
    }, 200);
  };

  input.addEventListener('input', doSearch);
  input.addEventListener('focus', doSearch);  // แสดงรายการแรกๆ ทันทีเมื่อ focus

  input.addEventListener('blur', () => setTimeout(close, 200));
};
