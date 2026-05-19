// Admin API methods — loaded dynamically for admins only
API.setStatus = function(status) { return this.put('/competition/status', { status: status }); };
API.purge = function() { return this.del('/admin/data'); };
API.purgeAvailable = function() { return this.get('/admin/data').then(function(d) { return d.purge_available; }); };
API.userLookup = function(code) { return this.get('/admin/users/' + encodeURIComponent(code)); };
API.resetUserField = function(code, field) { return this.del('/admin/users/' + encodeURIComponent(code) + '/fields/' + field); };
API.purgeUser = function(code) { return this.del('/admin/users/' + encodeURIComponent(code) + '/data'); };

var Admin = {
  STATES: ['setup', 'voting', 'counting', 'reveal'],
  STATE_INFO: {
    setup:    { label: 'Setup',    desc: 'Guests upload costumes and set their names.' },
    voting:   { label: 'Voting',   desc: 'Voting is open. Costumes are locked.' },
    counting: { label: 'Counting', desc: 'Voting closed. Results hidden.' },
    reveal:   { label: 'Reveal',   desc: 'Results are visible to everyone!' }
  },

  onEnter: function() {
    if (!App.user || !App.user.is_admin) {
      App.navigate('vote');
      return;
    }
    this.load();
  },

  load: function() {
    var self = this;
    Promise.all([
      API.getCompetitionStatus(),
      API.purgeAvailable()
    ]).then(function(results) {
      self.render(results[0].status, results[1]);
    });
  },

  render: function(currentStatus, purgeAvailable) {
    var container = $('#admin-content');
    var idx = this.STATES.indexOf(currentStatus);
    var info = this.STATE_INFO[currentStatus];
    var isFirst = idx === 0;
    var isLast = idx === this.STATES.length - 1;
    var self = this;

    // Phase stepper dots
    var dots = this.STATES.map(function(s, i) {
      var cls = 'phase-dot';
      if (i < idx) cls += ' done';
      else if (i === idx) cls += ' active';
      return '<div class="' + cls + '">' +
        '<div class="phase-dot-circle"></div>' +
        '<span class="phase-dot-label">' + self.STATE_INFO[s].label + '</span>' +
      '</div>';
    }).join('<div class="phase-line"></div>');

    // Section 1: Competition Phase
    var html = '<div class="admin-card">' +
      '<h3 class="admin-section-title">Competition Phase</h3>' +
      '<div class="phase-stepper">' + dots + '</div>' +
      '<div class="phase-info-card">' +
        '<p class="phase-current-label">' + info.label + '</p>' +
        '<p class="subtitle">' + info.desc + '</p>' +
      '</div>' +
      '<div class="admin-actions">';

    if (!isLast) {
      var nextInfo = this.STATE_INFO[this.STATES[idx + 1]];
      html += '<button class="btn btn-primary" id="btn-advance">' +
        'Advance to ' + nextInfo.label + '</button>';
    } else {
      html += '<p class="subtitle" style="text-align:center;margin:12px 0;">Competition complete!</p>';
    }
    if (!isFirst) {
      var prevInfo = this.STATE_INFO[this.STATES[idx - 1]];
      html += '<button class="btn btn-outline" id="btn-go-back">' +
        'Go back to ' + prevInfo.label + '</button>';
    }
    html += '</div></div>';

    container.innerHTML = html;
    UserMgmt.render();

    // Section 3: Danger Zone
    if (purgeAvailable) {
      var dangerCard = document.createElement('div');
      dangerCard.className = 'admin-card admin-danger-zone';
      dangerCard.innerHTML =
        '<h3 class="admin-section-title">Danger Zone</h3>' +
        '<button class="btn btn-danger" id="btn-purge" style="width:100%;">Purge All Data</button>';
      container.appendChild(dangerCard);
    }

    // Attach listeners
    var advanceBtn = document.getElementById('btn-advance');
    if (advanceBtn) {
      advanceBtn.addEventListener('click', function() { self.advance(self.STATES[idx + 1]); });
    }
    var goBackBtn = document.getElementById('btn-go-back');
    if (goBackBtn) {
      goBackBtn.addEventListener('click', function() {
        var prevStatus = self.STATES[idx - 1];
        self.setStatus(prevStatus);
      });
    }
    var purgeBtn = document.getElementById('btn-purge');
    if (purgeBtn) {
      purgeBtn.addEventListener('click', function() { self.purge(); });
    }
  },

  advance: function(nextStatus) {
    var self = this;
    API.setStatus(nextStatus).then(function(data) {
      showToast('Advanced to ' + self.STATE_INFO[data.status].label, 'success');
      self.load();
    }).catch(function(err) {
      showToast(err.detail, 'error');
      self.load();
    });
  },

  purge: function() {
    var self = this;
    confirmAction('Purge ALL data? This deletes all votes, costumes, and resets the competition. This cannot be undone.').then(function(ok) {
      if (!ok) return;
      API.purge().then(function(data) {
        showToast('Purged: ' + data.votes_deleted + ' votes, ' + data.costumes_deleted + ' costumes', 'success');
        self.load();
      }).catch(function(err) {
        showToast(err.detail, 'error');
      });
    });
  },

  setStatus: function(targetStatus) {
    var self = this;
    confirmAction('Go back to ' + this.STATE_INFO[targetStatus].label + ' phase?').then(function(ok) {
      if (!ok) return;
      API.setStatus(targetStatus).then(function(data) {
        showToast('Moved to ' + self.STATE_INFO[data.status].label, 'success');
        self.load();
      }).catch(function(err) {
        showToast(err.detail, 'error');
        self.load();
      });
    });
  }
};

var UserMgmt = {
  render: function() {
    var container = $('#admin-content');
    var section = document.createElement('div');
    section.className = 'admin-card';
    section.innerHTML =
      '<h3 class="admin-section-title">User Management</h3>' +
      '<input id="um-code" type="text" placeholder="Access code" class="um-input">' +
      '<button class="btn btn-outline" id="um-lookup" style="width:100%;margin-top:8px;">Look Up</button>' +
      '<div id="um-result" style="margin-top:12px;"></div>';
    container.appendChild(section);

    document.getElementById('um-lookup').addEventListener('click', function() {
      var code = document.getElementById('um-code').value.trim();
      if (code) UserMgmt.lookup(code);
    });
    document.getElementById('um-code').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        var code = this.value.trim();
        if (code) UserMgmt.lookup(code);
      }
    });
  },

  lookup: function(code) {
    var resultDiv = document.getElementById('um-result');
    resultDiv.innerHTML = '<p class="subtitle">Looking up…</p>';
    API.userLookup(code).then(function(data) {
      UserMgmt.renderResult(code, data);
    }).catch(function(err) {
      resultDiv.innerHTML = '<p class="subtitle" style="color:#ff6b6b;">' +
        (err.detail || 'User not found') + '</p>';
    });
  },

  renderResult: function(code, data) {
    var resultDiv = document.getElementById('um-result');
    resultDiv.innerHTML =
      '<div style="background:#0d0d1a;border-radius:8px;padding:12px;border:1px solid #333;">' +
        '<p style="margin:0 0 4px;"><strong>' + (data.display_name || '<em>no name</em>') + '</strong>' +
          (data.dressed_up_as ? ' &mdash; ' + data.dressed_up_as : '') + '</p>' +
        '<p class="subtitle" style="margin:0 0 8px;">Photo: ' + (data.has_photo ? 'yes' : 'none') +
          ' &nbsp;|&nbsp; Votes cast: ' + data.votes_cast +
          ' &nbsp;|&nbsp; Votes received: ' + data.votes_received + '</p>' +
        '<div style="display:flex;flex-wrap:wrap;gap:6px;">' +
          '<button class="btn btn-outline um-action" data-field="display_name" style="font-size:13px;padding:6px 10px;">Reset Name</button>' +
          '<button class="btn btn-outline um-action" data-field="dressed_up_as" style="font-size:13px;padding:6px 10px;">Reset Costume Desc</button>' +
          (data.has_photo ? '<button class="btn btn-outline um-action" data-field="photo" style="font-size:13px;padding:6px 10px;">Reset Photo</button>' : '') +
          '<button class="btn btn-danger" id="um-purge-user" style="font-size:13px;padding:6px 10px;">Purge Account</button>' +
        '</div>' +
      '</div>';

    resultDiv.querySelectorAll('.um-action').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var field = this.getAttribute('data-field');
        var label = { display_name: 'name', dressed_up_as: 'costume description', photo: 'photo' }[field];
        confirmAction('Reset ' + label + ' for ' + (data.display_name || code) + '?').then(function(ok) {
          if (!ok) return;
          API.resetUserField(code, field).then(function() {
            showToast('Reset ' + label, 'success');
            UserMgmt.lookup(code);
          }).catch(function(err) {
            showToast(err.detail || 'Error', 'error');
          });
        });
      });
    });

    document.getElementById('um-purge-user').addEventListener('click', function() {
      confirmAction('Purge entire account for ' + (data.display_name || code) + '? This removes their costume and all votes.').then(function(ok) {
        if (!ok) return;
        API.purgeUser(code).then(function() {
          showToast('Account purged', 'success');
          UserMgmt.lookup(code);
        }).catch(function(err) {
          showToast(err.detail || 'Error', 'error');
        });
      });
    });
  }
};
