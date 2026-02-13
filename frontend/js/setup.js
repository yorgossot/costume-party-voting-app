var Setup = {
  step: 0,
  selectedFile: null,

  init: function() {
    var self = this;

    // Step 1: Display name
    var dnInput = $('#input-display-name');
    var dnBtn = $('#btn-display-name');
    dnInput.addEventListener('input', function() {
      $('#dn-count').textContent = dnInput.value.length;
      dnBtn.disabled = dnInput.value.trim().length < 4;
    });
    dnBtn.addEventListener('click', function() { self.submitDisplayName(); });
    dnInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !dnBtn.disabled) self.submitDisplayName();
    });

    // Step 2: Dressed up as
    var duaInput = $('#input-dressed-up-as');
    var duaBtn = $('#btn-dressed-up-as');
    duaInput.addEventListener('input', function() {
      $('#dua-count').textContent = duaInput.value.length;
      duaBtn.disabled = duaInput.value.trim().length < 4;
    });
    duaBtn.addEventListener('click', function() { self.submitDressedUpAs(); });
    duaInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !duaBtn.disabled) self.submitDressedUpAs();
    });

    // Step 3: Photo upload
    var uploadArea = $('#upload-area');
    var photoInput = $('#photo-input');
    var uploadBtn = $('#btn-upload');

    uploadArea.addEventListener('click', function() { photoInput.click(); });

    photoInput.addEventListener('change', function() {
      if (photoInput.files && photoInput.files[0]) {
        self.selectedFile = photoInput.files[0];
        var preview = $('#photo-preview');
        preview.src = URL.createObjectURL(self.selectedFile);
        preview.classList.remove('hidden');
        $('#upload-placeholder').classList.add('hidden');
        uploadBtn.disabled = false;
      }
    });

    uploadBtn.addEventListener('click', function() { self.submitPhoto(); });
  },

  onEnter: function() {
    // Determine starting step
    if (!App.user.display_name) this.step = 0;
    else if (!App.user.dressed_up_as) this.step = 1;
    else if (!App.user.costume) this.step = 2;
    else { App.navigate('vote'); return; }

    this.showStep(this.step);

    // Focus the input for the current step
    if (this.step === 0) setTimeout(function() { $('#input-display-name').focus(); }, 100);
    else if (this.step === 1) setTimeout(function() { $('#input-dressed-up-as').focus(); }, 100);
  },

  showStep: function(index) {
    $$('.setup-step').forEach(function(s) { s.classList.add('hidden'); });
    $('[data-step="' + index + '"]').classList.remove('hidden');
    this.updateDots(index);
  },

  updateDots: function(current) {
    $$('#setup-progress .dot').forEach(function(dot, i) {
      dot.classList.remove('active', 'done');
      if (i < current) dot.classList.add('done');
      else if (i === current) dot.classList.add('active');
    });
  },

  advance: function() {
    this.step++;
    if (this.step >= 3) {
      App.navigate('vote');
    } else {
      this.showStep(this.step);
      if (this.step === 1) setTimeout(function() { $('#input-dressed-up-as').focus(); }, 100);
    }
  },

  submitDisplayName: function() {
    var value = $('#input-display-name').value.trim();
    var btn = $('#btn-display-name');
    var self = this;
    btn.disabled = true;
    btn.textContent = 'Saving...';
    hideError('setup-error-0');

    API.setDisplayName(value).then(function(data) {
      App.user.display_name = data.display_name;
      self.advance();
    }).catch(function(err) {
      showError('setup-error-0', err.detail);
    }).finally(function() {
      btn.disabled = false;
      btn.textContent = 'Continue';
    });
  },

  submitDressedUpAs: function() {
    var value = $('#input-dressed-up-as').value.trim();
    var btn = $('#btn-dressed-up-as');
    var self = this;
    btn.disabled = true;
    btn.textContent = 'Saving...';
    hideError('setup-error-1');

    API.setDressedUpAs(value).then(function(data) {
      App.user.dressed_up_as = data.dressed_up_as;
      self.advance();
    }).catch(function(err) {
      showError('setup-error-1', err.detail);
    }).finally(function() {
      btn.disabled = false;
      btn.textContent = 'Continue';
    });
  },

  submitPhoto: function() {
    if (!this.selectedFile) return;
    var btn = $('#btn-upload');
    var self = this;
    btn.disabled = true;
    btn.textContent = 'Uploading...';
    hideError('setup-error-2');

    resizeImage(this.selectedFile, 1920).then(function(file) {
      return API.uploadCostume(file);
    }).then(function(data) {
      App.user.costume = { id: data.costume_id, photo_url: '/static/costumes/' + data.filename };
      showToast('Costume uploaded!', 'success');
      self.advance();
    }).catch(function(err) {
      showError('setup-error-2', err.detail);
    }).finally(function() {
      btn.disabled = false;
      btn.textContent = 'Upload & Continue';
    });
  }
};
