/* Pozicijos form engine
 * Centralizuoja formos blokų logiką (be vizualinių pertvarkymų).
 * Tikslai:
 * - vienas init taškas;
 * - idempotentinis binding (neprisiriša kelis kartus);
 * - veikia tiek pozicijos formoje, tiek kainų valdymo puslapyje;
 * - blokai komunikuoja per event bus (CustomEvent).
 */
(function () {
  'use strict';

  // Jei skriptas dėl kokios nors priežasties įsikrauna 2 kartus – nebootinam pakartotinai.
  if (window.__POZ_FORM_ENGINE_LOADED__ === true) {
    return;
  }
  window.__POZ_FORM_ENGINE_LOADED__ = true;

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  // ------------------------
  // Event bus
  // ------------------------
  function emit(name, detail) {
    try {
      document.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (e) {
      var ev = document.createEvent('CustomEvent');
      ev.initCustomEvent(name, false, false, detail || {});
      document.dispatchEvent(ev);
    }
  }

  function autoGrow(el) {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = (el.scrollHeight) + 'px';
  }

  function getClosestFormsetPrefix(el) {
    try {
      var fs = el && el.closest ? el.closest('.kainos-formset') : null;
      if (!fs) return null;
      var p = fs.getAttribute('data-prefix') || (fs.dataset ? fs.dataset.prefix : null);
      return p || null;
    } catch (_) {
      return null;
    }
  }

  function setText(el, txt) {
    if (!el) return;
    el.textContent = txt;
  }

  function setShown(el, shown) {
    if (!el) return;
    el.style.display = shown ? '' : 'none';
  }

  // ------------------------
  // Decimal input normalizavimas
  // ------------------------
  function normalizeDecimalValue(raw, decimals) {
    var s = (raw == null ? '' : String(raw)).trim();
    if (!s) return '';
    s = s.replace(/\s+/g, '').replace(',', '.');

    var neg = false;
    if (s[0] === '-') {
      neg = true;
      s = s.slice(1);
    }

    s = s.replace(/[^0-9.]/g, '');
    var parts = s.split('.');
    if (parts.length > 2) {
      s = parts[0] + '.' + parts.slice(1).join('');
    }

    if (neg && s) s = '-' + s;

    var n = Number(s);
    if (!isFinite(n)) return raw;

    var d = parseInt(decimals || '0', 10) || 0;
    return n.toFixed(d);
  }

  function bindDecimalInputs(root) {
    $all('input[data-decimals]', root).forEach(function (inp) {
      if (inp.dataset && inp.dataset.decimalsBound === '1') return;
      if (inp.dataset) inp.dataset.decimalsBound = '1';

      inp.addEventListener('input', function () {
        if (typeof inp.value === 'string' && inp.value.indexOf(',') !== -1) {
          inp.value = inp.value.replace(',', '.');
        }
      });

      inp.addEventListener('blur', function () {
        var d = inp.getAttribute('data-decimals');
        var v = normalizeDecimalValue(inp.value, d);
        if (v !== inp.value) inp.value = v;

        // jei tai kainos laukas formsete – emitinam kainos pokytį, kad preview atsinaujintų
        var name = inp.getAttribute('name') || '';
        if (name && name.slice(-6) === '-kaina') {
          var prefix = getClosestFormsetPrefix(inp);
          if (prefix) emit('kainos:changed', { prefix: prefix, reason: 'decimal-blur' });
          else emit('kainos:changed', { reason: 'decimal-blur' });
        }
      });
    });
  }

  function initAutoResize(root) {
    $all('textarea[data-autoresize="1"]', root).forEach(function (ta) {
      if (ta.dataset && ta.dataset.autoresizeBound === '1') return;
      if (ta.dataset) ta.dataset.autoresizeBound = '1';
      autoGrow(ta);
      ta.addEventListener('input', function () { autoGrow(ta); });
    });
  }

  // ------------------------
  // Kainų formset
  // ------------------------
  function isLikelyCompleteDateValue(v) {
    return typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v);
  }

  function bindDateTabGuard(row) {
    $all('input[type="date"]', row).forEach(function (inp) {
      if (inp.dataset && inp.dataset.tabGuard === '1') return;
      if (inp.dataset) inp.dataset.tabGuard = '1';

      inp.addEventListener('keydown', function (e) {
        if (e.key !== 'Tab' || e.altKey || e.ctrlKey || e.metaKey) return;

        var v = inp.value || '';
        if (isLikelyCompleteDateValue(v)) return;

        e.preventDefault();

        try {
          inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', code: 'ArrowRight', bubbles: true }));
          inp.dispatchEvent(new KeyboardEvent('keyup', { key: 'ArrowRight', code: 'ArrowRight', bubbles: true }));
        } catch (_) {}

        try {
          inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', code: 'ArrowDown', bubbles: true }));
          inp.dispatchEvent(new KeyboardEvent('keyup', { key: 'ArrowDown', code: 'ArrowDown', bubbles: true }));
        } catch (_) {}
      });
    });
  }

  function initKainosRow(row) {
    initAutoResize(row);
    bindDateTabGuard(row);
    bindDecimalInputs(row);
  }

  function initKainosFormset(root) {
    if (!root) return;
    if (root.dataset && root.dataset.kainosBooted === '1') return;
    if (root.dataset) root.dataset.kainosBooted = '1';

    var prefix = root.getAttribute('data-prefix') || (root.dataset ? root.dataset.prefix : null);
    if (!prefix) return;

    var formEl = root.closest ? root.closest('form') : null;
    var body = $('#kainu-formset-body-' + prefix, root);
    var addBtn = $('#kainos-add-row-' + prefix, root);
    var tmpl = document.getElementById('kainos-empty-template-' + prefix);
    var totalInput = formEl ? formEl.querySelector('input[name="' + prefix + '-TOTAL_FORMS"]') : null;

    if (!formEl || !body || !addBtn || !totalInput || !tmpl) return;

    function removeEmptyRowIfPresent() {
      var empty = body.querySelector('tr[data-empty-row="1"]');
      if (empty) empty.remove();
    }

    $all('tr.kaina-row', body).forEach(initKainosRow);

    if (!(body.dataset && body.dataset.kainosDelegated === '1')) {
      if (body.dataset) body.dataset.kainosDelegated = '1';

      var fire = function (reason) { emit('kainos:changed', { prefix: prefix, reason: reason || 'input' }); };

      body.addEventListener('input', function (e) {
        var t = e.target;
        if (!t) return;
        var n = t.getAttribute('name') || '';
        if (
          n.slice(-6) === '-kaina' ||
          n.slice(-10) === '-busena_ui' ||
          n.slice(-7) === '-pastaba' ||
          n.slice(-10) === '-kiekis_nuo' ||
          n.slice(-10) === '-kiekis_iki'
        ) {
          fire('input');
        }
      });

      body.addEventListener('change', function (e) {
        var t = e.target;
        if (!t) return;
        var n = t.getAttribute('name') || '';
        if (
          n.slice(-7) === '-DELETE' ||
          n.slice(-10) === '-busena_ui' ||
          n.slice(-12) === '-galioja_nuo' ||
          n.slice(-12) === '-galioja_iki' ||
          n.slice(-6) === '-matas'
        ) {
          fire('change');
        }
      });
    }

    emit('kainos:changed', { prefix: prefix, reason: 'init' });

    addBtn.addEventListener('click', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();

      removeEmptyRowIfPresent();

      var i = parseInt(totalInput.value || '0', 10) || 0;
      var html = (tmpl.innerHTML || '').replace(/__prefix__/g, String(i));

      var tmp = document.createElement('tbody');
      tmp.innerHTML = html.trim();

      var row = tmp.querySelector('tr');
      if (!row) return;

      body.appendChild(row);

      var newTotal = i + 1;
      totalInput.value = String(newTotal);
      totalInput.setAttribute('value', String(newTotal));

      initKainosRow(row);
      emit('kainos:changed', { prefix: prefix, reason: 'add-row' });
    });
  }

  function initAllKainosFormsets() {
    $all('.kainos-formset[data-prefix]').forEach(initKainosFormset);
  }

  // ------------------------
  // Maskavimas (2 formsetai: KTL + Miltai)
  // ------------------------
  function initMaskavimasFormset(prefix) {
    var items = document.getElementById(prefix + '-items');
    var addBtn = document.querySelector('.maskavimas-add[data-mask-prefix="' + prefix + '"]');
    var tpl = document.getElementById(prefix + '-empty-form');

    var totalEl = document.getElementById('id_' + prefix + '-TOTAL_FORMS');
    if (!items || !totalEl) return;

    function anyVisible() {
      var list = items.querySelectorAll('.maskavimas-item[data-mask-prefix="' + prefix + '"]');
      for (var i = 0; i < list.length; i++) {
        if (list[i].style.display !== 'none') return true;
      }
      return false;
    }

    function sync(reason) {
      items.style.display = anyVisible() ? '' : 'none';
      emit('maskavimas:changed', { prefix: prefix, count: anyVisible() ? 1 : 0, reason: reason || 'sync' });
    }

    function addRow() {
      if (!tpl) return;
      var idx = parseInt(totalEl.value || '0', 10) || 0;

      var html = (tpl.innerHTML || '').replace(/__prefix__/g, String(idx));
      var wrap = document.createElement('div');
      wrap.innerHTML = html.trim();
      var node = wrap.firstElementChild;
      if (!node) return;

      items.appendChild(node);
      totalEl.value = String(idx + 1);
      totalEl.setAttribute('value', String(idx + 1));

      initAutoResize(node);
      bindDecimalInputs(node);

      sync('add-row');
    }

    // delegation remove
    if (!(items.dataset && items.dataset.maskDelegated === '1')) {
      if (items.dataset) items.dataset.maskDelegated = '1';

      items.addEventListener('click', function (e) {
        var btn = e.target && e.target.closest ? e.target.closest('.maskavimas-remove[data-mask-prefix="' + prefix + '"]') : null;
        if (!btn) return;

        var item = btn.closest('.maskavimas-item[data-mask-prefix="' + prefix + '"]');
        if (!item) return;

        var del = item.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (del) del.checked = true;
        item.style.display = 'none';
        sync('remove-row');
      });
    }

    if (addBtn && !(addBtn.dataset && addBtn.dataset.maskAddBound === '1')) {
      if (addBtn.dataset) addBtn.dataset.maskAddBound = '1';
      addBtn.addEventListener('click', function () { addRow(); });
    }

    // init existing
    $all('.maskavimas-item[data-mask-prefix="' + prefix + '"]', items).forEach(function (node) {
      initAutoResize(node);
      bindDecimalInputs(node);
    });

    sync('init');
  }

  function initMaskavimas() {
    initMaskavimasFormset('maskavimas_ktl');
    initMaskavimasFormset('maskavimas_miltai');
  }

  // ------------------------
  // Paslauga (sutarta: KTL + Miltai gali būti abu)
  // - Paruošimas privalomas, jei KTL arba Miltai true (A1)
  // - Presetai pildomi init metu ir įjungimo momentu, bet tik jei laukas tuščias (B2 + "tik jei tuščia")
  // - Spalva rodoma abiem (Variantas B)
  // ------------------------
  function initPaslaugos() {
    var chkKTL = document.getElementById('id_paslauga_ktl');
    var chkMiltai = document.getElementById('id_paslauga_miltai');
    var chkPar = document.getElementById('id_paslauga_paruosimas');

    if (!chkKTL || !chkMiltai || !chkPar) return;

    var inpPar = document.getElementById('id_paruosimas');
    var inpPad = document.getElementById('id_padengimas');
    var inpStd = document.getElementById('id_padengimo_standartas');

    // legacy spalva – paslepta, bet sinchronizuojam su miltų spalva
    var inpSpalvaLegacy = document.getElementById('id_spalva');
    var inpMiltuSpalva = document.getElementById('id_miltu_spalva');

    var ktlBox = document.getElementById('ktl-subblock');
    var miltaiBox = document.getElementById('miltai-subblock');
    var subGrid = document.getElementById('paslauga-subgrid');

    function isEmpty(el) {
      if (!el) return true;
      return !((el.value || '').toString().trim());
    }

    function setIfEmpty(el, val) {
      if (!el) return;
      if (isEmpty(el)) el.value = val;
    }

    function enforceParuosimas() {
      var need = (!!chkKTL.checked) || (!!chkMiltai.checked);
      if (need) {
        chkPar.checked = true;
        chkPar.disabled = true;
        var wrap = document.getElementById('paruosimas-lock-wrap');
        if (wrap) wrap.title = 'Privalomas, kai įjungtas KTL arba Miltai';
      } else {
        chkPar.disabled = false;
      }
    }

    function syncLegacySpalva() {
      if (!inpSpalvaLegacy) return;
      if (!!chkMiltai.checked && inpMiltuSpalva) {
        inpSpalvaLegacy.value = inpMiltuSpalva.value || '';
      } else {
        inpSpalvaLegacy.value = '';
      }
    }

    function syncKTLsandauga() {
      var a = document.getElementById('id_ktl_ilgis_mm');
      var b = document.getElementById('id_ktl_aukstis_mm');
      var c = document.getElementById('id_ktl_gylis_mm');
      var out = document.getElementById('ktl-sandauga-preview');
      if (!a || !b || !c || !out) return;

      function val(x) {
        var s = (x.value || '').toString().trim().replace(',', '.');
        if (!s) return null;
        var n = Number(s);
        return isFinite(n) ? n : null;
      }
      var av = val(a), bv = val(b), cv = val(c);
      if (av == null || bv == null || cv == null) {
        out.value = '';
        return;
      }
      var r = av * bv * cv;
      if (!isFinite(r)) out.value = '';
      else out.value = r.toFixed(1);
    }

    function sync(reason, source) {
      enforceParuosimas();

      // presetai (tik tuštiems)
      if (!!chkPar.checked && !(!!chkKTL.checked) && !(!!chkMiltai.checked)) {
        setIfEmpty(inpPar, 'Gardobond 24T');
      }
      if (!!chkKTL.checked) {
        setIfEmpty(inpPad, 'KTL BASF CG 570');
        if (inpStd && inpStd.value == null) inpStd.value = '';
      }

      setShown(ktlBox, !!chkKTL.checked);
      setShown(miltaiBox, !!chkMiltai.checked);

      if (subGrid) {
        var both = (!!chkKTL.checked) && (!!chkMiltai.checked);
        if (both) subGrid.classList.remove('one-col');
        else subGrid.classList.add('one-col');
      }

      syncLegacySpalva();
      syncKTLsandauga();

      emit('paslauga:changed', {
        ktl: !!chkKTL.checked,
        miltai: !!chkMiltai.checked,
        paruosimas: !!chkPar.checked,
        reason: reason || 'sync',
        source: source || null
      });
    }

    function bind(el, src) {
      if (!el) return;
      var key = 'boundPaslaugos' + (src || '');
      if (el.dataset && el.dataset[key] === '1') return;
      if (el.dataset) el.dataset[key] = '1';
      el.addEventListener('change', function () { sync('change', src || null); });
    }

    bind(chkKTL, 'ktl');
    bind(chkMiltai, 'miltai');

    // Paruošimas – jei privalomas, neleidžiam išjungti (JS enforce)
    bind(chkPar, 'paruosimas');

    if (inpMiltuSpalva && !(inpMiltuSpalva.dataset && inpMiltuSpalva.dataset.boundMiltuSpalva === '1')) {
      if (inpMiltuSpalva.dataset) inpMiltuSpalva.dataset.boundMiltuSpalva = '1';
      inpMiltuSpalva.addEventListener('input', function () { syncLegacySpalva(); });
      inpMiltuSpalva.addEventListener('change', function () { syncLegacySpalva(); });
    }

    ['id_ktl_ilgis_mm', 'id_ktl_aukstis_mm', 'id_ktl_gylis_mm'].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      if (el.dataset && el.dataset.boundSandauga === '1') return;
      if (el.dataset) el.dataset.boundSandauga = '1';
      el.addEventListener('input', function () { syncKTLsandauga(); });
      el.addEventListener('change', function () { syncKTLsandauga(); });
      el.addEventListener('blur', function () { syncKTLsandauga(); });
    });

    sync('init', null);
  }

  // ------------------------
  // Kabinimas (KTL + Miltai rodomi nepriklausomai, pagal Paslaugos checkbox'us)
  // ------------------------
  function initKabinimas() {
    var chkKTL = document.getElementById('id_paslauga_ktl');
    var chkMiltai = document.getElementById('id_paslauga_miltai');

    var ktlStatus = document.getElementById('ktl-kabinimas-status');
    var ktlBlock = document.getElementById('ktl-kabinimas-subblock');

    var miltaiStatus = document.getElementById('miltai-kabinimas-status');
    var miltaiBlock = document.getElementById('miltai-kabinimas-subblock');

    // Jei šito template neturi – išeinam tyliai.
    if ((!ktlStatus && !ktlBlock) && (!miltaiStatus && !miltaiBlock)) return;
    if (!chkKTL && !chkMiltai) return;

    function sync(reason) {
      var ktlOn = !!(chkKTL && chkKTL.checked);
      var miltaiOn = !!(chkMiltai && chkMiltai.checked);

      setText(ktlStatus, ktlOn ? 'Įjungta' : '—');
      setShown(ktlBlock, ktlOn);

      setText(miltaiStatus, miltaiOn ? 'Įjungta' : '—');
      setShown(miltaiBlock, miltaiOn);

      emit('kabinimas:changed', {
        ktl: ktlOn,
        miltai: miltaiOn,
        reason: reason || 'sync'
      });
    }

    function bind(el) {
      if (!el) return;
      if (el.dataset && el.dataset.boundKabinimas === '1') return;
      if (el.dataset) el.dataset.boundKabinimas = '1';
      el.addEventListener('change', function () { sync('change'); });
    }

    bind(chkKTL);
    bind(chkMiltai);

    // Jei paslauga emitina event'ą – paklausom ir jo (suderinamumui)
    if (!(document.documentElement.dataset && document.documentElement.dataset.boundKabinimasBus === '1')) {
      if (document.documentElement.dataset) document.documentElement.dataset.boundKabinimasBus = '1';
      document.addEventListener('paslauga:changed', function () { sync('bus'); });
    }

    sync('init');
  }

  // ------------------------
  // Papildomos paslaugos
  // ------------------------
  function initPapildomosPaslaugos() {
    var ppSel = document.getElementById('id_papildomos_paslaugos');
    var ppRow = document.getElementById('papildomos-paslaugos-aprasymas-row');
    var ppTxt = document.getElementById('id_papildomos_paslaugos_aprasymas');

    if (!ppSel || !ppRow) return;

    function sync(reason) {
      var val = (ppSel.value || '').toLowerCase();
      var show = (val === 'taip');
      ppRow.style.display = show ? '' : 'none';
      if (!show && ppTxt) {
        ppTxt.value = '';
        autoGrow(ppTxt);
      }
      if (show && ppTxt) autoGrow(ppTxt);

      emit('papildomos:changed', {
        yra: show,
        reason: reason || 'sync'
      });
    }

    if (!(ppSel.dataset && ppSel.dataset.boundPapildomos === '1')) {
      if (ppSel.dataset) ppSel.dataset.boundPapildomos = '1';
      ppSel.addEventListener('change', function () { sync('change'); });
    }

    sync('init');
  }

  // ------------------------
  // Matmenys XYZ
  // ------------------------
  function initXYZ() {
    var xEl = document.getElementById('id_x_mm');
    var yEl = document.getElementById('id_y_mm');
    var zEl = document.getElementById('id_z_mm');
    var xyzPreview = document.getElementById('matmenys-xyz-preview');

    if (!xyzPreview) return;

    function fmtDim(v) {
      v = (v || '').toString().trim();
      return v ? v : '—';
    }

    function sync(reason) {
      var x = xEl ? fmtDim(xEl.value) : '—';
      var y = yEl ? fmtDim(yEl.value) : '—';
      var z = zEl ? fmtDim(zEl.value) : '—';

      if (x === '—' && y === '—' && z === '—') {
        xyzPreview.textContent = '—';
      } else {
        xyzPreview.textContent = x + '×' + y + '×' + z + ' mm';
      }

      emit('xyz:changed', {
        x: xEl ? (xEl.value || '') : '',
        y: yEl ? (yEl.value || '') : '',
        z: zEl ? (zEl.value || '') : '',
        reason: reason || 'sync'
      });
    }

    if (xEl && !(xEl.dataset && xEl.dataset.boundXYZ === '1')) {
      if (xEl.dataset) xEl.dataset.boundXYZ = '1';
      xEl.addEventListener('input', function () { sync('input'); });
    }
    if (yEl && !(yEl.dataset && yEl.dataset.boundXYZ === '1')) {
      if (yEl.dataset) yEl.dataset.boundXYZ = '1';
      yEl.addEventListener('input', function () { sync('input'); });
    }
    if (zEl && !(zEl.dataset && zEl.dataset.boundXYZ === '1')) {
      if (zEl.dataset) zEl.dataset.boundXYZ = '1';
      zEl.addEventListener('input', function () { sync('input'); });
    }

    sync('init');
  }

  // ------------------------
  // Kainos preview
  // ------------------------
  function computeMainKainaFromDom() {
    var formset = document.querySelector('.kainos-formset[data-prefix]');
    if (!formset) return null;

    var rows = $all('tr.kaina-row', formset);
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];

      var del = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (del && del.checked) continue;

      var bus = row.querySelector('select[name$="-busena_ui"]');
      if (bus && (bus.value || '').toLowerCase() !== 'aktuali') continue;

      var kainaInp = row.querySelector('input[name$="-kaina"]');
      var raw = kainaInp ? (kainaInp.value || '').trim() : '';
      if (!raw) continue;

      var v = normalizeDecimalValue(raw, 4);
      return v || raw;
    }
    return null;
  }

  function renderKainaPreview() {
    var box = document.getElementById('kaina-eur-preview');
    if (!box) return;
    var strong = box.querySelector('strong');
    if (!strong) return;

    var v = computeMainKainaFromDom();
    strong.textContent = v ? (v + ' €') : '—';
  }

  function initKainosPreview() {
    if (document.documentElement.dataset && document.documentElement.dataset.kainosPreviewBound === '1') return;
    if (document.documentElement.dataset) document.documentElement.dataset.kainosPreviewBound = '1';
    document.addEventListener('kainos:changed', renderKainaPreview);
    renderKainaPreview();
  }

  // ------------------------
  // Rules router (blokų susiejimas per event bus)
  // ------------------------
  function bindRulesRouter() {
    if (document.documentElement.dataset && document.documentElement.dataset.rulesRouterBound === '1') return;
    if (document.documentElement.dataset) document.documentElement.dataset.rulesRouterBound = '1';

    document.addEventListener('paslauga:changed', function () {});
    document.addEventListener('kabinimas:changed', function () {});
    document.addEventListener('maskavimas:changed', function () {});
    document.addEventListener('papildomos:changed', function () {});
    document.addEventListener('xyz:changed', function () {});
    document.addEventListener('kainos:changed', function () {});
  }

  // ------------------------
  // Boot
  // ------------------------
  function init() {
    initAutoResize(document);
    bindDecimalInputs(document);

    initMaskavimas();
    initPaslaugos();

    // Kabinimas priklauso nuo paslaugų checkbox'ų, todėl inicijuojam po initPaslaugos()
    initKabinimas();

    initPapildomosPaslaugos();
    initXYZ();
    initAllKainosFormsets();
    initKainosPreview();
    bindRulesRouter();
  }

  window.PozFormEngine = {
    init: init,
    initKainosFormset: initKainosFormset
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
