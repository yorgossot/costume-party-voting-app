var Vote = {
  costumes: [],
  votedIds: {},
  votesUsed: 0,
  myUserId: null,
  competitionStatus: 'setup',
  refreshTimer: null,

  HEART_SVG: '<svg viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>',

  init: function() {
    var self = this;

    // Photo modal close
    $('#modal-close-btn').addEventListener('click', function() { self.closeModal(); });
    $('#photo-modal .modal-backdrop').addEventListener('click', function() { self.closeModal(); });
    $('#modal-vote-btn').addEventListener('click', function() {
      var id = parseInt($('#modal-vote-btn').dataset.costumeId);
      if (id) self.toggleVote(id);
    });
  },

  onEnter: function() {
    var self = this;
    this.loadData();
    // Auto-refresh every 30s
    this.refreshTimer = setInterval(function() { self.loadData(); }, 30000);
  },

  onLeave: function() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  },

  loadData: function() {
    var self = this;
    Promise.all([
      API.getCostumes(),
      API.me(),
      API.getCompetitionStatus()
    ]).then(function(results) {
      self.costumes = results[0];
      var me = results[1];
      self.myUserId = me.user_id;
      self.votesUsed = me.votes_used;
      self.votedIds = {};
      me.voted_costume_ids.forEach(function(id) { self.votedIds[id] = true; });
      self.competitionStatus = results[2].status;
      App.user = me;
      self.render();
    }).catch(function() {
      // Silent fail on auto-refresh
    });
  },

  render: function() {
    var grid = $('#costume-grid');
    var noItems = $('#no-costumes');
    var banner = $('#voting-closed-banner');

    // Update votes counter
    $('#votes-text').textContent = this.votesUsed + '/5';

    // Voting status banner
    var bannerText = $('#voting-banner-text');
    if (this.competitionStatus !== 'voting') {
      banner.classList.remove('hidden');
      if (this.competitionStatus === 'setup') bannerText.textContent = 'Voting has not started yet';
      else bannerText.textContent = 'Voting is closed';
    } else {
      banner.classList.add('hidden');
    }

    if (this.costumes.length === 0) {
      grid.innerHTML = '';
      noItems.classList.remove('hidden');
      return;
    }
    noItems.classList.add('hidden');

    var self = this;
    grid.innerHTML = this.costumes.map(function(c) { return self.renderCard(c); }).join('');

    // Attach event listeners
    grid.querySelectorAll('.costume-card').forEach(function(card) {
      var costumeId = parseInt(card.dataset.costumeId);

      // Tap photo to open modal
      card.querySelector('.costume-photo-wrap img').addEventListener('click', function(e) {
        e.stopPropagation();
        self.openModal(costumeId);
      });

      // Vote button
      var btn = card.querySelector('.vote-btn');
      if (btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          self.toggleVote(costumeId);
        });
      }
    });
  },

  renderCard: function(costume) {
    var isOwn = costume.user_id === this.myUserId;
    var isVoted = !!this.votedIds[costume.id];
    var canVote = !isOwn && this.competitionStatus === 'voting';
    var noVotesLeft = this.votesUsed >= 5 && !isVoted;

    var html = '<div class="costume-card" data-costume-id="' + costume.id + '">';
    html += '<div class="costume-photo-wrap">';
    html += '<img src="' + costume.thumb_url + '" loading="lazy" alt="Costume">';

    // Label at bottom
    var label = costume.dressed_up_as || costume.display_name || '';
    if (label) {
      html += '<span class="costume-label">' + this.escapeHtml(label) + '</span>';
    }

    // Own badge
    if (isOwn) {
      html += '<span class="own-badge">You</span>';
    }

    // Vote button
    if (canVote) {
      var btnClass = 'vote-btn';
      if (isVoted) btnClass += ' voted';
      if (noVotesLeft) btnClass += ' disabled-vote';
      html += '<button class="' + btnClass + '" aria-label="' + (isVoted ? 'Remove vote' : 'Vote') + '">';
      html += this.HEART_SVG;
      html += '</button>';
    }

    html += '</div></div>';
    return html;
  },

  toggleVote: function(costumeId) {
    var isVoted = !!this.votedIds[costumeId];
    var self = this;

    if (!isVoted && this.votesUsed >= 5) {
      showToast('No votes remaining! Remove a vote first.');
      return;
    }

    if (this.competitionStatus !== 'voting') {
      showToast('Voting is not open');
      return;
    }

    var promise = isVoted ? API.unvote(costumeId) : API.vote(costumeId);

    promise.then(function(res) {
      if (isVoted) {
        delete self.votedIds[costumeId];
      } else {
        self.votedIds[costumeId] = true;
      }
      self.votesUsed = 5 - res.votes_remaining;
      self.render();
      self.updateModalVoteState(costumeId);
    }).catch(function(err) {
      showToast(err.detail, 'error');
    });
  },

  openModal: function(costumeId) {
    var costume = this.costumes.find(function(c) { return c.id === costumeId; });
    if (!costume) return;

    var isOwn = costume.user_id === this.myUserId;

    $('#modal-photo').src = costume.photo_url;
    $('#modal-name').textContent = costume.display_name || '';
    $('#modal-costume').textContent = costume.dressed_up_as || '';

    var voteBtn = $('#modal-vote-btn');
    if (isOwn || this.competitionStatus !== 'voting') {
      voteBtn.classList.add('hidden');
    } else {
      voteBtn.classList.remove('hidden');
      voteBtn.dataset.costumeId = costumeId;
      this.updateModalVoteState(costumeId);
    }

    $('#photo-modal').classList.remove('hidden');
  },

  updateModalVoteState: function(costumeId) {
    var voteBtn = $('#modal-vote-btn');
    if (voteBtn.classList.contains('hidden')) return;
    var isVoted = !!this.votedIds[costumeId];
    voteBtn.classList.toggle('voted', isVoted);
    $('#modal-vote-text').textContent = isVoted ? 'Voted' : 'Vote';
  },

  closeModal: function() {
    $('#photo-modal').classList.add('hidden');
  },

  escapeHtml: function(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
};
