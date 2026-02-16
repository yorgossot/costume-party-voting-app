// Admin API methods — loaded dynamically for admins only
API.advanceStatus = function() { return this.post('/admin/advance-status'); };
API.setStatus = function(status) { return this.post('/admin/set-status', { status: status }); };
API.purge = function() { return this.post('/admin/purge'); };
API.purgeAvailable = function() { return this.get('/admin/purge-available'); };

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
      self.render(results[0].status, results[1].available);
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
    }).join('<div class="phase-line' + '"></div>');

    var html = '<div class="admin-card">' +
      '<div class="phase-stepper">' + dots + '</div>' +
    '</div>';

    // Current phase info
    html += '<div class="admin-card phase-info-card">' +
      '<h3>' + info.label + '</h3>' +
      '<p class="subtitle">' + info.desc + '</p>' +
    '</div>';

    // Actions
    html += '<div class="admin-actions">';
    if (!isLast) {
      var nextInfo = this.STATE_INFO[this.STATES[idx + 1]];
      html += '<button class="btn btn-primary" id="btn-advance">' +
        'Advance to ' + nextInfo.label + '</button>';
    } else {
      html += '<p class="subtitle" style="text-align:center;margin:12px 0;">Competition complete!</p>';
    }
    if (!isFirst) {
      var prevInfo = this.STATE_INFO[this.STATES[idx - 1]];
      html += '<button class="btn btn-outline" id="btn-go-back" style="margin-top:8px;">' +
        'Go back to ' + prevInfo.label + '</button>';
    }
    if (purgeAvailable) {
      html += '<button class="btn btn-danger" id="btn-purge" style="margin-top:8px;">' +
        'Purge All Data</button>';
    }
    html += '</div>';

    container.innerHTML = html;

    // Attach listeners
    var advanceBtn = document.getElementById('btn-advance');
    if (advanceBtn) {
      advanceBtn.addEventListener('click', function() { self.advance(); });
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

  advance: function() {
    var self = this;
    API.advanceStatus().then(function(data) {
      showToast('Advanced to ' + self.STATE_INFO[data.status].label, 'success');
      self.render(data.status);
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
        self.render(data.status);
      }).catch(function(err) {
        showToast(err.detail, 'error');
        self.load();
      });
    });
  }
};
