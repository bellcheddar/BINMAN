/* The ternary triangle (spec 6.3).
 *
 * The answer to "what am I currently looking at", always visible in the header.
 * Corners fill as they are pinned, an edge lights when a real structural link
 * exists between the pinned pair, and the centre resolves only when all three
 * are pinned. Clicking a corner jumps to that module.
 */
(function (global) {
  'use strict';

  var CORNER_TARGETS = {
    glue: '/',
    ligase: '/e3/',
    target: '/degron/',
    centre: '/degradability/'
  };

  /* Which selection slot each corner reflects. */
  var CORNER_SLOT = { glue: 'glue', ligase: 'e3', target: 'target' };

  function describe(selection) {
    var parts = [];
    if (selection.glue) { parts.push('glue ' + selection.glue); }
    if (selection.e3) { parts.push('ligase ' + selection.e3); }
    if (selection.target) { parts.push('target ' + selection.target); }
    if (selection.site) { parts.push('site ' + selection.site); }
    return parts.length ? 'Pinned: ' + parts.join('; ') + '.' : 'Nothing pinned yet.';
  }

  function init() {
    var svg = document.getElementById('ternary');
    if (!svg || !global.BINMAN || !global.BINMAN.Selection) { return; }
    var Selection = global.BINMAN.Selection;
    var desc = svg.querySelector('#ternary-desc');

    function render(selection) {
      Object.keys(CORNER_SLOT).forEach(function (corner) {
        var node = svg.querySelector('[data-corner="' + corner + '"]');
        if (!node) { return; }
        var pinned = !!selection[CORNER_SLOT[corner]];
        node.classList.toggle('is-pinned', pinned);
        var slot = CORNER_SLOT[corner];
        node.setAttribute('aria-pressed', pinned ? 'true' : 'false');
        node.setAttribute('aria-label',
          corner + ' corner: ' + (pinned ? 'pinned to ' + selection[slot] : 'not pinned'));
      });

      /* An edge lights only when both ends are pinned. Whether a *structural*
       * link exists is a question for the atlas, so the edge is marked
       * provisional until the API confirms it. */
      [['glue-ligase', 'glue', 'e3'],
       ['glue-target', 'glue', 'target'],
       ['ligase-target', 'e3', 'target']].forEach(function (triple) {
        var edge = svg.querySelector('[data-edge="' + triple[0] + '"]');
        if (!edge) { return; }
        edge.classList.toggle('is-live', !!(selection[triple[1]] && selection[triple[2]]));
      });

      var centre = svg.querySelector('[data-corner="centre"]');
      if (centre) { centre.classList.toggle('is-resolved', Selection.isComplete()); }
      if (desc) { desc.textContent = describe(selection); }
    }

    function activate(corner) {
      var href = CORNER_TARGETS[corner];
      if (!href) { return; }
      global.location.href = href + (global.location.hash || '');
    }

    svg.querySelectorAll('[data-corner]').forEach(function (node) {
      var corner = node.getAttribute('data-corner');
      node.addEventListener('click', function () { activate(corner); });
      node.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          activate(corner);
        }
      });
    });

    Selection.subscribe(render);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}(window));
