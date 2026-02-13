var Results = {
  refreshTimer: null,

  onEnter: function() {
    var self = this;
    this.load();
    this.refreshTimer = setInterval(function() { self.load(); }, 15000);
  },

  onLeave: function() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  },

  load: function() {
    var self = this;
    API.getResults().then(function(results) {
      self.renderResults(results);
    }).catch(function(err) {
      if (err.status === 403) {
        self.renderLocked();
      }
    });
  },

  renderResults: function(results) {
    var container = $('#results-content');
    if (results.length === 0) {
      container.innerHTML = '<div class="empty-state"><span class="empty-icon">🏆</span>' +
        '<p>No votes yet</p><p class="subtitle">Results will appear once people start voting</p></div>';
      return;
    }

    var maxVotes = results[0].vote_count || 1;
    var self = this;

    container.innerHTML = results.map(function(r, i) {
      var isTop = i < 3;
      var pct = (r.vote_count / maxVotes) * 100;

      var html = '<div class="result-row' + (isTop ? ' top-three' : '') + '">';

      // Rank
      html += '<div class="result-rank">';
      if (i === 0) html += '<span class="medal gold">1</span>';
      else if (i === 1) html += '<span class="medal silver">2</span>';
      else if (i === 2) html += '<span class="medal bronze">3</span>';
      else html += '<span>' + (i + 1) + '</span>';
      html += '</div>';

      // Photo
      html += '<img src="' + r.photo_url + '" class="result-thumb" alt="Costume" loading="lazy">';

      // Info
      html += '<div class="result-info">';
      html += '<div class="result-name">' + self.escapeHtml(r.display_name || r.access_code) + '</div>';
      if (r.dressed_up_as) {
        html += '<div class="result-costume-desc">' + self.escapeHtml(r.dressed_up_as) + '</div>';
      }
      html += '<div class="vote-bar"><div class="vote-bar-fill" style="width:' + pct + '%"></div></div>';
      html += '</div>';

      // Count
      html += '<div class="result-count">' + r.vote_count + '</div>';

      html += '</div>';
      return html;
    }).join('');
  },

  renderLocked: function() {
    $('#results-content').innerHTML =
      '<div class="results-locked">' +
        '<span class="lock-icon">🏆</span>' +
        '<h2>Results coming soon</h2>' +
        '<p class="subtitle">The host will reveal the results when voting closes</p>' +
      '</div>';
  },

  escapeHtml: function(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
};
