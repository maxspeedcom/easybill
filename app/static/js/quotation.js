// ThaiBill - Quotation form logic
(function () {
  const tbody = document.getElementById('items-body');
  const discountInput = document.getElementById('discount_amount');
  const vatInput = document.getElementById('vat_rate');
  const vatIncCheck = document.getElementById('price_includes_vat');

  // ---------- Helpers ----------
  function fmt(n) {
    if (n === null || n === undefined || isNaN(n)) return '0.00';
    return Number(n).toLocaleString('th-TH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // ---------- Row management ----------
  window.addRow = function (prefill) {
    const tr = document.createElement('tr');
    tr.className = 'qt-row';
    tr.innerHTML = `
      <td class="col-no row-no"></td>
      <td>
        <input type="hidden" name="item_product_id[]" value="${prefill?.id || ''}">
        <input type="hidden" name="item_code[]" value="${prefill?.code || ''}">
        <input class="item-name" name="item_name[]" value="${prefill?.name || ''}" placeholder="ค้นหาสินค้า หรือพิมพ์ชื่อ" autocomplete="off">
        <textarea name="item_description[]" rows="1" placeholder="รายละเอียดเพิ่มเติม (ไม่บังคับ)">${prefill?.description || ''}</textarea>
      </td>
      <td><input class="item-qty" type="number" step="0.001" name="item_quantity[]" value="1"></td>
      <td><input class="item-unit" name="item_unit[]" value="${prefill?.unit || 'ชิ้น'}"></td>
      <td><input class="item-price input--money" type="number" step="0.01" name="item_unit_price[]" value="${prefill?.price || 0}"></td>
      <td><input class="item-disc input--money" type="number" step="0.01" name="item_discount_percent[]" value="0"></td>
      <td class="col-total item-total">0.00</td>
      <td class="col-action"><button type="button" class="qt-row-action" onclick="removeRow(this)"><svg viewBox="0 0 24 24"><path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6zM19 4h-3.5l-1-1h-5l-1 1H5v2h14z"/></svg></button></td>
    `;
    tbody.appendChild(tr);
    bindRow(tr);
    renumber();
    recalc();
    tr.querySelector('.item-name').focus();
    return tr;
  };

  window.removeRow = function (btn) {
    const tr = btn.closest('tr');
    tr.remove();
    if (tbody.children.length === 0) addRow();
    renumber();
    recalc();
  };

  function renumber() {
    Array.from(tbody.querySelectorAll('.row-no')).forEach((td, i) => td.textContent = i + 1);
  }

  // ---------- Calculation ----------
  function recalc() {
    let subtotal = 0;
    tbody.querySelectorAll('tr').forEach(tr => {
      const qtyEl   = tr.querySelector('.item-qty');
      const priceEl = tr.querySelector('.item-price');
      const discEl  = tr.querySelector('.item-disc') || tr.querySelector('input[name="item_discount_percent[]"]');
      const totalEl = tr.querySelector('.item-total');
      if (!qtyEl || !priceEl) return;
      const qty   = parseFloat(qtyEl.value)   || 0;
      const price = parseFloat(priceEl.value) || 0;
      const disc  = parseFloat(discEl ? discEl.value : 0) || 0;
      const gross = qty * price;
      const total = gross - (gross * disc / 100);
      if (totalEl) totalEl.textContent = fmt(total);
      subtotal += total;
    });

    const discountAmt = parseFloat(discountInput ? discountInput.value : 0) || 0;
    let afterDisc = subtotal - discountAmt;
    if (afterDisc < 0) afterDisc = 0;

    const vatRate = parseFloat(vatInput ? vatInput.value : 0) || 0;
    let vatAmount, grand, base;
    if (vatIncCheck && vatIncCheck.checked) {
      grand = afterDisc;
      base = vatRate ? afterDisc * 100 / (100 + vatRate) : afterDisc;
      vatAmount = grand - base;
      afterDisc = base;
    } else {
      vatAmount = afterDisc * vatRate / 100;
      grand = afterDisc + vatAmount;
    }

    const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setText('t-subtotal',       fmt(subtotal));
    setText('t-after-discount', fmt(afterDisc));
    setText('t-vat',            fmt(vatAmount));
    setText('t-grand',          fmt(grand));
    setText('t-vat-rate-display', vatRate);
    setText('t-baht-text',      '(' + bahtText(grand) + ')');
  }

  // ---------- Thai number to baht text ----------
  const TH_DIGITS = ['ศูนย์', 'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า'];
  const TH_PLACES = ['', 'สิบ', 'ร้อย', 'พัน', 'หมื่น', 'แสน', 'ล้าน'];

  function readInt(s) {
    s = s.replace(/^0+/, '') || '0';
    if (s === '0') return 'ศูนย์';
    if (s.length > 7) {
      const head = s.slice(0, -6), tail = s.slice(-6);
      return readInt(head) + 'ล้าน' + (tail.replace(/^0+/, '') ? readInt(tail) : '');
    }
    let result = '';
    const L = s.length;
    for (let i = 0; i < L; i++) {
      const d = +s[i];
      const place = L - i - 1;
      if (d === 0) continue;
      if (place === 0 && d === 1 && L > 1) result += 'เอ็ด';
      else if (place === 1 && d === 2) result += 'ยี่' + TH_PLACES[place];
      else if (place === 1 && d === 1) result += TH_PLACES[place];
      else result += TH_DIGITS[d] + TH_PLACES[place];
    }
    return result;
  }

  function bahtText(amount) {
    if (isNaN(amount)) return '';
    if (amount < 0) return 'ลบ' + bahtText(-amount);
    const i = Math.floor(amount);
    const frac = Math.round((amount - i) * 100);
    let txt = i > 0 ? readInt(String(i)) + 'บาท' : '';
    if (frac === 0) return (txt || 'ศูนย์บาท') + 'ถ้วน';
    return (txt || '') + readInt(String(frac)) + 'สตางค์';
  }

  // ---------- Row bindings (autocomplete + recalc) ----------
  function bindRow(tr) {
    tr.querySelectorAll('input, textarea').forEach(inp => {
      if (inp.classList.contains('item-name')) return;
      inp.addEventListener('input', recalc);
    });

    // Product autocomplete on item-name
    const nameInput = tr.querySelector('.item-name');
    if (!nameInput) return;
    const codeInput = tr.querySelector('input[name="item_code[]"]');
    const productIdInput = tr.querySelector('input[name="item_product_id[]"]');
    // textarea หรือ hidden input ทั้งคู่ใช้ชื่อเดียวกัน
    const descInput = tr.querySelector('textarea[name="item_description[]"], input[name="item_description[]"]');
    // .item-unit อาจเป็น hidden ไม่มี class — fallback ไปหา name
    const unitInput = tr.querySelector('.item-unit') || tr.querySelector('input[name="item_unit[]"]');
    const priceInput = tr.querySelector('.item-price');

    setupAutocomplete(nameInput, '/products/api/search', (item) => {
      try {
        nameInput.value = item.name;
        if (codeInput) codeInput.value = item.code || '';
        if (productIdInput) productIdInput.value = item.id;
        if (descInput && !descInput.value) descInput.value = item.description || '';
        if (unitInput) unitInput.value = item.unit || 'ชิ้น';
        if (priceInput) priceInput.value = item.price || 0;
        recalc();
      } catch (err) {
        console.error('autocomplete fill error:', err);
      }
    });
  }

  // ---------- Customer select (native dropdown) ----------
  const customerSelect = document.getElementById('customer_id');
  const customerMeta = document.getElementById('customer-meta');
  if (customerSelect) {
    const updateMeta = () => {
      const opt = customerSelect.options[customerSelect.selectedIndex];
      if (!opt || !opt.value) { customerMeta.textContent = ''; return; }
      const meta = [];
      const taxId = opt.dataset.taxId;
      const branch = opt.dataset.branch;
      const phone = opt.dataset.phone;
      if (taxId) meta.push('เลขผู้เสียภาษี ' + taxId);
      if (branch) meta.push(branch);
      if (phone) meta.push('โทร. ' + phone);
      customerMeta.textContent = meta.join(' · ');
    };
    customerSelect.addEventListener('change', updateMeta);
    updateMeta();  // init for already-selected
  }

  // ---------- Init ----------
  if (!tbody) return;  // ไม่มี items table → ไม่ใช่หน้า form
  if (tbody.children.length === 0) {
    addRow();
  } else {
    Array.from(tbody.children).forEach(tr => bindRow(tr));
    renumber();
    recalc();
  }

  if (discountInput) discountInput.addEventListener('input', recalc);
  if (vatInput)      vatInput.addEventListener('input', recalc);
  if (vatIncCheck)   vatIncCheck.addEventListener('change', recalc);

  // Validate before submit
  const qtForm = document.getElementById('qt-form');
  if (qtForm) {
    qtForm.addEventListener('submit', (e) => {
      if (!customerSelect || !customerSelect.value) {
        e.preventDefault();
        alert('กรุณาเลือกลูกค้า');
        if (customerSelect) customerSelect.focus();
        return;
      }
      const hasItem = Array.from(tbody.querySelectorAll('.item-name')).some(i => i.value.trim());
      if (!hasItem) {
        e.preventDefault();
        alert('กรุณาเพิ่มอย่างน้อย 1 รายการ');
      }
    });
  }
})();
