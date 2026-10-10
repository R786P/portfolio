(function () {
  var f = document.querySelector('form[data-cloud]');
  if (!f) return;
  var CLOUD = f.dataset.cloud, PRESET = f.dataset.preset;
  var st = document.getElementById('status'), go = document.getElementById('go');
  function $(id) { return document.getElementById(id); }

  function toggle() {
    var src = f.querySelector('input[name=source]:checked');
    if (!src || !$('fileBox')) return;
    $('fileBox').hidden = src.value !== 'file';
    $('linkBox').hidden = src.value === 'file';
  }
  f.querySelectorAll('input[name=source]').forEach(function (r) { r.addEventListener('change', toggle); });
  toggle();

  function up(file, kind, label) {
    return new Promise(function (res, rej) {
      var x = new XMLHttpRequest();
      x.open('POST', 'https://api.cloudinary.com/v1_1/' + CLOUD + '/' + kind + '/upload');
      x.upload.onprogress = function (e) {
        if (e.lengthComputable) st.textContent = label + ' ' + Math.round(e.loaded / e.total * 100) + '%';
      };
      x.onload = function () {
        var j = {};
        try { j = JSON.parse(x.responseText); } catch (e) { return rej('Upload fail ho gaya'); }
        if (x.status === 200 && j.secure_url) res(j.secure_url);
        else rej((j.error && j.error.message) || 'Upload fail ho gaya');
      };
      x.onerror = function () { rej('Network error'); };
      var d = new FormData();
      d.append('file', file);
      d.append('upload_preset', PRESET);
      x.send(d);
    });
  }

  f.addEventListener('submit', async function (e) {
    e.preventDefault();
    go.disabled = true;
    try {
      var src = f.querySelector('input[name=source]:checked');
      if (src && src.value === 'file') {
        var vf = $('vfile').files[0];
        if (!vf) throw 'Video file chuno';
        if (vf.size > 100 * 1024 * 1024) throw 'Video 100MB se chhota rakho';
        $('video_url').value = await up(vf, 'video', 'Video upload');
      }
      var tf = $('tfile') && $('tfile').files[0];
      if (tf) $('thumb_url').value = await up(tf, 'image', 'Thumbnail upload');
      var af = $('afile') && $('afile').files[0];
      if (af) {
        if (af.size > 10 * 1024 * 1024) throw 'File 10MB se chhoti rakho';
        $('file_url').value = await up(af, 'auto', 'File upload');
      }
      st.textContent = 'Saving...';
      f.submit();
    } catch (err) {
      st.textContent = String(err);
      go.disabled = false;
    }
  });
})();
