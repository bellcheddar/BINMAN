/* The Lens Graph (spec 6.3).
 *
 * A D3 force-directed E3-to-substrate network where the four modules act as
 * lenses: they recolour the same graph and change the side panel rather than
 * showing a different graph. Pruned aggressively, defaulting to the pinned
 * ligase's neighbourhood at depth 2, and never rendering more than the
 * configured node cap without the user asking.
 */
(function (global) {
  'use strict';

  var B = global.BINMAN || {};
  var Util = B.Util;
  var Selection = B.Selection;

  var state = { nodes: [], links: [], simulation: null, lens: 'family', viewer: null };

  /* Enough ticks for a few hundred nodes to stop moving. d3's own default
   * cooling schedule reaches alphaMin in about this many. */
  var SETTLE_TICKS = 320;

  /* Categorical colours drawn from the Depot tokens, read off the live
   * computed style so both themes work without a second palette. */
  function token(name, fallback) {
    var value = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (value || '').trim() || fallback;
  }

  function lensColour(node) {
    var accent = token('--accent', '#D65B0A');
    var muted = token('--muted', '#6A6F68');
    var good = token('--good', '#2C6D60');
    var warn = token('--warn', '#9A7B10');
    var bad = token('--bad', '#A33A2A');

    if (state.lens === 'pocket') {
      if (node.pocket_score === null || node.pocket_score === undefined) { return muted; }
      return node.pocket_score >= 0.5 ? good : node.pocket_score >= 0.2 ? warn : bad;
    }
    if (state.lens === 'exploitation') {
      var map = {
        'clinically validated': good,
        'chemically validated': good,
        'covalent handle only': warn,
        'ligandable unproven': warn,
        'orphan': bad
      };
      return map[node.exploitation_status] || muted;
    }
    if (state.lens === 'triage') {
      if (!node.triage_rank) { return muted; }
      return node.triage_rank <= 25 ? accent : node.triage_rank <= 100 ? warn : muted;
    }
    /* default: E3 family, with a stable hash so a family keeps its colour */
    if (node.kind !== 'ligase' || !node.family) { return muted; }
    var hash = 0;
    for (var i = 0; i < node.family.length; i += 1) {
      hash = (hash * 31 + node.family.charCodeAt(i)) % 360;
    }
    return 'hsl(' + hash + ' 45% 45%)';
  }

  function render() {
    var svg = global.d3.select('#lens-canvas');
    if (svg.empty()) { return; }
    svg.selectAll('*').remove();

    var element = document.getElementById('lens-canvas');
    var width = element.clientWidth || 800;
    var height = element.clientHeight || 560;
    svg.attr('viewBox', '0 0 ' + width + ' ' + height);

    if (!state.nodes.length) {
      svg.append('text')
        .attr('x', width / 2).attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', token('--muted', '#6A6F68'))
        .attr('font-family', token('--body', 'sans-serif'))
        .text('No edges to show. Pin a ligase, or run stage 2.4 to build the network.');
      return;
    }

    var container = svg.append('g');
    var zoom = global.d3.zoom().scaleExtent([0.2, 6]).on('zoom', function (event) {
      container.attr('transform', event.transform);
    });
    svg.call(zoom);

    /* The force layout has no bounds: with a few hundred nodes and a charge of
       -120 the graph spreads well past the viewBox and the user sees an empty
       canvas with the network somewhere off-screen. Nothing refit the view, so
       this measures the laid-out extent and scales it to fit once the
       simulation has cooled. Manual zoom still works afterwards. */
    function fitToContent() {
      if (!state.nodes.length) { return; }
      var xs = state.nodes.map(function (d) { return d.x; }).filter(Number.isFinite);
      var ys = state.nodes.map(function (d) { return d.y; }).filter(Number.isFinite);
      if (!xs.length || !ys.length) { return; }
      var pad = 40;
      var minX = Math.min.apply(null, xs), maxX = Math.max.apply(null, xs);
      var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
      var spanX = Math.max(1, maxX - minX), spanY = Math.max(1, maxY - minY);
      var scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY, 4);
      var tx = width / 2 - scale * (minX + maxX) / 2;
      var ty = height / 2 - scale * (minY + maxY) / 2;
      svg.transition().duration(400).call(
        zoom.transform,
        global.d3.zoomIdentity.translate(tx, ty).scale(scale));
    }

    /* Once the layout settles, put the selected node in the middle.
     *
     * Fitting the whole graph is the right default with nothing selected, but
     * a 344-node layout fitted to the canvas leaves the selected node as one
     * dot somewhere, and often off the visible part of a canvas taller than
     * the window. A default entry nobody can find is not a default entry.
     * The scale keeps its neighbourhood in frame rather than filling the
     * canvas with one node, and manual zoom still works afterwards.
     */
    function settle() {
      var selection = Selection.get();
      var picked = state.nodes.filter(function (d) {
        return d.id === selection.e3 || d.id === selection.target;
      })[0];
      if (!picked || !Number.isFinite(picked.x) || !Number.isFinite(picked.y)) {
        fitToContent();
        return;
      }
      /* Zoom in on the selection, but never past what the layout can fill:
       * a tight scale on a sparse neighbourhood shows an empty canvas. */
      var xs = state.nodes.map(function (d) { return d.x; }).filter(Number.isFinite);
      var ys = state.nodes.map(function (d) { return d.y; }).filter(Number.isFinite);
      var spanX = Math.max(1, Math.max.apply(null, xs) - Math.min.apply(null, xs));
      var spanY = Math.max(1, Math.max.apply(null, ys) - Math.min.apply(null, ys));
      var fitScale = Math.min((width - 80) / spanX, (height - 80) / spanY);
      var scale = Math.min(Math.max(fitScale * 2.2, 0.6), 2.5);
      svg.transition().duration(400).call(
        zoom.transform,
        global.d3.zoomIdentity
          .translate(width / 2 - scale * picked.x, height / 2 - scale * picked.y)
          .scale(scale));
    }

    var link = container.append('g').selectAll('line')
      .data(state.links).enter().append('line')
      .attr('class', 'link')
      .attr('stroke-width', function (d) { return d.type === 'curated' ? 1.6 : 0.8; });

    var node = container.append('g').selectAll('circle')
      .data(state.nodes).enter().append('circle')
      .attr('class', 'node')
      .attr('r', baseRadius)
      .attr('fill', lensColour)
      .attr('tabindex', 0)
      .on('click', function (event, d) { pick(d); })
      .on('keydown', function (event, d) {
        if (event.key === 'Enter') { pick(d); }
      });

    node.append('title').text(function (d) {
      return (d.gene || d.id) + (d.family ? ' · ' + d.family : '');
    });

    var label = container.append('g').selectAll('text')
      .data(state.nodes.filter(function (d) { return d.kind === 'ligase'; }))
      .enter().append('text')
      .attr('class', 'node-label')
      .attr('dy', -10)
      .attr('text-anchor', 'middle')
      .text(function (d) { return d.gene || d.id; });

    function positionAll() {
      link.attr('x1', function (d) { return d.source.x; })
        .attr('y1', function (d) { return d.source.y; })
        .attr('x2', function (d) { return d.target.x; })
        .attr('y2', function (d) { return d.target.y; });
      node.attr('cx', function (d) { return d.x; }).attr('cy', function (d) { return d.y; });
      label.attr('x', function (d) { return d.x; }).attr('y', function (d) { return d.y; });
    }

    state.simulation = global.d3.forceSimulation(state.nodes)
      .force('link', global.d3.forceLink(state.links).id(function (d) { return d.id; })
        .distance(60).strength(0.4))
      .force('charge', global.d3.forceManyBody().strength(-120))
      .force('centre', global.d3.forceCenter(width / 2, height / 2))
      .force('collide', global.d3.forceCollide(10))
      /* Hold the layout together. This graph is mostly small disconnected
       * components, and many-body repulsion pushes those apart without limit:
       * 344 nodes sprawled over roughly 10,000 units, so fitting them to the
       * canvas landed on a scale of 0.1 and the graph read as dust. A weak
       * pull toward the centre bounds the sprawl without flattening the
       * clusters. */
      .force('x', global.d3.forceX(width / 2).strength(0.06))
      .force('y', global.d3.forceY(height / 2).strength(0.06))
      .on('tick', positionAll)
      .on('end', settle);

    /* Settle the layout synchronously instead of animating into it.
     *
     * The fit and the centring were wired to the simulation's `end` event,
     * and with 344 nodes that event does not arrive: the rendered graph
     * carried no transform at all, so it was never fitted and the selected
     * node could sit anywhere, including off a canvas taller than the window.
     * Ticking to completion here makes the layout deterministic and present on
     * the first frame. Dragging still restarts the simulation, and `end` still
     * re-settles afterwards.
     */
    state.simulation.stop();
    for (var tick = 0; tick < SETTLE_TICKS; tick += 1) { state.simulation.tick(); }
    positionAll();
    /* Kept so the view can be re-settled once a node has been picked. Fitting
     * 344 nodes to the canvas lands on a scale of about 0.1, which is the
     * "zoomed out until nothing is visible" state; centring on the selection
     * is the useful view, and the selection does not exist yet at this point
     * in the first render. */
    state.settle = settle;
    settle();

    node.call(global.d3.drag()
      .on('start', function (event, d) {
        if (!event.active) { state.simulation.alphaTarget(0.25).restart(); }
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', function (event, d) { d.fx = event.x; d.fy = event.y; })
      .on('end', function (event, d) {
        if (!event.active) { state.simulation.alphaTarget(0); }
        d.fx = null; d.fy = null;
      }));

    highlight();
  }

  function baseRadius(d) { return d.kind === 'ligase' ? 7 : 4.5; }

  function highlight() {
    var selection = Selection.get();
    function picked(d) {
      return d.id === selection.e3 || d.id === selection.target;
    }
    /* Outlining a 4.5px dot does not make it findable among 344 of them, and
     * a default entry nobody can locate is not much of a default. The selected
     * node grows as well, which is what actually reads at this density. */
    global.d3.selectAll('#lens-canvas .node')
      .classed('is-selected', picked)
      .attr('r', function (d) { return picked(d) ? baseRadius(d) + 4 : baseRadius(d); });
  }

  function pick(node) {
    /* Clicking a node sets the shared selection, which is what makes the lens
     * graph a control rather than a picture. */
    if (node.kind === 'ligase') {
      Selection.set({ e3: node.id });
    } else {
      Selection.set({ target: node.id });
    }
    var table = document.getElementById('lens-detail');
    var empty = document.getElementById('lens-empty');
    if (!table) { return; }
    var body = table.querySelector('tbody');
    body.innerHTML = '';
    [['Accession', node.id], ['Gene', node.gene], ['Kind', node.kind],
     ['Family', node.family], ['Triage rank', node.triage_rank],
     ['Pocket score', node.pocket_score], ['Exploitation', node.exploitation_status]]
      .forEach(function (pair) {
        if (pair[1] === null || pair[1] === undefined || pair[1] === '') { return; }
        var tr = document.createElement('tr');
        var th = document.createElement('td');
        th.textContent = pair[0];
        var td = document.createElement('td');
        td.textContent = String(pair[1]);
        tr.appendChild(th); tr.appendChild(td);
        body.appendChild(tr);
      });
    table.hidden = false;
    if (empty) { empty.hidden = true; }

    if (state.viewer) {
      B.applySelection(state.viewer, Selection.get(), function () {
        return {
          role: 'lens',
          url: B.afdbCifUrl(node.id),
          format: 'mmcif',
          identifier: node.gene || node.id,
          identifierHref: 'https://www.uniprot.org/uniprotkb/' + node.id
        };
      });
    }
  }

  var autoPicked = false;

  /* Pick a node on first load, so the graph opens with a protein in the viewer
   * and a filled detail table rather than an empty frame beside it.
   *
   * The focus node when the page was asked for one, otherwise the most
   * connected node in the graph, which is the one worth looking at first and
   * is also the one the layout puts near the middle. Once only, and never over
   * a selection that is already pinned: arriving from the E3 page with a
   * ligase pinned should keep that ligase.
   */
  function autoPickFirstNode(focus) {
    if (autoPicked || !state.nodes.length) { return; }
    autoPicked = true;
    var selection = Selection.get();
    if (selection.e3 || selection.target) { return; }

    var wanted = String(focus || '').trim().toUpperCase();
    var chosen = null;
    if (wanted) {
      chosen = state.nodes.filter(function (node) {
        return String(node.id).toUpperCase() === wanted ||
          String(node.gene || '').toUpperCase() === wanted;
      })[0] || null;
    }
    if (!chosen) {
      var degree = {};
      state.links.forEach(function (link) {
        var a = link.source && link.source.id !== undefined ? link.source.id : link.source;
        var b = link.target && link.target.id !== undefined ? link.target.id : link.target;
        degree[a] = (degree[a] || 0) + 1;
        degree[b] = (degree[b] || 0) + 1;
      });
      chosen = state.nodes.slice().sort(function (x, y) {
        return (degree[y.id] || 0) - (degree[x.id] || 0);
      })[0];
    }
    if (chosen) { pick(chosen); }
  }

  function load(focus, depth) {
    var url = '/api/lens?focus=' + encodeURIComponent(focus || '') +
      '&depth=' + encodeURIComponent(depth || 2);
    return Util.get(url).then(function (result) {
      var count = document.getElementById('lens-count');
      if (!result.ok) {
        if (count) { count.textContent = (result.data && result.data.note) || 'lens unavailable'; }
        state.nodes = []; state.links = [];
        render();
        return;
      }
      state.nodes = result.data.nodes || [];
      state.links = result.data.links || [];
      if (count) {
        count.textContent = Util.num(state.nodes.length) + ' nodes, ' +
          Util.num(state.links.length) + ' edges' +
          (result.data.truncated ? ' · pruned at ' + result.data.max_nodes : '');
      }
      render();
      autoPickFirstNode(focus);
      if (state.settle) { state.settle(); }
    });
  }

  function init() {
    if (typeof global.d3 === 'undefined') { return; }
    var focusInput = document.getElementById('lens-focus');
    var depthSelect = document.getElementById('lens-depth');
    var lensSelect = document.getElementById('lens-lens');
    var loadButton = document.getElementById('lens-load');
    var expandButton = document.getElementById('lens-expand');

    state.viewer = B.mountViewer(document.getElementById('viewer-lens'), { role: 'lens' });

    if (loadButton) {
      loadButton.addEventListener('click', function () {
        load(focusInput ? focusInput.value.trim() : '', depthSelect ? depthSelect.value : 2);
      });
    }
    if (expandButton) {
      expandButton.addEventListener('click', function () {
        if (depthSelect && Number(depthSelect.value) < 3) {
          depthSelect.value = String(Number(depthSelect.value) + 1);
        }
        load(focusInput ? focusInput.value.trim() : '', depthSelect ? depthSelect.value : 3);
      });
    }
    if (lensSelect) {
      lensSelect.addEventListener('change', function () {
        state.lens = lensSelect.value;
        global.d3.selectAll('#lens-canvas .node').attr('fill', lensColour);
      });
    }

    Selection.subscribe(function (selection, changed) {
      highlight();
      /* Default to the pinned ligase's neighbourhood (spec 6.3). */
      if (changed && changed.indexOf('e3') > -1 && selection.e3 && focusInput
          && focusInput.value.trim() !== selection.e3) {
        focusInput.value = selection.e3;
        load(selection.e3, depthSelect ? depthSelect.value : 2);
      }
    });

    var initialFocus = B.lensFocus || Selection.value('e3') || '';
    if (focusInput && initialFocus) { focusInput.value = initialFocus; }
    load(initialFocus, B.lensDepth || 2);

    global.addEventListener('resize', function () {
      if (state.nodes.length) { render(); }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}(window));
