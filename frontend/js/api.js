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
      if (res.status === 401) {
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
  me: function() { return this.get('/me'); },

  // Setup
  setDisplayName: function(v) { return this.post('/select-display-name', { value: v }); },
  setDressedUpAs: function(v) { return this.post('/select-dressed-up-as', { value: v }); },

  // Costumes
  uploadCostume: function(file) {
    var fd = new FormData();
    fd.append('file', file);
    return this.upload('/upload-costume', fd);
  },
  deleteCostume: function() { return this.del('/costume'); },
  getCostumes: function() { return this.get('/costumes'); },

  // Voting
  vote: function(id) { return this.post('/vote', { costume_id: id }); },
  unvote: function(id) { return this.post('/unvote', { costume_id: id }); },
  getVotingStatus: function() { return this.get('/voting-status'); },
  getResults: function() { return this.get('/results'); },

  // Admin
  toggleVoting: function() { return this.post('/admin/toggle-voting'); },
  toggleResults: function() { return this.post('/admin/toggle-result-visibility'); },

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
