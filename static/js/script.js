// ==========================================================================
// FoodieHub - client-side interactions
// ==========================================================================

document.addEventListener('DOMContentLoaded', function () {
  autoDismissToasts();
  initAddToCartButtons();
  initCartControls();
  initMenuFilters();
  initOrderStatusControls();
  initFoodAvailabilityToggle();
  initPasswordToggles();
});

// -- Auto-dismiss flash toasts after a few seconds -------------------------
function autoDismissToasts() {
  document.querySelectorAll('.fh-toast').forEach(function (toast, i) {
    setTimeout(function () {
      const alertInstance = bootstrap.Alert.getOrCreateInstance(toast);
      alertInstance.close();
    }, 4500 + i * 300);
  });
}

// -- Small helper to show an ephemeral toast --------------------------------
function showToast(message, type) {
  type = type || 'success';
  const wrap = document.querySelector('.fh-flash-wrap');
  if (!wrap) return;
  const icon = type === 'success' ? 'fa-circle-check' : (type === 'danger' ? 'fa-circle-exclamation' : 'fa-circle-info');
  const div = document.createElement('div');
  div.className = `fh-toast alert alert-${type} alert-dismissible fade show`;
  div.setAttribute('role', 'alert');
  div.innerHTML = `<i class="fa-solid ${icon} me-2"></i>${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
  wrap.appendChild(div);
  setTimeout(function () {
    bootstrap.Alert.getOrCreateInstance(div).close();
  }, 3500);
}

// -- Add to cart (used on menu / home cards) --------------------------------
function initAddToCartButtons() {
  document.querySelectorAll('.fh-add-btn[data-food-id]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (btn.disabled) return;
      const foodId = btn.getAttribute('data-food-id');
      const original = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="fh-loading-spinner"></span>';

      fetch('/cart/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: `food_id=${encodeURIComponent(foodId)}&quantity=1`,
      })
        .then(function (res) {
          if (res.status === 401) {
            window.location.href = '/login';
            return null;
          }
          return res.json();
        })
        .then(function (data) {
          if (!data) return;
          btn.innerHTML = original;
          btn.disabled = false;
          if (data.success) {
            showToast(data.message, 'success');
            document.querySelectorAll('.fh-cart-badge').forEach(function (b) { b.textContent = data.cart_count; b.style.display = 'flex'; });
            if (data.cart_count > 0) {
              let badge = document.querySelector('.fh-cart-badge');
              if (!badge) {
                const cartLink = document.querySelector('.fh-cart-link');
                if (cartLink) {
                  badge = document.createElement('span');
                  badge.className = 'fh-cart-badge';
                  cartLink.appendChild(badge);
                }
              }
              if (badge) badge.textContent = data.cart_count;
            }
          } else {
            showToast(data.message || 'Something went wrong.', 'danger');
          }
        })
        .catch(function () {
          btn.innerHTML = original;
          btn.disabled = false;
          showToast('Network error. Please try again.', 'danger');
        });
    });
  });
}

// -- Cart page quantity controls --------------------------------------------
function initCartControls() {
  document.querySelectorAll('.fh-qty-control [data-action]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const itemId = btn.getAttribute('data-item-id');
      const action = btn.getAttribute('data-action');
      const row = document.querySelector(`.fh-cart-item[data-item-id="${itemId}"]`);

      fetch('/cart/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: `item_id=${itemId}&action=${action}`,
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (!data.success) return;

          if (data.removed) {
            if (row) row.remove();
          } else if (row) {
            const qtyEl = row.querySelector('.fh-qty-control span');
            const subtotalEl = row.querySelector('.fh-item-subtotal');
            if (action === 'increase' && qtyEl) qtyEl.textContent = parseInt(qtyEl.textContent) + 1;
            if (action === 'decrease' && qtyEl) qtyEl.textContent = Math.max(0, parseInt(qtyEl.textContent) - 1);
            if (subtotalEl) subtotalEl.textContent = '₹' + data.item_subtotal.toFixed(2);
          }

          updateCartSummary(data.summary);
          document.querySelectorAll('.fh-cart-badge').forEach(function (b) { b.textContent = data.cart_count; });

          const remaining = document.querySelectorAll('.fh-cart-item').length;
          if (remaining === 0) {
            const container = document.getElementById('cartItemsList');
            if (container) {
              container.innerHTML = `
                <div class="fh-empty-state">
                  <i class="fa-solid fa-cart-shopping"></i>
                  <h5>Your cart is empty</h5>
                  <p>Looks like you haven't added anything yet.</p>
                  <a href="/menu" class="fh-btn fh-btn-primary mt-2">Browse Menu</a>
                </div>`;
            }
          }
        });
    });
  });
}

function updateCartSummary(summary) {
  if (!summary) return;
  const map = {
    'sum-subtotal': summary.subtotal,
    'sum-delivery': summary.delivery_fee,
    'sum-tax': summary.tax,
    'sum-total': summary.total,
  };
  Object.keys(map).forEach(function (id) {
    const el = document.getElementById(id);
    if (el) el.textContent = '₹' + map[id].toFixed(2);
  });
  const checkoutBtn = document.getElementById('proceedCheckoutBtn');
  if (checkoutBtn) {
    if (summary.subtotal <= 0) {
      checkoutBtn.classList.add('disabled');
      checkoutBtn.setAttribute('tabindex', '-1');
    } else {
      checkoutBtn.classList.remove('disabled');
      checkoutBtn.removeAttribute('tabindex');
    }
  }
}

// -- Menu page: client-side chip filters (category / veg) + form submit -----
function initMenuFilters() {
  document.querySelectorAll('.fh-chip-filter[data-category]').forEach(function (chip) {
    chip.addEventListener('click', function () {
      const category = chip.getAttribute('data-category');
      const url = new URL(window.location.href);
      if (category === 'all') {
        url.searchParams.delete('category');
      } else {
        url.searchParams.set('category', category);
      }
      window.location.href = url.toString();
    });
  });

  const sortSelect = document.getElementById('sortSelect');
  if (sortSelect) {
    sortSelect.addEventListener('change', function () {
      const url = new URL(window.location.href);
      if (sortSelect.value) {
        url.searchParams.set('sort', sortSelect.value);
      } else {
        url.searchParams.delete('sort');
      }
      window.location.href = url.toString();
    });
  }

  const vegToggle = document.getElementById('vegOnlyToggle');
  if (vegToggle) {
    vegToggle.addEventListener('change', function () {
      const url = new URL(window.location.href);
      if (vegToggle.checked) {
        url.searchParams.set('veg_only', '1');
      } else {
        url.searchParams.delete('veg_only');
      }
      window.location.href = url.toString();
    });
  }
}

// -- Admin: update order status via AJAX -------------------------------------
function initOrderStatusControls() {
  document.querySelectorAll('.fh-status-select').forEach(function (select) {
    select.addEventListener('change', function () {
      const orderId = select.getAttribute('data-order-id');
      const newStatus = select.value;
      const badge = document.querySelector(`.fh-status-badge[data-order-id="${orderId}"]`);

      fetch('/admin/orders/update-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `order_id=${orderId}&status=${encodeURIComponent(newStatus)}`,
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.success) {
            showToast(`Order status updated to "${data.status}".`, 'success');
            if (badge) {
              badge.textContent = data.status;
              badge.className = 'fh-status fh-status-badge ' + statusClass(data.status);
              badge.setAttribute('data-order-id', orderId);
            }
          } else {
            showToast('Could not update order status.', 'danger');
          }
        });
    });
  });
}

function statusClass(status) {
  switch (status) {
    case 'Order Placed': return 's-placed';
    case 'Preparing': return 's-preparing';
    case 'Out for Delivery': return 's-transit';
    case 'Delivered': return 's-delivered';
    default: return 's-placed';
  }
}

// -- Admin: toggle food availability -----------------------------------------
function initFoodAvailabilityToggle() {
  document.querySelectorAll('.fh-avail-toggle').forEach(function (toggle) {
    toggle.addEventListener('change', function () {
      const foodId = toggle.getAttribute('data-food-id');
      fetch(`/admin/food/toggle/${foodId}`, { method: 'POST' })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.success) {
            showToast(data.is_available ? 'Item marked available.' : 'Item marked unavailable.', 'success');
          }
        });
    });
  });
}

// -- Password show/hide toggles ----------------------------------------------
function initPasswordToggles() {
  document.querySelectorAll('.fh-pw-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (!input) return;
      const icon = btn.querySelector('i');
      if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
      } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
      }
    });
  });
}

// -- Delete confirmation helper (used by admin food delete forms) -----------
function confirmDelete(message) {
  return window.confirm(message || 'Are you sure you want to delete this item? This cannot be undone.');
}
