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
      API.me().then(function(user) {
        self.user = user;
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

  onEnter: function() {
    // Refresh user data
    var self = this;
    API.me().then(function(user) {
      App.user = user;
      self.render();
    });
  },

  render: function() {
    var u = App.user;
    var container = $('#home-content');

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
          '<div class="home-name">' + this.escapeHtml(u.display_name || '') + '</div>' +
          '<div class="home-costume-desc">' + this.escapeHtml(u.dressed_up_as || '') + '</div>' +
          '<div class="home-stats">' +
            '<span>Votes used: ' + u.votes_used + '/5</span>' +
          '</div>' +
          '<div class="home-actions">' +
            '<button class="btn btn-outline" id="btn-reupload">Change Photo</button>' +
            '<button class="btn btn-danger" id="btn-delete-costume">Delete Costume</button>' +
          '</div>' +
        '</div>' +
      '</div>';

    var self = this;
    $('#btn-reupload').addEventListener('click', function() {
      // Create a temporary file input
      var input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.capture = 'environment';
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
    });

    $('#btn-delete-costume').addEventListener('click', function() {
      confirmAction('Delete your costume? This will also remove any votes for it.').then(function(ok) {
        if (!ok) return;
        showLoading();
        API.deleteCostume().then(function() {
          App.user.costume = null;
          showToast('Costume deleted');
          self.render();
        }).catch(function(err) {
          showToast(err.detail, 'error');
        }).finally(function() {
          hideLoading();
        });
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
