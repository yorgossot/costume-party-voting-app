// Authenticated API methods — loaded dynamically after login
API.me = function() { return this.get('/me'); };

// Setup
API.setDisplayName = function(v) { return this.post('/select-display-name', { value: v }); };
API.setDressedUpAs = function(v) { return this.post('/select-dressed-up-as', { value: v }); };

// Costumes
API.uploadCostume = function(file) {
  var fd = new FormData();
  fd.append('file', file);
  return this.upload('/upload-costume', fd);
};
API.getCostumes = function() { return this.get('/costumes'); };

// Voting
API.vote = function(id) { return this.post('/vote', { costume_id: id }); };
API.unvote = function(id) { return this.post('/unvote', { costume_id: id }); };
API.getCompetitionStatus = function() { return this.get('/competition-status'); };
API.getResults = function() { return this.get('/results'); };
