"""Self-contained mobile upload page served by the phone bridge (no external resources)."""

from __future__ import annotations

import json
from typing import Any

_TEMPLATE = """<!doctype html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="color-scheme" content="light">
<title>Exan</title>
<style nonce="__NONCE__">
:root{--ink:#000;--surface:#f8f9fa;--line:#c6c6c6;--muted:#5d5f5f;--accent:#1f41ff;--error:#ba1a1a}
*{box-sizing:border-box;border-radius:0}
html,body{margin:0;background:var(--surface);color:var(--ink);
font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
-webkit-text-size-adjust:100%}
header{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;background:#fff;
border-bottom:.5px solid var(--line)}
.brand{font-weight:800;letter-spacing:.24em;text-transform:uppercase;font-size:14px}
.target{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;border:1px solid var(--ink);
padding:4px 8px}
main{max-width:560px;margin:0 auto;padding:20px 20px 40px}
h1{font-size:22px;line-height:1.2;margin:0 0 6px;letter-spacing:-.01em}
.lead{color:var(--muted);margin:0 0 20px;font-size:14px}
.actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
.btn{display:flex;align-items:center;justify-content:center;text-align:center;min-height:56px;padding:0 14px;
border:1px solid var(--ink);background:#fff;color:var(--ink);font:inherit;font-weight:700;font-size:12px;
letter-spacing:.12em;text-transform:uppercase;cursor:pointer;-webkit-tap-highlight-color:transparent;
-webkit-appearance:none;appearance:none}
.btn.primary{width:100%;background:var(--ink);color:#fff}
.btn:disabled{opacity:.35}
.picker{position:absolute;width:1px;height:1px;opacity:0;overflow:hidden;pointer-events:none}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:16px}
.thumb{position:relative;aspect-ratio:3/4;background:#fff;border:.5px solid var(--line);overflow:hidden;
display:flex;align-items:center;justify-content:center;font-size:11px;color:var(--muted);word-break:break-all;
padding:0}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.thumb .rm{position:absolute;top:0;right:0;width:36px;height:36px;border:0;background:rgba(0,0,0,.8);color:#fff;
font-size:18px;line-height:36px;padding:0}
.thumb .no{position:absolute;left:0;bottom:0;background:#000;color:#fff;font-size:11px;font-weight:700;padding:2px 6px}
fieldset{border:.5px solid var(--line);background:#fff;padding:10px 14px;margin:0 0 16px}
legend{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;padding:0 4px}
.opt{display:flex;gap:10px;align-items:flex-start;padding:8px 0;font-size:15px}
.opt input{margin-top:4px;accent-color:#000;width:18px;height:18px}
.status{margin-top:16px;padding:12px 14px;border:.5px solid var(--line);background:#fff;font-size:14px}
.status.ok{border-color:var(--ink)}
.status.err{border-color:var(--error);color:var(--error)}
.bar{height:4px;background:#e7e8e9;margin-top:10px}
.bar>div{height:100%;width:0;background:var(--accent);transition:width .15s}
.hint{font-size:13px;color:var(--muted);margin-top:22px}
ul.errors{margin:8px 0 0;padding-left:18px}
[hidden]{display:none!important}
</style>
</head>
<body>
<header><div class="brand">Exan</div><div class="target" id="target"></div></header>
<main>
<h1 id="title"></h1>
<p class="lead" id="lead"></p>
<div class="actions">
<label class="btn" for="camera" id="cameraLabel"></label>
<label class="btn" for="gallery" id="galleryLabel"></label>
</div>
<input class="picker" type="file" id="camera" accept="image/*" capture="environment">
<input class="picker" type="file" id="gallery" accept="image/*,application/pdf" multiple>
<div class="grid" id="grid"></div>
<fieldset id="grouping" hidden>
<legend id="groupingLegend"></legend>
<label class="opt"><input type="radio" name="grouping" value="single" checked><span id="groupSingle"></span></label>
<label class="opt"><input type="radio" name="grouping" value="file"><span id="groupEach"></span></label>
</fieldset>
<button class="btn primary" id="send" type="button" disabled></button>
<div class="status" id="status" hidden></div>
<p class="hint" id="hint"></p>
</main>
<script id="exan-config" type="application/json">__CONFIG__</script>
<script nonce="__NONCE__">
(function () {
  'use strict';
  var cfg = JSON.parse(document.getElementById('exan-config').textContent);
  var TEXT = {
    en: {
      key: 'Answer key', participants: 'Answer sheets',
      title_key: 'Photograph the answer key',
      title_participants: 'Photograph answer sheets',
      lead: 'Photos go straight to Exan on your computer over your Wi-Fi. Nothing is uploaded to the internet.',
      camera: 'Take photo', gallery: 'Choose files',
      send: 'Send to computer', send_n: 'Send {n} to computer',
      preparing: 'Preparing photos\u2026', sending: 'Sending\u2026 {p}%',
      sent_key: '{n} page(s) added to the answer key.',
      sent_participants: '{n} page(s) sent \u2013 {k} participant(s) added.',
      failed: 'Sending failed: {e}', network: 'The computer cannot be reached. Is it on the same Wi-Fi?',
      grouping: 'These photos are', single: 'pages of ONE participant',
      each: 'different participants (one photo each)',
      remove: 'Remove', too_many: 'At most {n} files per sending.',
      ended: 'This connection has ended. Open the phone dialog in Exan again and scan the new QR code.',
      hint: 'Tip: keep this page open, put the sheet on a flat surface with good light and fill the frame with it.'
    },
    de: {
      key: 'L\u00f6sungsschl\u00fcssel', participants: 'Antwortb\u00f6gen',
      title_key: 'L\u00f6sungsschl\u00fcssel fotografieren',
      title_participants: 'Antwortb\u00f6gen fotografieren',
      lead: 'Die Fotos gehen \u00fcber dein WLAN direkt an Exan auf deinem Computer. Nichts wird ins Internet hochgeladen.',
      camera: 'Foto aufnehmen', gallery: 'Dateien w\u00e4hlen',
      send: 'An Computer senden', send_n: '{n} an Computer senden',
      preparing: 'Fotos werden vorbereitet\u2026', sending: 'Wird gesendet\u2026 {p}%',
      sent_key: '{n} Seite(n) zum L\u00f6sungsschl\u00fcssel hinzugef\u00fcgt.',
      sent_participants: '{n} Seite(n) gesendet \u2013 {k} Teilnehmende hinzugef\u00fcgt.',
      failed: 'Senden fehlgeschlagen: {e}',
      network: 'Der Computer ist nicht erreichbar. Ist er im selben WLAN?',
      grouping: 'Diese Fotos sind', single: 'Seiten EINER teilnehmenden Person',
      each: 'verschiedene Teilnehmende (je ein Foto)',
      remove: 'Entfernen', too_many: 'H\u00f6chstens {n} Dateien pro Sendung.',
      ended: 'Diese Verbindung wurde beendet. \u00d6ffne den Handy-Dialog in Exan erneut und scanne den neuen QR-Code.',
      hint: 'Tipp: Lass diese Seite offen, leg den Bogen auf eine ebene Fl\u00e4che mit gutem Licht und f\u00fclle das Bild damit aus.'
    }
  };
  var lang = TEXT[cfg.lang] ? cfg.lang : 'en';
  function t(key, vars) {
    var text = TEXT[lang][key] || TEXT.en[key] || key;
    if (vars) {
      Object.keys(vars).forEach(function (name) { text = text.split('{' + name + '}').join(String(vars[name])); });
    }
    return text;
  }
  function $(id) { return document.getElementById(id); }

  var target = cfg.target;
  var items = [];
  var busy = false;
  var closed = false;

  function setStatus(kind, message, list) {
    var box = $('status');
    box.hidden = !message;
    box.className = 'status' + (kind ? ' ' + kind : '');
    box.textContent = message || '';
    if (list && list.length) {
      var ul = document.createElement('ul');
      ul.className = 'errors';
      list.forEach(function (line) {
        var li = document.createElement('li');
        li.textContent = line;
        ul.appendChild(li);
      });
      box.appendChild(ul);
    }
  }
  function setProgress(fraction) {
    var box = $('status');
    var bar = box.querySelector('.bar');
    if (!bar) {
      bar = document.createElement('div');
      bar.className = 'bar';
      bar.appendChild(document.createElement('div'));
      box.appendChild(bar);
    }
    bar.firstChild.style.width = Math.round(fraction * 100) + '%';
  }

  function render() {
    document.title = 'Exan \u2013 ' + t(target);
    $('target').textContent = t(target);
    $('title').textContent = t('title_' + target);
    $('lead').textContent = t('lead');
    $('cameraLabel').textContent = t('camera');
    $('galleryLabel').textContent = t('gallery');
    $('groupingLegend').textContent = t('grouping');
    $('groupSingle').textContent = t('single');
    $('groupEach').textContent = t('each');
    $('hint').textContent = t('hint');
    $('grouping').hidden = !(target === 'participants' && items.length > 1);
    var send = $('send');
    send.textContent = items.length ? t('send_n', { n: items.length }) : t('send');
    send.disabled = busy || closed || !items.length;
    $('camera').disabled = $('gallery').disabled = busy || closed;
    var grid = $('grid');
    while (grid.firstChild) { grid.removeChild(grid.firstChild); }
    items.forEach(function (item, index) {
      var cell = document.createElement('div');
      cell.className = 'thumb';
      if (item.url) {
        var img = document.createElement('img');
        img.alt = item.file.name;
        img.src = item.url;
        img.onerror = function () { cell.replaceChild(document.createTextNode(item.file.name), img); };
        cell.appendChild(img);
      } else {
        cell.appendChild(document.createTextNode(item.file.name));
      }
      var no = document.createElement('span');
      no.className = 'no';
      no.textContent = String(index + 1);
      cell.appendChild(no);
      var rm = document.createElement('button');
      rm.className = 'rm';
      rm.type = 'button';
      rm.textContent = '\u00d7';
      rm.setAttribute('aria-label', t('remove'));
      rm.disabled = busy;
      rm.onclick = function () {
        if (item.url) { URL.revokeObjectURL(item.url); }
        items.splice(index, 1);
        render();
      };
      cell.appendChild(rm);
      grid.appendChild(cell);
    });
  }

  function isPdf(file) { return file.type === 'application/pdf' || /\\.pdf$/i.test(file.name); }

  function addFiles(list) {
    var skipped = false;
    Array.prototype.forEach.call(list, function (file) {
      if (items.length >= cfg.maxFiles) { skipped = true; return; }
      items.push({ file: file, url: isPdf(file) ? null : URL.createObjectURL(file) });
    });
    setStatus(skipped ? 'err' : '', skipped ? t('too_many', { n: cfg.maxFiles }) : '');
    render();
  }
  ['camera', 'gallery'].forEach(function (id) {
    $(id).addEventListener('change', function (event) {
      addFiles(event.target.files || []);
      event.target.value = '';
    });
  });

  function shrink(file) {
    return new Promise(function (resolve) {
      if (isPdf(file)) { resolve(file); return; }
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        try {
          var w = img.naturalWidth, h = img.naturalHeight;
          var scale = Math.min(1, cfg.maxSide / Math.max(w, h));
          var canvas = document.createElement('canvas');
          canvas.width = Math.max(1, Math.round(w * scale));
          canvas.height = Math.max(1, Math.round(h * scale));
          var ctx = canvas.getContext('2d');
          ctx.fillStyle = '#fff';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          URL.revokeObjectURL(url);
          canvas.toBlob(function (blob) { resolve(blob || file); }, 'image/jpeg', 0.85);
        } catch (err) {
          URL.revokeObjectURL(url);
          resolve(file);
        }
      };
      img.onerror = function () { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    });
  }

  function upload(form) {
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', cfg.base + '/upload');
      xhr.upload.onprogress = function (event) {
        if (event.lengthComputable) {
          setStatus('', t('sending', { p: Math.round(event.loaded / event.total * 100) }));
          setProgress(event.loaded / event.total);
        }
      };
      xhr.onload = function () {
        var body = null;
        try { body = JSON.parse(xhr.responseText); } catch (err) { body = null; }
        if (xhr.status >= 200 && xhr.status < 300 && body) { resolve(body); return; }
        if (xhr.status === 404 || xhr.status === 403) { endSession(); }
        reject(new Error((body && body.detail) || ('HTTP ' + xhr.status)));
      };
      xhr.onerror = function () { reject(new Error(t('network'))); };
      xhr.send(form);
    });
  }

  $('send').addEventListener('click', function () {
    if (busy || !items.length) { return; }
    busy = true;
    render();
    setStatus('', t('preparing'));
    var grouping = (document.querySelector('input[name=grouping]:checked') || {}).value || 'single';
    var form = new FormData();
    form.append('target', target);
    form.append('grouping', grouping);
    var chain = Promise.resolve();
    items.forEach(function (item, index) {
      chain = chain.then(function () { return shrink(item.file); }).then(function (blob) {
        var base = item.file.name.replace(/\\.[^.]*$/, '') || ('photo-' + (index + 1));
        var name = blob === item.file ? item.file.name : base + '.jpg';
        form.append('files', blob, name);
      });
    });
    chain.then(function () { return upload(form); }).then(function (result) {
      items.forEach(function (item) { if (item.url) { URL.revokeObjectURL(item.url); } });
      items = [];
      busy = false;
      var lines = (result.errors || []).map(function (e) { return e.file + ': ' + e.message; });
      var message = result.target === 'key'
        ? t('sent_key', { n: result.pages })
        : t('sent_participants', { n: result.pages, k: result.participants });
      setStatus(lines.length ? 'err' : 'ok', message, lines);
      render();
    }).catch(function (err) {
      busy = false;
      setStatus('err', t('failed', { e: err.message }));
      render();
    });
  });

  function endSession() {
    closed = true;
    setStatus('err', t('ended'));
    render();
  }

  function poll() {
    if (closed) { return; }
    var xhr = new XMLHttpRequest();
    xhr.open('GET', cfg.base + '/info');
    xhr.onload = function () {
      if (xhr.status === 404 || xhr.status === 403) { endSession(); return; }
      if (xhr.status !== 200) { return; }
      try {
        var info = JSON.parse(xhr.responseText);
        if (info.target && info.target !== target) { target = info.target; render(); }
        if (info.lang && TEXT[info.lang] && info.lang !== lang) { lang = info.lang; render(); }
      } catch (err) { /* ignore */ }
    };
    xhr.send();
  }
  setInterval(poll, 4000);
  render();
})();
</script>
</body>
</html>
"""


def render_page(*, nonce: str, config: dict[str, Any], lang: str) -> str:
    payload = json.dumps(config, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e")
    page = _TEMPLATE.replace("__NONCE__", nonce).replace("__LANG__", "de" if lang == "de" else "en")
    return page.replace("__CONFIG__", payload)
