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

  /* Surface first, because that is what every viewer now opens on. Cycling
   * starts from the shown state rather than jumping to cartoon on first press. */
  var REPRESENTATIONS = ['molecular-surface', 'cartoon', 'ball-and-stick'];

  /* The standard AlphaFold four-band pLDDT scale (spec 6.4). */
  var PLDDT_BANDS = [
    { min: 90, colour: 0x0053D6, label: 'very high' },
    { min: 70, colour: 0x65CBF3, label: 'confident' },
    { min: 50, colour: 0xFFDB13, label: 'low' },
    { min: 0, colour: 0xFF7D45, label: 'very low' }
  ];

  /* Ligand presentation. Every viewer frames its ligand, renders it as sticks
   * and wraps it in an emissive neon shell that Mol*'s bloom pass turns into a
   * glow. Bloom runs in `emissive` mode, so only geometry carrying emissive > 0
   * blooms: the protein behind the ligand stays readable instead of washing out.
   *
   * It is all tuning, so it lives in one place rather than spread over the call
   * sites.
   */
  var LIGAND = {
    neon: 0x00F5D4,
    /* Carbons are pinned to one vivid colour instead of being coloured by
     * chain. Chain colouring gave 7PH7's lipid cyan carbons inside a cyan
     * shell, so the ligand vanished into its own glow; the colour a ligand
     * gets should not depend on which chain it happens to sit next to.
     * Oxygen, nitrogen and sulfur keep their standard element colours, so the
     * molecule still reads chemically. */
    carbon: 0xFF2D9E,
    /* Thick enough to read through the shell. At 0.26 the sticks were thin
     * enough that the glow sat over them and the ligand looked like a cloud of
     * unconnected dots: the bonds were always there (150 atoms, 154 bonds on
     * 7PH7) and simply could not be seen. */
    stick: { sizeFactor: 0.34, aspectRatio: 1, emissive: 0.6 },
    /* A halo, not a fog. The probe radius inflates the surface clear of the
     * atoms so it reads as a shell around the molecule rather than a sheet in
     * front of it, and the emissive is well below the sticks' own so the bloom
     * pass cannot wash them out. */
    cloud: { alpha: 0.09, emissive: 0.7, probeRadius: 2.4, resolution: 0.5 },
    bloom: {
      strength: 1.3, radius: 0.6, threshold: 0,
      mode: 'emissive', transparency: true
    },
    /* The initial framing is instant. An animated fly-in competes with Mol*'s
     * own queued camera reset and loses, so the viewer silently stayed on the
     * whole structure; it is also the wrong behaviour, since the ligand should
     * already be framed when the viewer appears rather than drifting into
     * place on every pin. The Reset button animates, where a transition helps
     * the user keep their bearings. */
    /* The polymer surface is translucent so the ligand still reads through it.
     * An opaque surface fills the space a cartoon leaves open, and at a camera
     * framed on the ligand it simply swallows it. */
    polymer: { alpha: 0.45 },
    focus: {
      extraRadius: 22,
      /* A named CCD is the ligand the row is about, so it can fill the frame.
       * An inferred one is whatever non-polymer the file happened to carry,
       * and on an E3 structure that can be a single ion: framing it as tightly
       * shows a glowing dot in a void, so it is pulled back far enough to show
       * the pocket it sits in. */
      minRadius: 18, minRadiusInferred: 34,
      /* Below 1 tightens the whole-structure framing, which is the branch a
       * lens node lands in: no ligand and no named residues, so there is
       * nothing to zoom to and the default reset leaves a monomer small. */
      wholeRadiusFactor: 0.85,
      durationMs: 0, resetDurationMs: 250
    }
  };

  /* Non-polymer residues that are crystallisation furniture rather than the
   * ligand. A trimmed entry keeps whatever sat near the interface, so 10MF
   * carries 42T, 1N7, ZN and MG and only one of them is the bridge. When the
   * caller knows the CCD this list is unused; it only guards the fallback.
   *
   * Metals are deliberately absent. A zinc can be the entire point, as it is
   * in every C2H2 degron in this atlas.
   */
  var FURNITURE = {
    HOH: 1, DOD: 1, SO4: 1, PO4: 1, GOL: 1, EDO: 1, PEG: 1, PG4: 1, MPD: 1,
    DMS: 1, ACT: 1, ACY: 1, FMT: 1, TRS: 1, EPE: 1, MES: 1, IMD: 1, NH4: 1,
    IOD: 1, BME: 1, CIT: 1, TLA: 1, NO3: 1, AZI: 1
  };

  function available() {
    return typeof global.molstar !== 'undefined' && global.molstar;
  }

  /* Mol*'s viewer bundle exports a `lib` namespace carrying the real query
   * API. Without it there is no way to name the ligand, so the glow degrades
   * to framing the whole structure rather than guessing.
   */
  function structureLib() {
    var molstar = available();
    return (molstar && molstar.lib && molstar.lib.structure) || null;
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
    this.ligandTarget = null;
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
    /* The loci holds references into the structure being torn down, so it has
     * to go with it. Keeping it would point the reset button at a structure
     * that no longer exists. */
    this.ligandTarget = null;
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
      return self._surfacePolymer();
    }).then(function () {
      return self.applyLigandPresentation(spec);
    }).catch(function (error) {
      console.warn('presentation step skipped', error);
    });
  };

  Viewer.prototype._plugin = function () {
    return this.plugin ? (this.plugin.plugin || this.plugin) : null;
  };

  Viewer.prototype._structureRefs = function () {
    try {
      var plugin = this._plugin();
      return plugin.managers.structure.hierarchy.current.structures || [];
    } catch (e) {
      return [];
    }
  };

  /* The components the default preset built for non-polymer entities. Changing
   * these is how the ligand becomes sticks, and skipping them is how the
   * polymer keeps whatever representation the user has cycled to. */
  Viewer.prototype._ligandComponents = function () {
    var out = [];
    this._structureRefs().forEach(function (ref) {
      (ref.components || []).forEach(function (component) {
        var key = String(component.key || '').toLowerCase();
        var label = '';
        try {
          label = String(component.cell.obj.label || '').toLowerCase();
        } catch (e) { /* an unlabelled component is still testable by key */ }
        if (key.indexOf('ligand') >= 0 || label.indexOf('ligand') >= 0) {
          out.push(component);
        }
      });
    });
    return out;
  };

  /* The polymer components: everything the preset built that is not the ligand,
   * not water and not a lone ion. These are what become the surface. */
  Viewer.prototype._polymerComponents = function () {
    var out = [];
    this._structureRefs().forEach(function (ref) {
      (ref.components || []).forEach(function (component) {
        var key = String(component.key || '').toLowerCase();
        var label = '';
        try {
          label = String(component.cell.obj.label || '').toLowerCase();
        } catch (e) { /* key alone is enough to decide */ }
        var text = key + ' ' + label;
        if (text.indexOf('polymer') >= 0) { out.push(component); }
      });
    });
    return out;
  };

  /* Render the protein as a surface rather than ribbons.
   *
   * The ligand keeps its sticks and its shell: a surface over the ligand too
   * would bury the thing the viewer exists to show. Only the polymer changes.
   *
   * `resolution` is left on Mol*'s adaptive default rather than pinned. A
   * fixed fine resolution is affordable on a 200-residue monomer and is not on
   * a 300-chain assembly, and this atlas holds both.
   */
  Viewer.prototype._surfacePolymer = function () {
    var plugin = this._plugin();
    var components = this._polymerComponents();
    if (!plugin || !plugin.build || !components.length) {
      return Promise.resolve(false);
    }
    var update = plugin.build();
    var touched = 0;
    components.forEach(function (component) {
      (component.representations || []).forEach(function (rep) {
        if (!rep.cell) { return; }
        touched += 1;
        update.to(rep.cell).update(function (old) {
          /* params reset so the new type takes its own defaults rather than
           * inheriting the cartoon's, then the alpha applied on top. */
          old.type = {
            name: 'molecular-surface',
            params: { alpha: LIGAND.polymer.alpha }
          };
        });
      });
    });
    if (!touched) { return Promise.resolve(false); }
    return Promise.resolve(update.commit()).then(function () {
      return true;
    }).catch(function (error) {
      console.warn('polymer surface not applied', error);
      return false;
    });
  };

  /* The ligand to frame, as a Mol* loci.
   *
   * `ccdId` makes this exact, which matters: a trimmed entry keeps the
   * neighbouring ligands, so framing "every non-polymer" in 10MF would frame
   * the midpoint of 42T, 1N7, a zinc and a magnesium and show none of them
   * properly. Without a CCD it falls back to every non-furniture non-polymer.
   */
  Viewer.prototype._ligandTarget = function (ccdId) {
    var S = structureLib();
    var refs = this._structureRefs();
    if (!S || !refs.length) { return null; }
    var wanted = ccdId ? String(ccdId).toUpperCase() : null;
    var props = S.StructureProperties;
    var query = S.Queries.generators.atoms({
      entityTest: function (ctx) {
        var type = props.entity.type(ctx.element);
        return type === 'non-polymer' || type === 'branched';
      },
      residueTest: function (ctx) {
        var comp = String(props.residue.label_comp_id(ctx.element) || '').toUpperCase();
        return wanted ? comp === wanted : !FURNITURE[comp];
      }
    });
    for (var i = 0; i < refs.length; i += 1) {
      var whole = refs[i].cell && refs[i].cell.obj && refs[i].cell.obj.data;
      if (!whole) { continue; }
      try {
        var sub = S.StructureSelection.unionStructure(
          S.StructureQuery.run(query, whole));
        if (sub && sub.elementCount > 0) {
          return { loci: S.Structure.toStructureElementLoci(sub), structure: sub,
                   named: !!wanted };
        }
      } catch (e) { /* try the next loaded structure */ }
    }
    /* A named CCD that is not in this file is worth one more pass: the trimmed
     * copy may differ from the entry the row was built from. */
    return wanted ? this._ligandTarget(null) : null;
  };

  /* Sticks, by equalising the ball and stick radii. Mol*'s ball-and-stick
   * defaults to aspectRatio 5, which reads as balls threaded on wires.
   *
   * The params go through the state builder rather than
   * `managers.structure.component.updateRepresentations`, which takes three
   * arguments (components, pivot, params) and does not do what a two-argument
   * call suggests. `cycleRepresentation` had that bug.
   */
  Viewer.prototype._stickifyLigand = function () {
    var plugin = this._plugin();
    var components = this._ligandComponents();
    if (!plugin || !plugin.build || !components.length) {
      return Promise.resolve(false);
    }
    var update = plugin.build();
    var touched = 0;
    components.forEach(function (component) {
      (component.representations || []).forEach(function (rep) {
        if (!rep.cell) { return; }
        touched += 1;
        update.to(rep.cell).update(function (old) {
          /* Only retune a ball-and-stick. Renaming the type while keeping
           * another type's params is how a representation ends up with
           * nonsense settings, so anything else is left alone and the neon
           * shell below carries the effect on its own. */
          if (!old.type || old.type.name !== 'ball-and-stick') { return; }
          old.type.params = old.type.params || {};
          old.type.params.sizeFactor = LIGAND.stick.sizeFactor;
          old.type.params.aspectRatio = LIGAND.stick.aspectRatio;
          old.type.params.emissive = LIGAND.stick.emissive;
          old.colorTheme = {
            name: 'element-symbol',
            params: {
              carbonColor: { name: 'uniform', params: { value: LIGAND.carbon } }
            }
          };
        });
      });
    });
    if (!touched) { return Promise.resolve(false); }
    return Promise.resolve(update.commit()).then(function () {
      return true;
    }).catch(function (error) {
      console.warn('ligand sticks not applied', error);
      return false;
    });
  };

  /* The neon shell. A translucent molecular surface at full emissive is what
   * the bloom pass turns into a cloud; `ignoreLight` keeps it a flat glow
   * rather than a shaded blob. */
  Viewer.prototype._addLigandCloud = function () {
    var plugin = this._plugin();
    var components = this._ligandComponents();
    var builder = null;
    try {
      builder = plugin.builders.structure.representation;
    } catch (e) {
      return Promise.resolve(false);
    }
    if (!builder || !components.length) { return Promise.resolve(false); }

    var chain = Promise.resolve(false);
    components.forEach(function (component) {
      chain = chain.then(function (added) {
        return Promise.resolve(builder.addRepresentation(component.cell, {
          type: 'molecular-surface',
          typeParams: {
            alpha: LIGAND.cloud.alpha,
            emissive: LIGAND.cloud.emissive,
            probeRadius: LIGAND.cloud.probeRadius,
            resolution: LIGAND.cloud.resolution,
            ignoreLight: true
          },
          color: 'uniform',
          colorParams: { value: LIGAND.neon }
        })).then(function () {
          return true;
        }).catch(function () {
          /* Surface meshing can fail on a very small or disordered ligand.
           * Inflated spheres are the same idea with no mesh to build. */
          return Promise.resolve(builder.addRepresentation(component.cell, {
            type: 'spacefill',
            typeParams: {
              alpha: LIGAND.cloud.alpha,
              emissive: LIGAND.cloud.emissive,
              sizeFactor: 1.7,
              ignoreLight: true
            },
            color: 'uniform',
            colorParams: { value: LIGAND.neon }
          })).then(function () {
            return true;
          }).catch(function (error) {
            console.warn('ligand glow not applied', error);
            return added;
          });
        });
      });
    });
    return chain;
  };

  /* Run `fn` after the canvas has drawn once more.
   *
   * Mol* queues its own camera reset when the first object is committed, and
   * that reset lands *after* a focus issued from the load promise, so the
   * camera snapped back to the whole structure and the framing silently did
   * not happen. Waiting for the next draw puts the focus after the reset.
   */
  Viewer.prototype._afterNextDraw = function (fn) {
    var plugin = this._plugin();
    try {
      if (plugin && plugin.canvas3d && plugin.canvas3d.didDraw
          && plugin.canvas3d.didDraw.subscribe) {
        var subscription = plugin.canvas3d.didDraw.subscribe(function () {
          try { subscription.unsubscribe(); } catch (e) { /* already gone */ }
          fn();
        });
        return;
      }
    } catch (e) { /* fall through to the timer */ }
    global.setTimeout(fn, 300);
  };

  Viewer.prototype._setBloom = function (on) {
    var plugin = this._plugin();
    try {
      if (!plugin || !plugin.canvas3d) { return false; }
      plugin.canvas3d.setProps({
        postprocessing: {
          bloom: on
            ? { name: 'on', params: LIGAND.bloom }
            : { name: 'off', params: {} }
        }
      });
      return true;
    } catch (e) {
      console.warn('bloom unavailable', e);
      return false;
    }
  };

  /* Frame the ligand and orient to it. `optimizeDirection` has Mol* pick the
   * view direction from the loci's own principal axes, which is the difference
   * between zoomed in and zoomed in while actually looking at the thing. */
  Viewer.prototype.focusLigand = function (target, durationMs) {
    var plugin = this._plugin();
    try {
      if (!plugin || !plugin.managers || !plugin.managers.camera) { return false; }
      if (!target || !target.loci) { return false; }
      plugin.managers.camera.focusLoci(target.loci, {
        durationMs: durationMs === undefined ? LIGAND.focus.durationMs : durationMs,
        extraRadius: LIGAND.focus.extraRadius,
        minRadius: target.named
          ? LIGAND.focus.minRadius
          : LIGAND.focus.minRadiusInferred,
        optimizeDirection: true
      });
      return true;
    } catch (e) {
      console.warn('ligand focus failed', e);
      return false;
    }
  };

  /* A residue window as a loci, for the viewers that show an AlphaFold monomer
   * and so have no ligand to frame. `residues` is a list of {start, end} in
   * author numbering, which is what every atlas column records.
   */
  Viewer.prototype._residueTarget = function (residues) {
    var S = structureLib();
    var refs = this._structureRefs();
    if (!S || !refs.length || !residues || !residues.length) { return null; }
    var props = S.StructureProperties;
    var query = S.Queries.generators.atoms({
      residueTest: function (ctx) {
        var number = props.residue.auth_seq_id(ctx.element);
        for (var i = 0; i < residues.length; i += 1) {
          if (number >= residues[i].start && number <= residues[i].end) {
            return true;
          }
        }
        return false;
      }
    });
    for (var i = 0; i < refs.length; i += 1) {
      var whole = refs[i].cell && refs[i].cell.obj && refs[i].cell.obj.data;
      if (!whole) { continue; }
      try {
        var sub = S.StructureSelection.unionStructure(
          S.StructureQuery.run(query, whole));
        if (sub && sub.elementCount > 0) {
          /* `named`, because a residue window is as deliberate as a named CCD:
           * the row asked for these residues, so they can fill the frame. */
          return { loci: S.Structure.toStructureElementLoci(sub), structure: sub,
                   named: true };
        }
      } catch (e) { /* try the next loaded structure */ }
    }
    return null;
  };

  /* Mol*'s own focus: it renders the focused loci as ball-and-stick with its
   * surroundings, which is the sticks half of the treatment for free.
   *
   * It does not carry the neon shell. Attaching a custom representation needs
   * a component built from a selection expression, and this bundle exports the
   * query API but not the selection-expression builder, so an arbitrary
   * residue set cannot be given one. Stated rather than faked.
   */
  Viewer.prototype._focusStructureElements = function (target) {
    try {
      var plugin = this._plugin();
      if (!plugin || !plugin.managers || !plugin.managers.structure
          || !plugin.managers.structure.focus || !target) { return false; }
      plugin.managers.structure.focus.setFromLoci(target.loci);
      return true;
    } catch (e) {
      console.warn('structure focus unavailable', e);
      return false;
    }
  };

  /* Sticks, neon shell, bloom, and a camera on the ligand.
   *
   * An AlphaFold monomer has no ligand, so the degron, degradability and lens
   * viewers legitimately land in the no-ligand branch. That writes
   * `data-ligand-focus="none"` on the root instead of leaving the viewer
   * looking as though the treatment applied. This module has already shipped
   * one round of silent degradation (D-050), and a glow that quietly did not
   * happen is the same defect wearing a different hat.
   */
  Viewer.prototype.applyLigandPresentation = function (spec) {
    var self = this;
    this.ligandTarget = null;
    var target = this._ligandTarget(spec && spec.ccdId);
    if (target) {
      this.ligandTarget = target;
      this.root.setAttribute('data-ligand-focus', 'ligand');
      return this._stickifyLigand().then(function () {
        return self._addLigandCloud();
      }).then(function () {
        self._setBloom(true);
        self.focusLigand(target);
        /* Again once the canvas has drawn, so Mol*'s own queued camera reset
         * cannot land on top of the framing. */
        self._afterNextDraw(function () { self.focusLigand(target); });
        return true;
      });
    }

    /* No ligand. An AlphaFold monomer never has one, so the degron and
     * degradability viewers land here by design and get the same zoom and
     * orientation onto whatever the row is about. */
    var residues = this._residueTarget(spec && spec.focusResidues);
    this._setBloom(false);
    if (residues) {
      this.ligandTarget = residues;
      this.root.setAttribute('data-ligand-focus', 'residues');
      this._focusStructureElements(residues);
      this.focusLigand(residues);
      this._afterNextDraw(function () { self.focusLigand(residues); });
      return Promise.resolve(true);
    }
    this.root.setAttribute('data-ligand-focus', 'none');
    this._resetWholeStructure();
    /* Again after the next draw, for the same reason the ligand branch does
     * it: Mol*'s own queued camera reset lands after this one and would undo
     * the orientation. */
    this._afterNextDraw(function () { self._resetWholeStructure(); });
    return Promise.resolve(false);
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

  /* Frame the whole model, oriented to its own principal axes.
   *
   * This is the branch a lens node lands in: an AlphaFold monomer with no
   * ligand and no named residue window. A plain camera reset frames it from
   * whatever direction the file happens to be written in, which for an
   * elongated protein is usually end-on and reads as a blob. Orienting first
   * and framing second lays the longest axis across the viewport.
   */
  Viewer.prototype._resetWholeStructure = function () {
    var plugin = this._plugin();
    try {
      if (!plugin || !plugin.managers || !plugin.managers.camera) { return; }
      if (plugin.managers.camera.orientAxes) {
        /* No argument: it selects the root structures itself. */
        plugin.managers.camera.orientAxes(undefined, 0);
      }
      if (plugin.managers.camera.focusObject) {
        /* Frame the whole scene a little tighter than a plain reset, which
         * leaves a monomer sitting small in the middle of the panel. */
        plugin.managers.camera.focusObject({
          targets: [{ radiusFactor: LIGAND.focus.wholeRadiusFactor }],
          durationMs: 0
        });
      } else {
        plugin.managers.camera.reset();
      }
    } catch (e) {
      try { plugin.managers.camera.reset(); } catch (e2) { /* nothing to reset */ }
    }
  };

  /* Reset returns to the ligand, not to the whole structure: the ligand is
   * what every viewer is framed on, so "reset" should undo a user's orbit
   * rather than undo the framing. Viewers with no ligand reset as before. */
  Viewer.prototype.resetCamera = function () {
    if (this.ligandTarget) {
      this.focusLigand(this.ligandTarget, LIGAND.focus.resetDurationMs);
    } else {
      this._resetWholeStructure();
    }
    this.linked.forEach(function (other) {
      if (other.ligandTarget) {
        other.focusLigand(other.ligandTarget, LIGAND.focus.resetDurationMs);
      } else {
        other._resetWholeStructure();
      }
    });
  };

  /* Cycle the polymer representation, leaving the ligand on sticks.
   *
   * The previous version called `updateRepresentations(components, {type})`.
   * That method takes (components, pivot, params), so the type object arrived
   * as the pivot and the params were undefined: it never changed anything, and
   * the overlay said it had. The state builder is the stable route, and the
   * type's params are reset to {} so the new type gets its own defaults
   * instead of inheriting the old type's.
   */
  Viewer.prototype.cycleRepresentation = function () {
    var self = this;
    this.representationIndex = (this.representationIndex + 1) % REPRESENTATIONS.length;
    var name = REPRESENTATIONS[this.representationIndex];
    var plugin = this._plugin();
    if (!plugin || !plugin.build) {
      this.setOverlay('representation: ' + name + ' (not applied)');
      return;
    }
    var ligands = this._ligandComponents();
    var update = plugin.build();
    var touched = 0;
    this._structureRefs().forEach(function (ref) {
      (ref.components || []).forEach(function (component) {
        if (ligands.indexOf(component) >= 0) { return; }
        (component.representations || []).forEach(function (rep) {
          if (!rep.cell) { return; }
          touched += 1;
          update.to(rep.cell).update(function (old) {
            old.type = { name: name, params: {} };
          });
        });
      });
    });
    if (!touched) {
      this.setOverlay('representation: ' + name + ' (nothing to change)');
      return;
    }
    Promise.resolve(update.commit()).then(function () {
      self.setOverlay('representation: ' + name);
    }).catch(function (error) {
      console.warn('representation not applied', error);
      self.setOverlay('representation: ' + name + ' (not applied)');
    });
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
  /* AlphaFold file naming carries a model version that moves (v4 to v6 during
   * this build), so it is kept in one place rather than spread across modules. */
  global.BINMAN.AFDB_MODEL_VERSION = 'v6';
  global.BINMAN.afdbCifUrl = function (accession) {
    if (!accession) { return null; }
    return 'https://alphafold.ebi.ac.uk/files/AF-' + accession + '-F1-model_' +
      global.BINMAN.AFDB_MODEL_VERSION + '.cif';
  };
  global.BINMAN.PLDDT_BANDS = PLDDT_BANDS;
}(window));
