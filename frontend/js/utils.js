/* ===== Global Config ===== */
var PARTY_CONFIG = {
  showHeaderLogo: true,
  logoSrc: '/logo.png'
};

/* ===== DOM Helpers ===== */
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

/* ===== Toast Notifications ===== */
function showToast(message, type) {
  var container = $('#toast-container');
  var toast = document.createElement('div');
  toast.className = 'toast' + (type ? ' toast-' + type : '');
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(function() { toast.remove(); }, 3000);
}

/* ===== Loading Overlay ===== */
function showLoading() { $('#loading-overlay').classList.remove('hidden'); }
function hideLoading() { $('#loading-overlay').classList.add('hidden'); }

/* ===== Error Display ===== */
function showError(elementId, message) {
  var el = document.getElementById(elementId);
  el.textContent = message;
  el.classList.remove('hidden');
}

function hideError(elementId) {
  document.getElementById(elementId).classList.add('hidden');
}

/* ===== Confirm Dialog ===== */
function confirmAction(message) {
  return new Promise(function(resolve) {
    var modal = $('#confirm-modal');
    $('#confirm-text').textContent = message;
    modal.classList.remove('hidden');

    function cleanup(result) {
      modal.classList.add('hidden');
      $('#confirm-ok').removeEventListener('click', onOk);
      $('#confirm-cancel').removeEventListener('click', onCancel);
      $('.confirm-dialog .modal-backdrop')
      resolve(result);
    }

    function onOk() { cleanup(true); }
    function onCancel() { cleanup(false); }

    $('#confirm-ok').addEventListener('click', onOk);
    $('#confirm-cancel').addEventListener('click', onCancel);
    $('#confirm-modal .modal-backdrop').addEventListener('click', onCancel, { once: true });
  });
}

/* ===== Client-side Image Resize ===== */
function resizeImage(file, maxWidth) {
  maxWidth = maxWidth || 1920;
  return new Promise(function(resolve) {
    // Don't resize small files (under 500KB)
    if (file.size < 500 * 1024) { resolve(file); return; }

    var img = new Image();
    var url = URL.createObjectURL(file);
    img.onload = function() {
      URL.revokeObjectURL(url);
      if (img.width <= maxWidth) { resolve(file); return; }

      var ratio = maxWidth / img.width;
      var canvas = document.createElement('canvas');
      canvas.width = maxWidth;
      canvas.height = Math.round(img.height * ratio);
      var ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(function(blob) {
        resolve(new File([blob], file.name, { type: 'image/jpeg' }));
      }, 'image/jpeg', 0.85);
    };
    img.onerror = function() { resolve(file); };
    img.src = url;
  });
}
