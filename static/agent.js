(function () {
  var chat = document.getElementById('chat');
  if (!chat) return;
  var CSRF = chat.dataset.csrf, hist = [];
  var form = document.getElementById('cform'), inp = document.getElementById('cin'), btn = document.getElementById('csend');

  function add(cls, text) {
    var d = document.createElement('div');
    d.className = 'msg ' + cls;
    d.textContent = text;
    chat.appendChild(d);
    window.scrollTo(0, document.body.scrollHeight);
    return d;
  }

  function confirmBox(p) {
    var d = document.createElement('div');
    d.className = 'msg bot';
    d.textContent = 'Delete karna hai: "' + p.label + '" (' + p.kind + ')? ';
    var y = document.createElement('button'); y.type = 'button'; y.className = 'btn small danger'; y.textContent = 'Haan, delete';
    var n = document.createElement('button'); n.type = 'button'; n.className = 'btn small ghost'; n.textContent = 'Nahi';
    y.onclick = function () {
      y.disabled = true;
      fetch('/admin/agent/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF': CSRF }, body: JSON.stringify({ kind: p.kind, id: p.id }) })
        .then(function (r) { return r.json(); })
        .then(function (j) { d.textContent = j.ok ? 'Delete ho gaya: ' + p.label : 'Delete fail ho gaya.'; })
        .catch(function () { d.textContent = 'Network error.'; });
    };
    n.onclick = function () { d.textContent = 'Theek hai, delete nahi kiya.'; };
    d.appendChild(y); d.appendChild(n);
    chat.appendChild(d);
  }

  var shot = null, cfile = document.getElementById('cfile'), cprev = document.getElementById('cprev');
  function clearShot() { shot = null; if (cfile) cfile.value = ''; if (cprev) cprev.hidden = true; }
  if (cfile) {
    document.getElementById('cattach').addEventListener('click', function () { cfile.click(); });
    document.getElementById('cprevx').addEventListener('click', clearShot);
    cfile.addEventListener('change', function () {
      var f = cfile.files[0];
      if (!f) return;
      var url = URL.createObjectURL(f), im = new Image();
      im.onload = function () {
        var m = 1024, k = Math.min(1, m / Math.max(im.width, im.height));
        var cv = document.createElement('canvas');
        cv.width = Math.round(im.width * k); cv.height = Math.round(im.height * k);
        cv.getContext('2d').drawImage(im, 0, 0, cv.width, cv.height);
        var data = cv.toDataURL('image/jpeg', 0.8);
        shot = { mime: 'image/jpeg', data: data.split(',')[1], url: data };
        document.getElementById('cprevimg').src = data;
        cprev.hidden = false;
        URL.revokeObjectURL(url);
      };
      im.onerror = function () { add('note', 'Ye image khul nahi payi.'); clearShot(); };
      im.src = url;
    });
  }

  function send(text) {
    var pic = shot;
    var ub = add('user', text);
    if (pic) { var th = document.createElement('img'); th.src = pic.url; th.className = 'shot'; ub.appendChild(th); clearShot(); }
    hist.push({ role: 'user', text: text });
    btn.disabled = true;
    var wait = add('bot', 'Soch raha hu...');
    fetch('/admin/agent/chat', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF': CSRF }, body: JSON.stringify({ messages: hist, image: pic ? { mime: pic.mime, data: pic.data } : null }) })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (j) {
        wait.textContent = j.reply;
        hist.push({ role: 'assistant', text: j.reply });
        if (j.changed) add('note', 'Site update ho gayi. Public page refresh karke dekho.');
        (j.pending || []).forEach(confirmBox);
      })
      .catch(function (e) { wait.textContent = 'Error: ' + e.message + '. Dobara login karke try karo.'; })
      .then(function () { btn.disabled = false; });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var t = inp.value.trim();
    if (!t && shot) t = 'Ye screenshot dekho.';
    if (!t) return;
    inp.value = '';
    send(t);
  });
  var mic = document.getElementById('cmic'), SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    if (mic) mic.style.display = 'none';
    var mn = document.getElementById('micnote'); if (mn) mn.style.display = 'none';
  } else if (mic) {
    var rec = null, listening = false;
    mic.addEventListener('click', function () {
      if (listening && rec) { rec.stop(); return; }
      rec = new SR();
      rec.lang = 'hi-IN';
      rec.interimResults = false;
      rec.onstart = function () { listening = true; mic.classList.add('on'); inp.placeholder = 'Sun raha hu...'; };
      rec.onresult = function (e) {
        var t = e.results[0][0].transcript.trim();
        if (t) send(t);
      };
      rec.onerror = function () { add('note', 'Mic kaam nahi kar raha. Mic ki permission check karo.'); };
      rec.onend = function () { listening = false; mic.classList.remove('on'); inp.placeholder = 'Agent ko kaam batao...'; };
      rec.start();
    });
  }
  document.querySelectorAll('.chip').forEach(function (c) { c.addEventListener('click', function () { send(c.textContent); }); });
})();
