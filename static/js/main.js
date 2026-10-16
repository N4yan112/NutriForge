/* NutriForge - simple vanilla JavaScript. Each block below is one feature. */
document.addEventListener('DOMContentLoaded', function () {

  // ---- 1. Toast notifications ----
  const container = document.getElementById('toast-container');
  function showToast(message, level) {
    const colors = { success: 'bg-green-600', error: 'bg-red-600', warning: 'bg-yellow-600', info: 'bg-blue-600' };
    const toast = document.createElement('div');
    toast.className = 'toast text-white text-sm px-4 py-3 rounded-lg shadow-lg max-w-xs ' + (colors[level] || colors.info);
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 3500);
  }
  window.showToast = showToast;
  // Django flash messages -> toasts
  document.querySelectorAll('#flash-data span').forEach(function (el) {
    showToast(el.textContent, el.dataset.level);
  });

  // ---- 2. Mobile navigation menu ----
  const menuBtn = document.getElementById('menu-btn');
  if (menuBtn) {
    menuBtn.addEventListener('click', function () {
      document.getElementById('mobile-menu').classList.toggle('hidden');
    });
  }

  // ---- 3. Cart / wishlist without reloading the page (AJAX forms) ----
  function setBadge(id, count) {
    const badge = document.getElementById(id);
    if (!badge || count === undefined) return;
    badge.textContent = count;
    badge.classList.toggle('hidden', count === 0);
  }
  document.querySelectorAll('form.ajax-form').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      // "Buy now" button on the details page sets this
      const data = new FormData(form);
      if (event.submitter && event.submitter.name) data.append(event.submitter.name, event.submitter.value);
      fetch(form.action, {
        method: 'POST', body: data,
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      }).then(function (res) {
        return res.json().then(function (json) { return { status: res.status, json: json }; });
      }).then(function (r) {
        if (r.status === 401) { window.location = r.json.login_url + '?next=' + encodeURIComponent(location.pathname); return; }
        if (r.json.redirect) { window.location = r.json.redirect; return; }
        showToast(r.json.message, r.json.ok ? 'success' : 'error');
        setBadge('cart-count', r.json.cart_count);
        setBadge('wishlist-count', r.json.wishlist_count);
        const heart = form.querySelector('[data-wishlist-btn]');
        if (heart && r.json.added !== undefined) {
          heart.dataset.active = r.json.added ? 'true' : 'false';
          // On the wishlist page, un-hearting removes the card
          if (!r.json.added && form.dataset.removeCard) location.reload();
        }
      }).catch(function () { showToast('Something went wrong. Please try again.', 'error'); });
    });
  });

  // ---- 4. Quantity controls (+ / -) ----
  document.querySelectorAll('[data-qty]').forEach(function (box) {
    const input = box.querySelector('input');
    const min = parseInt(input.min || '1', 10), max = parseInt(input.max || '10', 10);
    box.querySelector('[data-dec]').addEventListener('click', function () {
      input.value = Math.max(min, (parseInt(input.value, 10) || min) - 1);
    });
    box.querySelector('[data-inc]').addEventListener('click', function () {
      input.value = Math.min(max, (parseInt(input.value, 10) || min) + 1);
    });
  });

  // ---- 5. Product image gallery ----
  const mainImg = document.getElementById('gallery-main');
  document.querySelectorAll('[data-thumb]').forEach(function (thumb) {
    thumb.addEventListener('click', function () {
      mainImg.src = thumb.dataset.thumb;
      document.querySelectorAll('[data-thumb]').forEach(function (t) { t.classList.remove('ring-2', 'ring-orange-500'); });
      thumb.classList.add('ring-2', 'ring-orange-500');
    });
  });

  // ---- 6. Confirmation dialogs ----
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  // ---- 7. Product filters: auto-submit + mobile toggle ----
  const filterForm = document.getElementById('filter-form');
  if (filterForm) {
    filterForm.querySelectorAll('select, input[type=radio]').forEach(function (el) {
      el.addEventListener('change', function () { filterForm.submit(); });
    });
  }
  const sortSelect = document.getElementById('sort-select');
  if (sortSelect) sortSelect.addEventListener('change', function () { sortSelect.form.submit(); });
  const filterToggle = document.getElementById('filter-toggle');
  if (filterToggle) {
    filterToggle.addEventListener('click', function () {
      document.getElementById('filter-panel').classList.toggle('hidden');
    });
  }

  // ---- 8. Live search suggestions ----
  const searchInput = document.getElementById('search-input');
  const box = document.getElementById('suggest-box');
  let timer = null;
  if (searchInput && box) {
    searchInput.addEventListener('input', function () {
      clearTimeout(timer);
      const q = searchInput.value.trim();
      if (q.length < 2) { box.classList.add('hidden'); return; }
      timer = setTimeout(function () {       // wait until the user pauses typing
        fetch('/products/suggest/?q=' + encodeURIComponent(q)).then(function (r) { return r.json(); }).then(function (data) {
          box.innerHTML = '';
          data.results.forEach(function (item) {
            const a = document.createElement('a');
            a.href = item.url;
            a.className = 'flex justify-between px-4 py-2 text-sm hover:bg-orange-50';
            a.innerHTML = '<span></span><span class="text-gray-500">₹' + item.price + '</span>';
            a.firstChild.textContent = item.name;
            box.appendChild(a);
          });
          box.classList.toggle('hidden', data.results.length === 0);
        });
      }, 250);
    });
    document.addEventListener('click', function (e) { if (!box.contains(e.target)) box.classList.add('hidden'); });
  }

  // ---- 9. Simple client-side form validation (the server validates again) ----
  document.querySelectorAll('form[data-validate]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      let valid = true;
      form.querySelectorAll('.js-error').forEach(function (e) { e.remove(); });
      form.querySelectorAll('input[name$="phone"], input[name$="pincode"], input[type=email]').forEach(function (input) {
        if (!input.value) return;
        let ok = true, msg = '';
        if (input.name.endsWith('phone')) { ok = /^\d{10}$/.test(input.value); msg = 'Enter a 10-digit phone number.'; }
        if (input.name.endsWith('pincode')) { ok = /^\d{6}$/.test(input.value); msg = 'Enter a 6-digit pincode.'; }
        if (input.type === 'email') { ok = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.value); msg = 'Enter a valid email.'; }
        if (!ok) {
          valid = false;
          const p = document.createElement('p');
          p.className = 'js-error text-sm text-red-600 mt-1';
          p.textContent = msg;
          input.insertAdjacentElement('afterend', p);
        }
      });
      if (!valid) { event.preventDefault(); showToast('Please fix the highlighted fields.', 'error'); }
    });
  });

  // ---- 10. Checkout: show/hide the new-address form ----
  const newAddr = document.getElementById('new-address-form');
  if (newAddr) {
    const radios = document.querySelectorAll('input[name=address]');
    const toggle = function () {
      const checked = document.querySelector('input[name=address]:checked');
      newAddr.classList.toggle('hidden', !!(checked && checked.value));
    };
    radios.forEach(function (r) { r.addEventListener('change', toggle); });
    toggle();
  }
});
