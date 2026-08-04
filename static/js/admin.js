document.addEventListener('DOMContentLoaded', function () {
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

  toggleButton.addEventListener('click', toggleSidebar);
  overlay.addEventListener('click', closeMobileSidebar);

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      closeMobileSidebar();
    }
  });

  desktopMedia.addEventListener('change', applyState);
  applyState();
});
