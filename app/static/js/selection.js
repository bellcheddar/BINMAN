/* The shared selection object (spec 6.3).
 *
 * A single object {glue, e3, target, site} held in one place and shared by every
 * module and every viewer. Changing it anywhere updates everything. It is also
 * the deep link: the state round-trips through the URL fragment, so any view can
 * be shared as a plain URL.
 *
 * Deliberately a tiny pub/sub rather than a framework. There is no React, Vue or
 * build step in this project (spec 3.2).
 */
(function (global) {
  'use strict';

  var KEYS = ['glue', 'e3', 'target', 'site'];
  var state = { glue: null, e3: null, target: null, site: null };
  var listeners = [];
  var suppress = false;

  function readFragment() {
    var raw = (global.location.hash || '').replace(/^#/, '');
    if (!raw) { return; }
    var params = new URLSearchParams(raw);
    KEYS.forEach(function (key) {
      var value = params.get(key);
      state[key] = value ? decodeURIComponent(value) : null;
    });
  }

  function writeFragment() {
    var params = new URLSearchParams();
    KEYS.forEach(function (key) {
      if (state[key]) { params.set(key, state[key]); }
    });
    var next = params.toString();
    var url = global.location.pathname + global.location.search + (next ? '#' + next : '');
    // replaceState keeps the back button meaningful: pinning is not navigation.
    global.history.replaceState(null, '', url);
  }

  function notify(changed) {
    var snapshot = Selection.get();
    listeners.forEach(function (fn) {
      try { fn(snapshot, changed); } catch (e) { console.error('selection listener failed', e); }
    });
  }

  var Selection = {
    keys: KEYS,

    get: function () {
      return { glue: state.glue, e3: state.e3, target: state.target, site: state.site };
    },

    value: function (key) { return state[key] || null; },

    /* Pin one or more slots. Pass null to clear a slot. */
    set: function (patch) {
      var changed = [];
      Object.keys(patch || {}).forEach(function (key) {
        if (KEYS.indexOf(key) === -1) { return; }
        var next = patch[key] || null;
        if (state[key] !== next) { state[key] = next; changed.push(key); }
      });
      if (!changed.length) { return changed; }
      if (!suppress) { writeFragment(); }
      notify(changed);
      return changed;
    },

    clear: function () {
      return Selection.set({ glue: null, e3: null, target: null, site: null });
    },

    /* How many of the three corners are pinned. The centre resolves at three. */
    pinnedCount: function () {
      return ['glue', 'e3', 'target'].filter(function (k) { return !!state[k]; }).length;
    },

    isComplete: function () { return Selection.pinnedCount() === 3; },

    subscribe: function (fn) {
      if (typeof fn !== 'function') { return function () {}; }
      listeners.push(fn);
      // Fire immediately so a late subscriber renders the current state.
      try { fn(Selection.get(), []); } catch (e) { console.error(e); }
      return function () {
        var index = listeners.indexOf(fn);
        if (index > -1) { listeners.splice(index, 1); }
      };
    },

    /* Apply a whole record to the selection, working out which slots it fills. */
    fromRecord: function (recordType, row) {
      if (!row) { return; }
      var patch = {};
      if (recordType === 'bridge') {
        patch.glue = row.ccd_id ? row.pdb_id + ':' + row.ccd_id + ':' + (row.id || '') : null;
      } else if (recordType === 'ligase') {
        patch.e3 = row.uniprot_acc || null;
      } else if (recordType === 'degron') {
        patch.target = row.uniprot_acc || null;
      } else if (recordType === 'lysine') {
        patch.target = row.uniprot_acc || null;
        patch.site = row.site_id || null;
      }
      return Selection.set(patch);
    }
  };

  readFragment();

  global.addEventListener('hashchange', function () {
    suppress = true;
    var before = JSON.stringify(state);
    readFragment();
    suppress = false;
    if (JSON.stringify(state) !== before) { notify(KEYS); }
  });

  global.BINMAN = global.BINMAN || {};
  global.BINMAN.Selection = Selection;
}(window));
