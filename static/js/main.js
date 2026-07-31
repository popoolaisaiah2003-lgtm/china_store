// Yan Zhen Peptide - Chinese Biotech Interactivity & Modal Checkout Workflow

document.addEventListener('DOMContentLoaded', () => {
  // Mobile Navigation Toggle
  const mobileToggle = document.getElementById('mobileNavToggle');
  const navLinks = document.getElementById('navLinks');

  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener('click', () => {
      navLinks.classList.toggle('active');
    });
  }

  // Language Persistence
  const currentLangMatch = window.location.pathname.match(/\/set_language\/([a-z]{2})/);
  if (currentLangMatch && currentLangMatch[1]) {
    localStorage.setItem('yz_language', currentLangMatch[1]);
  }

  // Stackable Toast Notification Helper
  const toastContainer = document.getElementById('toastContainer');

  function showToast(title, message = '', isError = false) {
    if (!toastContainer) return;

    const toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6);
    const bgStyle = isError 
      ? 'background: #991B1B; color: #FFFFFF; border: 1px solid #FCA5A5;' 
      : 'background: #0B1F3A; color: #FFFFFF; border: 1.5px solid #C8A96B;';

    const toastHTML = `
      <div id="${toastId}" class="toast align-items-center border-0 shadow-lg mb-2" role="alert" aria-live="assertive" aria-atomic="true" style="${bgStyle} border-radius: 8px; font-family: inherit;">
        <div class="d-flex" style="padding: 0.75rem 1rem; align-items: center;">
          <div class="toast-body d-flex align-items-center gap-3" style="padding: 0; flex-grow: 1;">
            <span style="font-size: 1.35rem; line-height: 1;">${isError ? '❌' : '📋'}</span>
            <div>
              <div style="font-weight: 700; font-size: 0.9rem; color: #FFFFFF;">${title}</div>
              ${message ? `<div style="font-size: 0.78rem; color: #CBD5E1; margin-top: 0.15rem;">${message}</div>` : ''}
            </div>
          </div>
          <button type="button" class="btn-close btn-close-white ms-3" data-bs-dismiss="toast" aria-label="Close" style="opacity: 0.8;"></button>
        </div>
      </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastEl = document.getElementById(toastId);

    if (window.bootstrap && bootstrap.Toast) {
      const bsToast = new bootstrap.Toast(toastEl, { delay: 3500 });
      bsToast.show();
    } else {
      toastEl.classList.add('show');
      setTimeout(() => {
        toastEl.classList.remove('show');
        setTimeout(() => toastEl.remove(), 400);
      }, 3500);
    }
  }

  // Intercept all cart add forms for AJAX submission (No page reload, zero scroll jump)
  document.body.addEventListener('submit', async (e) => {
    const form = e.target;
    if (!form || !form.action || !form.action.includes('/cart/add/')) return;

    e.preventDefault();

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn ? submitBtn.innerHTML : '';

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span style="display:inline-block; animation: spin 1s linear infinite;">⏳</span> Adding...';
    }

    const ajaxUrl = form.action.replace('/cart/add/', '/cart/add-ajax/');
    const formData = new FormData(form);

    try {
      const response = await fetch(ajaxUrl, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        // Update all navbar cart badges
        const cartBadges = document.querySelectorAll('.cart-badge');
        cartBadges.forEach(badge => {
          badge.textContent = data.cart_total_count;
        });

        // Trigger stackable toast notification
        showToast(
          'Added to quotation cart', 
          `${data.quantity} × ${data.product_name}`, 
          false
        );
      } else {
        showToast('Failed to add item', data.message || 'Error updating quotation', true);
      }
    } catch (err) {
      console.error('AJAX Cart Request Failed:', err);
      showToast('Error', 'Unable to add item to quotation cart. Please try again.', true);
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
      }
    }
  });

  // Modal Trigger Logic for Checkout Flow ("Proceed to Checkout" / "Review Quotation Sheet")
  const triggerButtons = document.querySelectorAll('.trigger-order-info, .trigger-checkout-modal');
  const modalElement = document.getElementById('orderInfoModal');

  if (modalElement && window.bootstrap && bootstrap.Modal) {
    const orderModal = new bootstrap.Modal(modalElement);

    triggerButtons.forEach(btn => {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        const checkoutUrl = this.dataset.checkoutUrl || this.getAttribute('href') || '/checkout';
        
        // Always open modal popup on every click (no sessionStorage restriction)
        modalElement.dataset.checkoutUrl = checkoutUrl;
        orderModal.show();
      });
    });

    const continueBtn = document.getElementById('confirmOrderInfo') || document.getElementById('btnAcknowledgeAndContinue');

    if (continueBtn) {
      continueBtn.addEventListener('click', function () {
        // Navigate directly to checkout URL without storing any acknowledgment state
        const checkoutUrl = modalElement.dataset.checkoutUrl || '/checkout';
        window.location.href = checkoutUrl;
      });
    }
  }
});
