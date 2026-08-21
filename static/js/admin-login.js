document.addEventListener('DOMContentLoaded', function () {
  var passwordInput = document.getElementById('password');
  var passwordToggle = document.getElementById('passwordToggle');

  if (!passwordInput || !passwordToggle) {
    return;
  }

  passwordToggle.addEventListener('click', function () {
    var isVisible = passwordInput.type === 'text';
    passwordInput.type = isVisible ? 'password' : 'text';
    passwordToggle.setAttribute('aria-label', isVisible ? 'Show password' : 'Hide password');
    passwordToggle.setAttribute('aria-pressed', isVisible ? 'false' : 'true');

    var icon = passwordToggle.querySelector('i');
    icon.classList.toggle('bi-eye', isVisible);
    icon.classList.toggle('bi-eye-slash', !isVisible);
  });
});