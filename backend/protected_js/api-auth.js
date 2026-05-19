// Authenticated API methods — loaded dynamically after login
API.me = function() { return this.get('/users/me'); };

// Setup — single-field PATCH of the user resource
API.setDisplayName = function(v) { return this.patch('/users/me', { display_name: v }); };
API.setDressedUpAs = function(v) { return this.patch('/users/me', { dressed_up_as: v }); };

// Costumes — costume is a per-user singleton, replaced via PUT
API.uploadCostume = function(file) {
  var fd = new FormData();
  fd.append('file', file);
  return this.upload('/users/me/costume', fd);
};
API.getCostumes = function() { return this.get('/costumes'); };

// Voting — vote is a sub-resource of a costume
API.vote = function(id) { return this.put('/costumes/' + id + '/vote'); };
API.unvote = function(id) { return this.del('/costumes/' + id + '/vote'); };
API.getCompetitionStatus = function() { return this.get('/competition'); };
API.getResults = function() { return this.get('/results'); };
