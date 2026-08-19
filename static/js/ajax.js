window.AppAjax = (function () {
  function t(key, fallback) {
    return (window.VeloraI18n && window.VeloraI18n[key]) || fallback;
  }
  function getMetaCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function getFormCsrfToken(form) {
    if (!form) return getMetaCsrfToken();
    var input = form.querySelector('input[name="csrf_token"]');
    return input ? input.value : getMetaCsrfToken();
  }

  function ensureToastContainer() {
    var container = document.getElementById('toastContainer');
    if (container) return container;

    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1090';
    document.body.appendChild(container);
    return container;
  }

  function showToast(title, message, isError) {
    var toastContainer = ensureToastContainer();
    var toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);
    var bgStyle = isError
      ? 'background: #991B1B; color: #FFFFFF; border: 1px solid #FCA5A5;'
      : 'background: #0B1F3A; color: #FFFFFF; border: 1.5px solid #C8A96B;';

    toastContainer.insertAdjacentHTML('beforeend',
      '<div id="' + toastId + '" class="toast align-items-center border-0 shadow-lg mb-2" role="alert" aria-live="assertive" aria-atomic="true" style="' + bgStyle + ' border-radius: 8px; font-family: inherit;">' +
        '<div class="d-flex" style="padding: 0.75rem 1rem; align-items: center;">' +
          '<div class="toast-body d-flex align-items-center gap-3" style="padding: 0; flex-grow: 1;">' +
            '<span style="font-size: 1.35rem; line-height: 1;">' + (isError ? '❌' : '✅') + '</span>' +
            '<div>' +
              '<div style="font-weight: 700; font-size: 0.9rem; color: #FFFFFF;">' + title + '</div>' +
              (message ? '<div style="font-size: 0.78rem; color: #CBD5E1; margin-top: 0.15rem;">' + message + '</div>' : '') +
            '</div>' +
          '</div>' +
          '<button type="button" class="btn-close btn-close-white ms-3" data-bs-dismiss="toast" aria-label="Close" style="opacity: 0.8;"></button>' +
        '</div>' +
      '</div>'
    );

    var toastEl = document.getElementById(toastId);
    if (window.bootstrap && window.bootstrap.Toast) {
      var bsToast = new window.bootstrap.Toast(toastEl, { delay: 3200 });
      bsToast.show();
    } else {
      toastEl.classList.add('show');
      setTimeout(function () {
        toastEl.classList.remove('show');
        setTimeout(function () { toastEl.remove(); }, 300);
      }, 3200);
    }
  }

  function setLoading(button, isLoading, loadingText) {
    if (!button) return;
    if (isLoading) {
      button.dataset.originalHtml = button.innerHTML;
      button.disabled = true;
      button.classList.add('is-loading');
      button.innerHTML = loadingText || button.dataset.loadingText || t('loading', 'Loading...');
      return;
    }

    button.disabled = false;
    button.classList.remove('is-loading');
    if (button.dataset.originalHtml) {
      button.innerHTML = button.dataset.originalHtml;
      delete button.dataset.originalHtml;
    }
  }

  async function request(url, options) {
    var opts = options || {};
    var method = opts.method || 'GET';
    var headers = Object.assign({
      'X-Requested-With': 'XMLHttpRequest',
      'Accept': 'application/json'
    }, opts.headers || {});

    var fetchOptions = {
      method: method,
      headers: headers,
      credentials: 'same-origin'
    };

    if (opts.form) {
      fetchOptions.body = new FormData(opts.form);
      headers['X-CSRFToken'] = getFormCsrfToken(opts.form);
    } else if (opts.data) {
      fetchOptions.headers['Content-Type'] = 'application/json';
      headers['X-CSRFToken'] = opts.csrfToken || getMetaCsrfToken();
      fetchOptions.body = JSON.stringify(opts.data);
    }

    var response = await fetch(url, fetchOptions);
    var payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      payload = { success: false, message: t('invalid_server_response', 'Invalid server response.') };
    }

    if (!response.ok) {
      throw new Error(payload.message || (t('request_failed', 'Request failed') + ' (' + response.status + ')'));
    }

    return payload;
  }

  return {
    getMetaCsrfToken: getMetaCsrfToken,
    getFormCsrfToken: getFormCsrfToken,
    showToast: showToast,
    setLoading: setLoading,
    request: request
  };
})();
