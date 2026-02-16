var API = {
  token: localStorage.getItem('token'),

  request: function(method, path, body, isFormData) {
    var headers = {};
    if (this.token) headers['Authorization'] = 'Bearer ' + this.token;
    if (body && !isFormData) headers['Content-Type'] = 'application/json';

    var opts = { method: method, headers: headers };
    if (body) opts.body = isFormData ? body : JSON.stringify(body);

    var self = this;
    return fetch('/api' + path, opts).then(function(res) {
      if (res.status === 401 && path !== '/login') {
        self.logout();
        return Promise.reject({ status: 401, detail: 'Session expired' });
      }
      return res.json().then(function(data) {
        if (!res.ok) return Promise.reject({ status: res.status, detail: data.detail || 'Something went wrong' });
        return data;
      });
    });
  },

  get: function(path) { return this.request('GET', path); },
  post: function(path, body) { return this.request('POST', path, body); },
  del: function(path) { return this.request('DELETE', path); },
  upload: function(path, formData) { return this.request('POST', path, formData, true); },

  // Auth
  login: function(code) { return this.post('/login', { access_code: code }); },

  // Load a script dynamically, returns a Promise
  loadScript: function(src) {
    return new Promise(function(resolve, reject) {
      var s = document.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = function() { reject(new Error('Failed to load ' + src)); };
      document.head.appendChild(s);
    });
  },

  // Token management
  setToken: function(token) {
    this.token = token;
    localStorage.setItem('token', token);
  },

  logout: function() {
    this.token = null;
    localStorage.removeItem('token');
    App.navigate('login');
  }
};
