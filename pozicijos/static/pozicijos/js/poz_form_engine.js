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
  // Maskavimas
  // ------------------------
  function initMaskavimas() {
    var masTipas = document.getElementById('id_maskavimo_tipas');
    var masItems = document.getElementById('maskavimas-items');
    var masAddBtn = document.getElementById('maskavimas-add');
    var masTpl = document.getElementById('maskavimas-empty-form');

    if (!masTipas || !masItems) return;

    function getTotalFormsEl() {
      return document.getElementById('id_maskavimas-TOTAL_FORMS');
    }

    function anyVisibleMaskItem() {
      var items = masItems.querySelectorAll('.maskavimas-item');
      for (var i = 0; i < items.length; i++) {
        if (items[i].style.display !== 'none') return true;
      }
      return false;
    }

    function visibleCount() {
      var items = masItems.querySelectorAll('.maskavimas-item');
      var c = 0;
      for (var i = 0; i < items.length; i++) {
        if (items[i].style.display !== 'none') c++;
      }
      return c;
    }

    function markAllForDelete() {
      $all('.maskavimas-item', masItems).forEach(function (item) {
        var del = item.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (del) del.checked = true;
        item.style.display = 'none';
      });
    }

    function syncMaskavimasUI(changedReason) {
      var val = (masTipas.value || '').toLowerCase();

      if (val === 'yra') masItems.style.display = '';
      else masItems.style.display = 'none';

      if (anyVisibleMaskItem() && val !== 'yra') {
        masTipas.value = 'yra';
        masItems.style.display = '';
        val = 'yra';
      }

      emit('maskavimas:changed', {
        tipas: val,
        count: visibleCount(),
        reason: changedReason || 'sync'
      });
    }

    function addMaskRow() {
      if (!masTpl) return;
      var totalEl = getTotalFormsEl();
      if (!totalEl) return;

      var idx = parseInt(totalEl.value || '0', 10);

      var html = (masTpl.innerHTML || '').replace(/__prefix__/g, String(idx));
      var wrap = document.createElement('div');
      wrap.innerHTML = html.trim();
      var node = wrap.firstElementChild;
      if (!node) return;

      masItems.appendChild(node);
      totalEl.value = String(idx + 1);

      masTipas.value = 'yra';
      masItems.style.display = '';
    }

    // remove handler (delegation)
    document.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest ? e.target.closest('.maskavimas-remove') : null;
      if (!btn) return;

      var item = btn.closest('.maskavimas-item');
      if (!item) return;

      var del = item.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (del) del.checked = true;
      item.style.display = 'none';

      if (!anyVisibleMaskItem()) {
        masTipas.value = 'nera';
        masItems.style.display = 'none';
      }

      syncMaskavimasUI('remove-row');
    });

    masTipas.addEventListener('change', function () {
      var val = (masTipas.value || '').toLowerCase();
      if (val === 'nera') markAllForDelete();
      syncMaskavimasUI('tipas-change');
    });

    if (masAddBtn) {
      masAddBtn.addEventListener('click', function () {
        addMaskRow();
        syncMaskavimasUI('add-row');
      });
    }

    syncMaskavimasUI('init');
  }

  // ------------------------
  // Paslauga (sutarta: KTL + Miltai gali būti abu)
  // - Paruošimas privalomas, jei KTL arba Miltai true (A1)
  // - Presetai pildomi init metu ir įjungimo momentu, bet tik jei laukas tuščias (B2 + "tik jei tuščia")
  // - Spalva rodoma abiem (Variantas B): Miltai nebeslepia ir nebevalo "spalva"
  // ------------------------
  function initPaslaugos() {
    var chkKTL = document.getElementById('id_paslauga_ktl');
    var chkMiltai = document.getElementById('id_paslauga_miltai');
    var chkPar = document.getElementById('id_paslauga_paruosimas');

    if (!chkKTL || !chkMiltai || !chkPar) return;

    var inpPar = document.getElementById('id_paruosimas');
    var inpPad = document.getElementById('id_padengimas');
    var inpStd = document.getElementById('id_padengimo_standartas');
    var inpSpalva = document.getElementById('id_spalva');

    var miltaiBox = document.getElementById('miltai-subblock');
    var rowSpalvaTop = document.getElementById('row-spalva-top');

    function isEmpty(el) {
      if (!el) return true;
      return !((el.value || '').toString().trim());
    }

    function setIfEmpty(el, val) {
      if (!el) return;
      if (isEmpty(el)) el.value = val;
    }

    function emitPaslauga(reason, source) {
      emit('paslauga:changed', {
        ktl: !!chkKTL.checked,
        miltai: !!chkMiltai.checked,
        paruosimas: !!chkPar.checked,
        reason: reason || 'sync',
        source: source || null
      });
    }

    function enforceParuosimasIfNeeded(source) {
      // A1: tyliai priverčiam Paruošimą būti ON, jei yra KTL arba Miltai
      var need = (!!chkKTL.checked) || (!!chkMiltai.checked);
      if (need && !chkPar.checked) {
        chkPar.checked = true;
      }
      // jei need=false – nieko neprievartaujam (Paruošimas gali būti laisvas)
      emitPaslauga('enforce', source || 'constraint');
    }

    function applyPresets(reason, source) {
      // B2: presetai init metu ir įjungimo momentu – tik jei laukai tušti
      var ktl = !!chkKTL.checked;
      var miltai = !!chkMiltai.checked;
      var par = !!chkPar.checked;

      // Paruošimas tik pats: jei par tikras ir kiti false – galim įrašyti default paruošimą, bet tik jei tuščia
      if (par && !ktl && !miltai) {
        setIfEmpty(inpPar, 'Gardobond 24T');
      }

      // KTL presetai (tik jei tuščia)
      if (ktl) {
        setIfEmpty(inpPad, 'KTL BASF CG 570');
        // standartą anksčiau valydavai; čia saugiau: jei tuščia – paliekam tuščia, jei ne – nejudinam
        // jei visgi reikia "išvalyti" tik įjungimo momentu – galim pridėti atskirą taisyklę vėliau
        // spalva KTL (tik jei tuščia)
        setIfEmpty(inpSpalva, 'Juoda RAL 9005');
      }

      // UI: miltų blokas rodomas pagal Miltai=true
      if (miltaiBox) miltaiBox.style.display = miltai ? '' : 'none';

      // Variant B: spalvos eilutė visada matoma (neslepiam dėl Miltų)
      if (rowSpalvaTop) rowSpalvaTop.style.display = '';

      emitPaslauga(reason || 'sync', source || null);
    }

    function sync(changedEl, reason) {
      var source = null;
      if (changedEl === chkKTL) source = 'ktl';
      else if (changedEl === chkMiltai) source = 'miltai';
      else if (changedEl === chkPar) source = 'paruosimas';

      // Pirma: constraint'as Paruošimui
      // Jei user bando išjungti Paruošimą, kai KTL/Miltai yra – grąžinam ON (A1)
      if (changedEl === chkPar) {
        var need = (!!chkKTL.checked) || (!!chkMiltai.checked);
        if (need && !chkPar.checked) {
          chkPar.checked = true;
        }
      } else {
        // jei pasikeitė KTL arba Miltai – enforce’inam Paruošimą
        enforceParuosimasIfNeeded(source);
      }

      // Antra: presetai + UI (B2)
      applyPresets(reason || 'change', source);
    }

    function bind(el) {
      if (!el) return;
      if (el.dataset && el.dataset.boundPaslaugos === '1') return;
      if (el.dataset) el.dataset.boundPaslaugos = '1';
      el.addEventListener('change', function () { sync(el, 'change'); });
    }

    bind(chkKTL);
    bind(chkMiltai);
    bind(chkPar);

    // init: B2 (presetai tik jei tuščia) + constraint'ai
    sync(null, 'init');
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

    // Šiame etape routeris paliekamas plėtrai:
    // vėliau čia kabinsim Pakavimą ir Maskavimą reaguojant į paslaugų kombinaciją.
    document.addEventListener('paslauga:changed', function () {});
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
