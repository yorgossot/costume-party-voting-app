var App = {
  currentView: null,
  user: null,

  views: {
    home:    { module: function() { return typeof Home    !== 'undefined' ? Home    : null; } },
    vote:    { module: function() { return typeof Vote    !== 'undefined' ? Vote    : null; } },
    results: { module: function() { return typeof Results !== 'undefined' ? Results : null; } },
    admin:   { module: function() { return typeof Admin   !== 'undefined' ? Admin   : null; } },
    setup:   { module: function() { return typeof Setup   !== 'undefined' ? Setup   : null; } },
  },

  init: function() {
    var self = this;

    // Init all modules
    if (typeof Auth  !== 'undefined' && Auth.init)  Auth.init();
    if (typeof Setup !== 'undefined' && Setup.init) Setup.init();
    if (typeof Vote  !== 'undefined' && Vote.init)  Vote.init();
    if (typeof Home  !== 'undefined' && Home.init)  Home.init();

    // Tab bar clicks
    $$('.tab-item').forEach(function(tab) {
      tab.addEventListener('click', function() {
        var view = tab.dataset.view;
        if (view) self.navigate(view);
      });
    });

    // Logout button
    var logoutBtn = $('#btn-logout');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', function() {
        API.logout();
      });
    }

    // Check existing session
    if (API.token) {
      showLoading();
      API.loadScript('/js/api-auth.js').then(function() {
        return API.me();
      }).then(function(user) {
        self.user = user;
        if (user.is_admin) return API.loadScript('/js/admin.js');
      }).then(function() {
        self.routeAfterAuth();
      }).catch(function() {
        API.logout();
      }).finally(function() {
        hideLoading();
      });
    } else {
      this.navigate('login');
    }
  },

  loadProtectedScripts: function(isAdmin) {
    var p = API.loadScript('/js/api-auth.js');
    if (isAdmin) p = p.then(function() { return API.loadScript('/js/admin.js'); });
    return p;
  },

  routeAfterAuth: function() {
    // Show admin tab if admin
    if (this.user && this.user.is_admin) {
      $$('.tab-admin').forEach(function(el) { el.classList.remove('hidden'); });
    }

    // Check setup completion
    if (!this.user.display_name || !this.user.dressed_up_as || !this.user.costume) {
      this.navigate('setup');
    } else {
      this.navigate('vote');
    }
  },

  navigate: function(viewName) {
    // Leave current view
    if (this.currentView) {
      var currentMod = this.views[this.currentView];
      if (currentMod) {
        var mod = currentMod.module();
        if (mod && mod.onLeave) mod.onLeave();
      }
    }

    // Hide all views, show target
    $$('.view').forEach(function(v) { v.classList.add('hidden'); });
    var target = document.getElementById('view-' + viewName);
    if (target) target.classList.remove('hidden');

    // Tab bar visibility
    var showTabs = ['home', 'vote', 'results', 'admin'].indexOf(viewName) !== -1;
    $('#tab-bar').classList.toggle('hidden', !showTabs);

    // Update active tab
    $$('.tab-item').forEach(function(t) {
      t.classList.toggle('active', t.dataset.view === viewName);
    });

    // Enter new view
    var viewDef = this.views[viewName];
    if (viewDef) {
      var mod = viewDef.module();
      if (mod && mod.onEnter) mod.onEnter();
    }

    this.currentView = viewName;
    window.scrollTo(0, 0);
  }
};

/* Home view module — defined here to keep file count manageable */
var Home = {
  init: function() {},

  competitionStatus: 'setup',

  onEnter: function() {
    var self = this;
    Promise.all([API.me(), API.getCompetitionStatus()]).then(function(results) {
      App.user = results[0];
      self.competitionStatus = results[1].status;
      self.render();
    });
  },

  render: function() {
    var u = App.user;
    var container = $('#home-content');
    var isSetup = this.competitionStatus === 'setup';

    if (!u.costume) {
      container.innerHTML =
        '<div class="empty-state">' +
          '<span class="empty-icon">📸</span>' +
          '<p>No costume uploaded yet</p>' +
          '<button class="btn btn-primary" style="margin-top:16px" onclick="App.navigate(\'setup\')">Upload Costume</button>' +
        '</div>';
      return;
    }

    container.innerHTML =
      '<div class="home-card">' +
        '<img src="' + u.costume.photo_url + '" class="home-photo" alt="Your costume">' +
        '<div class="home-info">' +
          '<div class="home-editable" id="field-display-name">' +
            '<span class="home-name">' + this.escapeHtml(u.display_name || '') + '</span>' +
            (isSetup ? '<button class="btn-icon btn-edit" data-field="display_name" aria-label="Edit name">&#9998;</button>' : '') +
          '</div>' +
          '<div class="home-editable" id="field-dressed-up-as">' +
            '<span class="home-costume-desc">' + this.escapeHtml(u.dressed_up_as || '') + '</span>' +
            (isSetup ? '<button class="btn-icon btn-edit" data-field="dressed_up_as" aria-label="Edit costume name">&#9998;</button>' : '') +
          '</div>' +
          '<div class="home-stats">' +
            '<span>Votes used: ' + u.votes_used + '/5</span>' +
          '</div>' +
          (isSetup ? '<div class="home-actions"><button class="btn btn-outline" id="btn-reupload-camera">Take New Photo</button> <button class="btn btn-outline" id="btn-reupload-gallery">Choose from Gallery</button></div>' : '') +
        '</div>' +
      '</div>';

    if (!isSetup) return;

    var self = this;
    function reuploadWithInput(useCapture) {
      var input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      if (useCapture) input.setAttribute('capture', 'environment');
      input.addEventListener('change', function() {
        if (input.files && input.files[0]) {
          showLoading();
          resizeImage(input.files[0], 1920).then(function(file) {
            return API.uploadCostume(file);
          }).then(function(data) {
            App.user.costume = { id: data.costume_id, photo_url: '/static/costumes/' + data.filename };
            showToast('Photo updated!', 'success');
            self.render();
          }).catch(function(err) {
            showToast(err.detail, 'error');
          }).finally(function() {
            hideLoading();
          });
        }
      });
      input.click();
    }
    $('#btn-reupload-camera').addEventListener('click', function() { reuploadWithInput(true); });
    $('#btn-reupload-gallery').addEventListener('click', function() { reuploadWithInput(false); });

    container.querySelectorAll('.btn-edit').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var field = btn.dataset.field;
        var currentVal = field === 'display_name' ? u.display_name : u.dressed_up_as;
        var label = field === 'display_name' ? 'display name' : 'costume name';
        var apiFn = field === 'display_name' ? API.setDisplayName : API.setDressedUpAs;

        var modal = $('#edit-modal');
        var inp = $('#edit-modal-input');
        $('#edit-modal-label').textContent = 'Enter your ' + label;
        inp.value = currentVal || '';
        modal.classList.remove('hidden');
        inp.focus();
        inp.select();

        function close() {
          modal.classList.add('hidden');
          $('#edit-modal-save').removeEventListener('click', save);
          $('#edit-modal-cancel').removeEventListener('click', close);
          $('#edit-modal .modal-backdrop').removeEventListener('click', close);
          inp.removeEventListener('keydown', onKey);
        }

        function save() {
          var val = inp.value.trim();
          if (!val || val === currentVal) { close(); return; }
          close();
          showLoading();
          apiFn.call(API, val).then(function(data) {
            App.user[field] = data[field];
            showToast('Updated!', 'success');
            self.render();
          }).catch(function(err) {
            showToast(err.detail, 'error');
          }).finally(function() {
            hideLoading();
          });
        }

        function onKey(e) {
          if (e.key === 'Enter') save();
          if (e.key === 'Escape') close();
        }

        $('#edit-modal-save').addEventListener('click', save);
        $('#edit-modal-cancel').addEventListener('click', close);
        $('#edit-modal .modal-backdrop').addEventListener('click', close);
        inp.addEventListener('keydown', onKey);
      });
    });
  },

  escapeHtml: function(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
};

/* Boot */
document.addEventListener('DOMContentLoaded', function() { App.init(); });
