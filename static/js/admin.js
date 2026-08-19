document.addEventListener('DOMContentLoaded', function () {
  var i18n = window.VeloraI18n || {};
  var storageKey = 'adminSidebarCollapsed';
  var body = document.body;
  var toggleButton = document.getElementById('adminSidebarToggle');
  var sidebar = document.getElementById('adminSidebar');
  var overlay = document.getElementById('adminSidebarOverlay');
  var desktopMedia = window.matchMedia('(min-width: 992px)');

  if (!toggleButton || !sidebar || !overlay) {
    return;
  }

  function isCollapsedPreference() {
    return window.localStorage.getItem(storageKey) === 'true';
  }

  function setAriaExpanded(expanded) {
    toggleButton.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  }

  function syncOverlay() {
    var visible = body.classList.contains('admin-sidebar-open') && !desktopMedia.matches;
    overlay.hidden = !visible;
    overlay.classList.toggle('is-visible', visible);
  }

  function applyState() {
    if (desktopMedia.matches) {
      body.classList.remove('admin-sidebar-open');
      body.classList.toggle('admin-sidebar-collapsed', isCollapsedPreference());
      setAriaExpanded(!body.classList.contains('admin-sidebar-collapsed'));
    } else {
      body.classList.remove('admin-sidebar-collapsed');
      setAriaExpanded(body.classList.contains('admin-sidebar-open'));
    }

    syncOverlay();
  }

  function toggleSidebar() {
    if (desktopMedia.matches) {
      var shouldCollapse = !body.classList.contains('admin-sidebar-collapsed');
      body.classList.toggle('admin-sidebar-collapsed', shouldCollapse);
      window.localStorage.setItem(storageKey, shouldCollapse ? 'true' : 'false');
      setAriaExpanded(!shouldCollapse);
    } else {
      var willOpen = !body.classList.contains('admin-sidebar-open');
      body.classList.toggle('admin-sidebar-open', willOpen);
      setAriaExpanded(willOpen);
    }

    syncOverlay();
  }

  function closeMobileSidebar() {
    if (!desktopMedia.matches && body.classList.contains('admin-sidebar-open')) {
      body.classList.remove('admin-sidebar-open');
      setAriaExpanded(false);
      syncOverlay();
      toggleButton.focus();
    }
  }

  function updateSidebarBadge(selector, count) {
    var badge = document.querySelector(selector);
    if (!badge) {
      return;
    }

    badge.hidden = !count;
    var text = badge.querySelector('.admin-nav-badge-text');
    if (text) {
      text.textContent = count;
    }
  }

  function updateSidebarMeta(count) {
    var meta = document.querySelector('[data-sidebar-inprogress-meta]');
    if (!meta) {
      return;
    }

    meta.hidden = !count;
    meta.textContent = count;
  }

  function updateOrderRow(row, status) {
    var statusCell = row.querySelector('[data-order-status-cell]');
    var actions = row.querySelector('[data-order-actions]');
    if (statusCell) {
      statusCell.innerHTML = '<span class="admin-status-badge admin-status-' + status.toLowerCase().replace(/\s+/g, '-') + '">' + status + '</span>';
    }
    if (actions) {
      actions.querySelectorAll('[data-ajax-order-action]').forEach(function (form) {
        if ((status === 'In Progress' && form.dataset.orderActionType === 'in-progress') ||
            (status === 'Completed' && (form.dataset.orderActionType === 'in-progress' || form.dataset.orderActionType === 'completed'))) {
          form.remove();
        }
      });
    }
  }

  function updateInquiryRow(row, isRead, deleted) {
    if (deleted) {
      row.remove();
      return;
    }

    var statusCell = row.querySelector('[data-inquiry-status-cell]');
    if (statusCell && isRead) {
      statusCell.innerHTML = '<span class="badge bg-secondary">Read</span>';
    }

    row.querySelectorAll('[data-inquiry-action-type="mark-read"]').forEach(function (form) {
      form.remove();
    });
  }

  toggleButton.addEventListener('click', toggleSidebar);
  overlay.addEventListener('click', closeMobileSidebar);

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      closeMobileSidebar();
    }
  });

  document.body.addEventListener('submit', async function (event) {
    var form = event.target;
    if (!form) {
      return;
    }

    if (form.matches('[data-ajax-order-action], [data-ajax-inquiry-action]')) {
      event.preventDefault();

      var button = form.querySelector('button[type="submit"]');
      AppAjax.setLoading(button, true);

      try {
        var payload = await AppAjax.request(form.action, { method: 'POST', form: form });
        updateSidebarBadge('[data-sidebar-pending-badge]', payload.pending_orders_count || 0);
        updateSidebarBadge('[data-sidebar-unread-badge]', payload.unread_inquiries_count || 0);
        updateSidebarMeta(payload.in_progress_orders_count || 0);

        var orderRow = form.closest('[data-order-row]');
        if (orderRow && payload.status) {
          updateOrderRow(orderRow, payload.status);
        }

        var inquiryRow = form.closest('[data-inquiry-row]');
        if (inquiryRow) {
          updateInquiryRow(inquiryRow, payload.is_read, payload.deleted);
        }

        AppAjax.showToast(i18n.saved || 'Saved', payload.message || '', false);
      } catch (error) {
        AppAjax.showToast(i18n.request_failed || 'Request failed', error.message, true);
      } finally {
        AppAjax.setLoading(button, false);
      }
    }
  });

  desktopMedia.addEventListener('change', applyState);
  applyState();
});
