/* Shell behaviour: the theme toggle and small shared helpers. */
(function (global) {
  'use strict';

  function initTheme() {
    var button = document.getElementById('theme-toggle');
    if (!button) { return; }
    button.addEventListener('click', function () {
      var root = document.documentElement;
      var current = root.getAttribute('data-theme');
      /* Without an explicit theme the page follows the system, so the first
       * press flips away from whatever is currently showing. */
      if (!current) {
        var dark = global.matchMedia
          && global.matchMedia('(prefers-color-scheme: dark)').matches;
        current = dark ? 'dark' : 'light';
      }
      var next = current === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('binman-theme', next); } catch (e) { /* private mode */ }
      button.setAttribute('aria-label',
        'Switch to ' + (next === 'dark' ? 'light' : 'dark') + ' theme');
    });
  }

  var Util = {
    /* Format a number for display without implying precision it lacks. */
    num: function (value, digits) {
      if (value === null || value === undefined || value === '') { return '–'; }
      var n = Number(value);
      if (!isFinite(n)) { return String(value); }
      if (Number.isInteger(n) && Math.abs(n) < 1e6) { return n.toLocaleString('en-GB'); }
      return n.toPrecision(digits || 3).replace(/\.?0+$/, '');
    },

    pill: function (text, tone) {
      var cls = tone ? 'pill pill--' + tone : 'pill';
      return '<span class="' + cls + '">' + Util.escape(text) + '</span>';
    },

    escape: function (value) {
      return String(value === null || value === undefined ? '' : value)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    },

    post: function (url, body) {
      return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      }).then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, status: response.status, data: data };
        });
      });
    },

    get: function (url) {
      return fetch(url).then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, status: response.status, data: data };
        });
      });
    }
  };

  global.BINMAN = global.BINMAN || {};
  global.BINMAN.Util = Util;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
  } else {
    initTheme();
  }
}(window));
