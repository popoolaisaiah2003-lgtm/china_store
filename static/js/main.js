document.addEventListener('DOMContentLoaded', function () {
  var mobileToggle = document.getElementById('mobileNavToggle');
  var navLinks = document.getElementById('navLinks');
  var modalElement = document.getElementById('orderInfoModal');
  var productsGrid = document.getElementById('productsGrid');
  var productsSummaryText = document.getElementById('productsSummaryText');
  var productsLoadMoreWrap = document.getElementById('productsLoadMoreWrap');
  var orderPanel = document.getElementById('orderPanel');

  function updateCartBadges(count) {
    document.querySelectorAll('.cart-badge').forEach(function (badge) {
      badge.textContent = count;
    });
  }

  function updateWishlistButtonState(button, isFavorited) {
    if (!button) return;
    button.classList.toggle('is-active', isFavorited);
    button.setAttribute('aria-pressed', isFavorited ? 'true' : 'false');
    var icon = button.querySelector('i');
    if (icon) {
      icon.className = 'bi ' + (isFavorited ? 'bi-heart-fill' : 'bi-heart');
    }
  }

  function updateProductsPayload(payload, append) {
    if (!productsGrid) return;
    if (append) {
      productsGrid.insertAdjacentHTML('beforeend', payload.products_html);
    } else {
      productsGrid.innerHTML = payload.products_html;
    }

    productsGrid.dataset.currentPage = String(payload.page || 1);
    productsGrid.dataset.hasNext = payload.has_next ? 'true' : 'false';
    productsGrid.dataset.nextPage = payload.next_page || '';

    if (productsSummaryText) {
      productsSummaryText.textContent = 'Showing ' + payload.loaded_count + ' Products';
    }

    if (productsLoadMoreWrap) {
      if (payload.has_next) {
        var url = new URL(window.location.href);
        url.searchParams.set('page', payload.next_page);
        productsLoadMoreWrap.innerHTML = '<a href="' + url.toString() + '" class="btn btn-outline-blue" data-ajax-load-more data-loading-text="Loading more...">Load more products</a>';
      } else {
        productsLoadMoreWrap.innerHTML = '';
      }
    }
  }

  function syncProductFilterState(urlString) {
    var activeUrl = new URL(urlString, window.location.origin);
    var activeCategory = activeUrl.searchParams.get('category') || '';

    document.querySelectorAll('[data-ajax-product-filter-link]').forEach(function (link) {
      var linkUrl = new URL(link.href, window.location.origin);
      var linkCategory = linkUrl.searchParams.get('category') || '';
      link.classList.toggle('active', linkCategory === activeCategory);
    });

    document.querySelectorAll('[data-ajax-products-form]').forEach(function (form) {
      var hiddenCategory = form.querySelector('input[name="category"]');
      if (activeCategory) {
        if (!hiddenCategory) {
          hiddenCategory = document.createElement('input');
          hiddenCategory.type = 'hidden';
          hiddenCategory.name = 'category';
          form.appendChild(hiddenCategory);
        }
        hiddenCategory.value = activeCategory;
      } else if (hiddenCategory) {
        hiddenCategory.remove();
      }
    });
  }

  async function submitAjaxForm(form, successTitle) {
    var button = form.querySelector('button[type="submit"]');
    AppAjax.setLoading(button, true);
    try {
      var payload = await AppAjax.request(form.action, { method: 'POST', form: form });
      AppAjax.showToast(successTitle, payload.message || '', false);
      return payload;
    } catch (error) {
      AppAjax.showToast('Request failed', error.message, true);
      throw error;
    } finally {
      AppAjax.setLoading(button, false);
    }
  }

  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener('click', function () {
      navLinks.classList.toggle('active');
    });
  }

  var currentLangMatch = window.location.pathname.match(/\/set_language\/([a-z]{2})/);
  if (currentLangMatch && currentLangMatch[1]) {
    localStorage.setItem('yz_language', currentLangMatch[1]);
  }

  document.body.addEventListener('submit', async function (event) {
    var form = event.target;
    if (!form) return;

    if (form.matches('[data-ajax-cart-add]')) {
      event.preventDefault();
      try {
        var cartAddPayload = await submitAjaxForm(form, 'Added to quotation cart');
        updateCartBadges(cartAddPayload.cart_total_count || 0);
      } catch (error) {}
      return;
    }

    if (form.matches('[data-ajax-cart-update], [data-ajax-cart-remove]')) {
      event.preventDefault();
      try {
        var cartPayload = await submitAjaxForm(form, 'Quotation updated');
        updateCartBadges(cartPayload.cart_total_count || 0);
        if (orderPanel && cartPayload.order_panel_html) {
          orderPanel.innerHTML = cartPayload.order_panel_html;
        }
      } catch (error) {}
      return;
    }

    if (form.matches('[data-ajax-wishlist]')) {
      event.preventDefault();
      try {
        var wishlistPayload = await submitAjaxForm(form, 'Favorites updated');
        updateWishlistButtonState(form.querySelector('[data-wishlist-button]'), wishlistPayload.is_favorited);
      } catch (error) {}
      return;
    }

    if (form.matches('[data-ajax-products-form]')) {
      event.preventDefault();
      var queryUrl = new URL(form.action, window.location.origin);
      new FormData(form).forEach(function (value, key) {
        if (value) {
          queryUrl.searchParams.set(key, value);
        } else {
          queryUrl.searchParams.delete(key);
        }
      });
      queryUrl.searchParams.delete('page');
      try {
        var productsPayload = await AppAjax.request(queryUrl.toString(), { method: 'GET' });
        updateProductsPayload(productsPayload, false);
        syncProductFilterState(queryUrl.toString());
        window.history.replaceState({}, '', queryUrl.toString());
      } catch (error) {
        AppAjax.showToast('Search failed', error.message, true);
      }
    }
  });

  document.body.addEventListener('change', function (event) {
    var select = event.target;
    if (select && select.matches('[data-ajax-products-sort]')) {
      var form = select.closest('form');
      if (form) {
        form.requestSubmit();
      }
    }
  });

  document.body.addEventListener('click', async function (event) {
    var filterLink = event.target.closest('[data-ajax-product-filter-link]');
    if (filterLink) {
      event.preventDefault();
      try {
        var filterPayload = await AppAjax.request(filterLink.href, { method: 'GET' });
        updateProductsPayload(filterPayload, false);
        syncProductFilterState(filterLink.href);
        window.history.replaceState({}, '', filterLink.href);
      } catch (error) {
        AppAjax.showToast('Filter failed', error.message, true);
      }
      return;
    }

    var loadMoreButton = event.target.closest('[data-ajax-load-more]');
    if (loadMoreButton) {
      event.preventDefault();
      AppAjax.setLoading(loadMoreButton, true, loadMoreButton.dataset.loadingText);
      try {
        var loadMorePayload = await AppAjax.request(loadMoreButton.href, { method: 'GET' });
        updateProductsPayload(loadMorePayload, true);
        window.history.replaceState({}, '', loadMoreButton.href);
      } catch (error) {
        AppAjax.showToast('Load failed', error.message, true);
      } finally {
        AppAjax.setLoading(loadMoreButton, false);
      }
      return;
    }

    var triggerButton = event.target.closest('.trigger-order-info, .trigger-checkout-modal');
    if (triggerButton && modalElement && window.bootstrap && window.bootstrap.Modal) {
      event.preventDefault();
      var orderModal = window.bootstrap.Modal.getOrCreateInstance(modalElement);
      modalElement.dataset.checkoutUrl = triggerButton.dataset.checkoutUrl || triggerButton.getAttribute('href') || '/checkout';
      orderModal.show();
    }
  });

  if (modalElement) {
    var continueBtn = document.getElementById('confirmOrderInfo') || document.getElementById('btnAcknowledgeAndContinue');
    if (continueBtn) {
      continueBtn.addEventListener('click', function () {
        var checkoutUrl = modalElement.dataset.checkoutUrl || '/checkout';
        window.location.href = checkoutUrl;
      });
    }
  }
});
