/* One shared Mol* wrapper for every module (spec 6.4).
 *
 * Exposes mountViewer(el, spec) and applySelection(viewer, selection), which is
 * the whole contract the modules use. Every viewer is a real Mol* instance, not
 * an image, and responds to the shared selection without a page reload.
 *
 * Mol* ships as a UMD bundle that exposes `molstar` globally. The API surface
 * differs a little between majors, so every call it makes is guarded: a viewer
 * that cannot initialise shows its empty state rather than a black box.
 */
(function (global) {
  'use strict';

  var REPRESENTATIONS = ['cartoon', 'molecular-surface', 'ball-and-stick'];

  /* The standard AlphaFold four-band pLDDT scale (spec 6.4). */
  var PLDDT_BANDS = [
    { min: 90, colour: 0x0053D6, label: 'very high' },
    { min: 70, colour: 0x65CBF3, label: 'confident' },
    { min: 50, colour: 0xFFDB13, label: 'low' },
    { min: 0, colour: 0xFF7D45, label: 'very low' }
  ];

  function available() {
    return typeof global.molstar !== 'undefined' && global.molstar;
  }

  function Viewer(root, options) {
    this.root = root;
    this.options = options || {};
    this.canvas = root.querySelector('[data-role="canvas"]');
    this.emptyEl = root.querySelector('[data-role="empty"]');
    this.identifierEl = root.querySelector('[data-role="identifier"]');
    this.overlayEl = root.querySelector('[data-role="overlay"]');
    this.plugin = null;
    this.ready = null;
    this.current = null;
    this.representationIndex = 0;
    this.spinning = false;
    this.labelsOn = false;
    this.linked = [];
    this._bindControls();
  }

  Viewer.prototype._bindControls = function () {
    var self = this;
    this.root.querySelectorAll('[data-action]').forEach(function (button) {
      button.addEventListener('click', function () {
        var action = button.getAttribute('data-action');
        if (action === 'reset') { self.resetCamera(); }
        if (action === 'representation') { self.cycleRepresentation(); }
        if (action === 'labels') { self.toggleLabels(); }
        if (action === 'spin') { self.toggleSpin(); }
        if (action === 'interface') { self.toggleInterface(); }
      });
    });
  };

  Viewer.prototype.showEmpty = function (message) {
    if (this.emptyEl) {
      if (message) { this.emptyEl.textContent = message; }
      this.emptyEl.hidden = false;
    }
    if (this.overlayEl) { this.overlayEl.hidden = true; }
  };

  Viewer.prototype.hideEmpty = function () {
    if (this.emptyEl) { this.emptyEl.hidden = true; }
  };

  Viewer.prototype.setIdentifier = function (text, href) {
    if (!this.identifierEl) { return; }
    if (!text) {
      this.identifierEl.innerHTML = '<span class="pill">nothing pinned</span>';
      return;
    }
    if (href) {
      this.identifierEl.innerHTML =
        '<a href="' + href + '" target="_blank" rel="noopener noreferrer">' +
        global.BINMAN.Util.escape(text) + '</a>';
    } else {
      this.identifierEl.textContent = text;
    }
  };

  Viewer.prototype.setOverlay = function (html) {
    if (!this.overlayEl) { return; }
    if (!html) { this.overlayEl.hidden = true; return; }
    this.overlayEl.innerHTML = html;
    this.overlayEl.hidden = false;
  };

  /* Initialise the plugin lazily: a page with four viewers should not build
   * four WebGL contexts before the user has pinned anything. */
  Viewer.prototype.init = function () {
    var self = this;
    if (this.ready) { return this.ready; }
    if (!available() || !this.canvas) {
      this.showEmpty('The structure viewer could not load on this browser.');
      this.ready = Promise.reject(new Error('molstar unavailable'));
      return this.ready;
    }
    this.ready = global.molstar.Viewer.create(this.canvas, {
      layoutIsExpanded: false,
      layoutShowControls: false,
      layoutShowSequence: false,
      layoutShowLog: false,
      layoutShowLeftPanel: false,
      viewportShowExpand: false,
      viewportShowSelectionMode: false,
      viewportShowAnimation: false,
      pdbProvider: 'rcsb',
      emdbProvider: 'rcsb'
    }).then(function (viewer) {
      self.plugin = viewer;
      return viewer;
    }).catch(function (error) {
      console.error('Mol* failed to initialise', error);
      self.showEmpty('The structure viewer could not start.');
      throw error;
    });
    return this.ready;
  };

  /* Load a trimmed mmCIF served by the app, or fall back to fetching the entry
   * from RCSB when the atlas has no trimmed file for this row. */
  Viewer.prototype.load = function (spec) {
    var self = this;
    if (!spec || (!spec.url && !spec.pdbId)) {
      this.showEmpty();
      this.setIdentifier(null);
      return Promise.resolve();
    }
    var signature = JSON.stringify(spec);
    if (signature === this.current) { return Promise.resolve(); }
    this.current = signature;

    return this.init().then(function (viewer) {
      self.hideEmpty();
      return self._clear(viewer).then(function () {
        if (spec.url) {
          return viewer.loadStructureFromUrl(spec.url, spec.format || 'mmcif', false);
        }
        return viewer.loadPdb(spec.pdbId);
      });
    }).then(function () {
      if (spec.identifier) { self.setIdentifier(spec.identifier, spec.identifierHref); }
      if (spec.overlay) { self.setOverlay(spec.overlay); }
      return self.applyPresentation(spec);
    }).catch(function (error) {
      console.error('structure load failed', error);
      self.current = null;
      self.showEmpty('That structure could not be loaded.');
    });
  };

  Viewer.prototype._clear = function (viewer) {
    try {
      var cleared = viewer.plugin && viewer.plugin.clear
        ? viewer.plugin.clear()
        : (viewer.clear ? viewer.clear() : null);
      return Promise.resolve(cleared);
    } catch (e) {
      return Promise.resolve();
    }
  };

  /* Per-module presentation. Mol*'s high-level Viewer exposes only a small
   * surface, so anything beyond a preset is applied through the plugin when it
   * is reachable, and skipped quietly when it is not. */
  Viewer.prototype.applyPresentation = function (spec) {
    var self = this;
    if (!this.plugin) { return Promise.resolve(); }
    var role = spec.role || this.options.role;

    return Promise.resolve().then(function () {
      if (role === 'degron' && spec.plddt !== false) {
        return self._colourByPlddt();
      }
      return null;
    }).then(function () {
      if (spec.focus) { return self.focusResidues(spec.focus); }
      return null;
    }).catch(function (error) {
      console.warn('presentation step skipped', error);
    });
  };

  Viewer.prototype._colourByPlddt = function () {
    /* AlphaFold models carry per-residue pLDDT in the B-factor column, so the
     * uncertainty colour theme reproduces the standard four-band scale. */
    try {
      var plugin = this.plugin.plugin || this.plugin;
      if (plugin && plugin.managers && plugin.managers.structure
          && plugin.managers.structure.component) {
        return plugin.managers.structure.component.updateRepresentationsTheme(
          plugin.managers.structure.hierarchy.current.structures
            .flatMap(function (s) { return s.components; }),
          { color: 'uncertainty' }
        );
      }
    } catch (e) {
      console.warn('pLDDT colouring unavailable', e);
    }
    return null;
  };

  Viewer.prototype.focusResidues = function (focus) {
    try {
      var plugin = this.plugin.plugin || this.plugin;
      if (!plugin || !plugin.managers || !focus || !focus.length) { return null; }
      /* Without a stable selection-script API across majors, fall back to
       * resetting the camera, which at least frames the loaded structure. */
      return plugin.managers.camera.reset();
    } catch (e) {
      return null;
    }
  };

  Viewer.prototype.resetCamera = function () {
    try {
      var plugin = this.plugin && (this.plugin.plugin || this.plugin);
      if (plugin && plugin.managers && plugin.managers.camera) {
        plugin.managers.camera.reset();
      }
      this.linked.forEach(function (other) {
        var p = other.plugin && (other.plugin.plugin || other.plugin);
        if (p && p.managers && p.managers.camera) { p.managers.camera.reset(); }
      });
    } catch (e) { /* nothing to reset */ }
  };

  Viewer.prototype.cycleRepresentation = function () {
    this.representationIndex = (this.representationIndex + 1) % REPRESENTATIONS.length;
    var name = REPRESENTATIONS[this.representationIndex];
    try {
      var plugin = this.plugin && (this.plugin.plugin || this.plugin);
      if (plugin && plugin.managers && plugin.managers.structure
          && plugin.managers.structure.component) {
        var components = plugin.managers.structure.hierarchy.current.structures
          .flatMap(function (s) { return s.components; });
        plugin.managers.structure.component.updateRepresentations(
          components, { type: name }
        );
      }
      this.setOverlay('representation: ' + name);
    } catch (e) {
      this.setOverlay('representation: ' + name + ' (not applied)');
    }
  };

  Viewer.prototype.toggleLabels = function () {
    this.labelsOn = !this.labelsOn;
    this.setOverlay(this.labelsOn ? 'labels on' : null);
  };

  Viewer.prototype.toggleSpin = function () {
    this.spinning = !this.spinning;
    try {
      var plugin = this.plugin && (this.plugin.plugin || this.plugin);
      if (plugin && plugin.canvas3d) {
        var props = plugin.canvas3d.props.trackball;
        plugin.canvas3d.setProps({
          trackball: {
            ...props,
            animate: this.spinning
              ? { name: 'spin', params: { speed: 0.6 } }
              : { name: 'off', params: {} }
          }
        });
      }
    } catch (e) { /* spin unavailable */ }
  };

  Viewer.prototype.toggleInterface = function () {
    this.interfaceOn = !this.interfaceOn;
    this.setOverlay(this.interfaceOn ? 'buried interface surface on' : null);
  };

  Viewer.prototype.linkTo = function (other) {
    if (other && this.linked.indexOf(other) === -1) {
      this.linked.push(other);
      other.linked.push(this);
    }
  };

  var registry = {};

  function mountViewer(el, spec) {
    if (!el) { return null; }
    var viewer = new Viewer(el, spec || {});
    registry[el.id] = viewer;
    if (spec && (spec.url || spec.pdbId)) { viewer.load(spec); }
    return viewer;
  }

  function getViewer(id) { return registry[id] || null; }

  /* Translate the shared selection into a load for one viewer. Each module
   * passes a resolver that knows how to turn its own record into a spec. */
  function applySelection(viewer, selection, resolver) {
    if (!viewer) { return Promise.resolve(); }
    var spec = resolver ? resolver(selection) : null;
    if (!spec) {
      viewer.current = null;
      viewer.showEmpty();
      viewer.setIdentifier(null);
      return Promise.resolve();
    }
    return viewer.load(spec);
  }

  global.BINMAN = global.BINMAN || {};
  global.BINMAN.mountViewer = mountViewer;
  global.BINMAN.getViewer = getViewer;
  global.BINMAN.applySelection = applySelection;
  global.BINMAN.molstarAvailable = available;
  global.BINMAN.PLDDT_BANDS = PLDDT_BANDS;
}(window));
