var Admin = {
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
      API.getVotingStatus(),
      API.getResults().then(function() { return true; }).catch(function() { return false; })
    ]).then(function(results) {
      self.render(!results[0].voting_closed, results[1]);
    });
  },

  render: function(votingOpen, resultsVisible) {
    var container = $('#admin-content');
    var self = this;

    container.innerHTML =
      '<div class="admin-card">' +
        '<div class="admin-card-header">' +
          '<div>' +
            '<h3>Voting</h3>' +
            '<p><span class="status-dot ' + (votingOpen ? 'on' : 'off') + '"></span>' +
              (votingOpen ? 'Open — guests can vote' : 'Closed — voting is locked') + '</p>' +
          '</div>' +
          '<label class="toggle">' +
            '<input type="checkbox" id="toggle-voting" ' + (votingOpen ? 'checked' : '') + '>' +
            '<span class="toggle-slider"></span>' +
          '</label>' +
        '</div>' +
      '</div>' +
      '<div class="admin-card">' +
        '<div class="admin-card-header">' +
          '<div>' +
            '<h3>Results</h3>' +
            '<p><span class="status-dot ' + (resultsVisible ? 'on' : 'off') + '"></span>' +
              (resultsVisible ? 'Visible — everyone can see' : 'Hidden — only you can see') + '</p>' +
          '</div>' +
          '<label class="toggle">' +
            '<input type="checkbox" id="toggle-results" ' + (resultsVisible ? 'checked' : '') + '>' +
            '<span class="toggle-slider"></span>' +
          '</label>' +
        '</div>' +
      '</div>';

    // Attach listeners
    $('#toggle-voting').addEventListener('change', function() {
      self.toggleVoting();
    });

    $('#toggle-results').addEventListener('change', function() {
      self.toggleResults();
    });
  },

  toggleVoting: function() {
    var self = this;
    API.toggleVoting().then(function() {
      self.load();
      showToast('Voting updated', 'success');
    }).catch(function(err) {
      showToast(err.detail, 'error');
      self.load();
    });
  },

  toggleResults: function() {
    var self = this;
    API.toggleResults().then(function() {
      self.load();
      showToast('Results visibility updated', 'success');
    }).catch(function(err) {
      showToast(err.detail, 'error');
      self.load();
    });
  }
};
