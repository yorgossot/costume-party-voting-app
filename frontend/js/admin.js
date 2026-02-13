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
    API.getCompetitionStatus().then(function(data) {
      self.render(data.status);
    });
  },

  render: function(currentStatus) {
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
