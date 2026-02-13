var Auth = {
  init: function() {
    $('#login-form').addEventListener('submit', function(e) {
      e.preventDefault();
      hideError('login-error');
      var code = $('#login-code').value.trim();
      if (!code) return;

      var btn = $('#login-form .btn');
      btn.disabled = true;
      btn.textContent = 'Joining...';

      API.login(code).then(function(data) {
        API.setToken(data.token);
        return API.me();
      }).then(function(user) {
        App.user = user;
        App.routeAfterAuth();
      }).catch(function(err) {
        showError('login-error', err.detail || 'Invalid access code');
      }).finally(function() {
        btn.disabled = false;
        btn.textContent = 'Join the Party';
      });
    });
  }
};
