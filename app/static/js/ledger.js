/* The split ledger: the query stack, the filter builder and the Tabulator table
 * (spec 6.3).
 *
 * The query stack is the app's audit trail. It accumulates readable filter lines,
 * survives a module switch (the whole stack is re-run against the new record
 * type, dropping any filter that type does not have) and copies cleanly into a
 * methods section.
 */
(function (global) {
  'use strict';

  var B = global.BINMAN || {};
  var Util = B.Util;
  var Selection = B.Selection;

  var STORAGE_KEY = 'binman-query-stack';

  var state = {
    recordType: B.recordType,
    schema: B.schema || {},
    filters: [],
    sortField: B.defaultSort,
    sortDirection: B.defaultDirection || 'desc',
    table: null,
    viewer: null,
    lastRows: [],
    pinnedRow: null
  };

  function fields() {
    var spec = state.schema[state.recordType];
    return spec ? spec.fields : {};
  }

  /* ---------------------------------------------------------------- stack --- */

  function loadStack() {
    var stored = null;
    try { stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); }
    catch (e) { stored = null; }
    if (!stored || !Array.isArray(stored.filters)) { return; }
    /* Switching module re-runs the whole stack against the new record type
     * rather than resetting it, so keep only the filters this type has. */
    var available = fields();
    state.filters = stored.filters.filter(function (f) { return !!available[f.field]; });
    state.dropped = stored.filters.length - state.filters.length;
  }

  function saveStack() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ filters: state.filters }));
    } catch (e) { /* private mode: the stack simply does not persist */ }
  }

  var OP_WORDS = {
    eq: 'is', ne: 'is not', gt: 'above', gte: 'at least', lt: 'below', lte: 'at most'
  };

  function describeFilter(filter) {
    var spec = fields()[filter.field];
    if (!spec) { return filter.field + ' ' + filter.op + ' ' + filter.value; }
    if (spec.kind === 'bool') {
      return spec.label + ' ' + (Number(filter.value) ? 'yes' : 'no');
    }
    return spec.label + ' ' + OP_WORDS[filter.op] + ' ' + filter.value +
      (spec.unit ? ' ' + spec.unit : '');
  }

  function renderStack() {
    var list = document.getElementById('stack-list');
    if (!list) { return; }
    list.innerHTML = '';
    if (!state.filters.length) {
      var empty = document.createElement('li');
      empty.className = 'stack__empty';
      empty.textContent = 'No filters yet. Everything in ' +
        (state.schema[state.recordType] || {}).label + ' is shown.';
      list.appendChild(empty);
    } else {
      state.filters.forEach(function (filter, index) {
        var item = document.createElement('li');
        var text = document.createElement('span');
        text.textContent = describeFilter(filter);
        var drop = document.createElement('button');
        drop.className = 'drop';
        drop.type = 'button';
        drop.textContent = '×';
        drop.setAttribute('aria-label', 'Remove filter: ' + describeFilter(filter));
        drop.addEventListener('click', function () {
          state.filters.splice(index, 1);
          saveStack();
          renderStack();
          run();
        });
        item.appendChild(text);
        item.appendChild(drop);
        list.appendChild(item);
      });
    }
    if (state.dropped) {
      var note = document.createElement('li');
      note.className = 'stack__empty';
      note.textContent = state.dropped + ' filter(s) dropped: not a field of this record type.';
      list.appendChild(note);
      state.dropped = 0;
    }
  }

  function stackAsText() {
    var lines = ['BINMAN query, record type: ' +
      (state.schema[state.recordType] || {}).label];
    state.filters.forEach(function (f) { lines.push('  ' + describeFilter(f)); });
    var spec = fields()[state.sortField];
    lines.push('  sorted by ' + ((spec && spec.label) || state.sortField) + ', ' +
      (state.sortDirection === 'desc' ? 'highest first' : 'lowest first'));
    return lines.join('\n');
  }

  /* -------------------------------------------------------------- builder --- */

  function initBuilder() {
    var fieldSelect = document.getElementById('f-field');
    var opSelect = document.getElementById('f-op');
    var valueInput = document.getElementById('f-value');
    var addButton = document.getElementById('f-add');
    if (!fieldSelect || !opSelect || !valueInput || !addButton) { return; }

    var all = fields();
    Object.keys(all).sort().forEach(function (name) {
      var option = document.createElement('option');
      option.value = name;
      option.textContent = all[name].label +
        (all[name].unit ? ' (' + all[name].unit + ')' : '');
      fieldSelect.appendChild(option);
    });

    function syncOperators() {
      var spec = all[fieldSelect.value] || {};
      var allowed = (spec.kind === 'enum' || spec.kind === 'bool')
        ? ['eq', 'ne']
        : ['eq', 'ne', 'gt', 'gte', 'lt', 'lte'];
      opSelect.innerHTML = '';
      allowed.forEach(function (op) {
        var option = document.createElement('option');
        option.value = op;
        option.textContent = OP_WORDS[op];
        opSelect.appendChild(option);
      });
      /* Offer the closed vocabulary as a datalist rather than free text, so an
       * invalid enum value is hard to type by accident. */
      var existing = document.getElementById('f-value-list');
      if (existing) { existing.remove(); }
      if (spec.enum && spec.enum.length) {
        var list = document.createElement('datalist');
        list.id = 'f-value-list';
        spec.enum.forEach(function (value) {
          var option = document.createElement('option');
          option.value = value;
          list.appendChild(option);
        });
        valueInput.parentNode.appendChild(list);
        valueInput.setAttribute('list', 'f-value-list');
        valueInput.placeholder = spec.enum[0];
      } else {
        valueInput.removeAttribute('list');
        valueInput.placeholder = spec.kind === 'number' ? 'a number' : '';
      }
      valueInput.type = spec.kind === 'number' ? 'number' : 'text';
      if (spec.kind === 'number') { valueInput.step = 'any'; }
    }

    fieldSelect.addEventListener('change', syncOperators);
    syncOperators();

    addButton.addEventListener('click', function () {
      var raw = valueInput.value.trim();
      if (!raw) { valueInput.focus(); return; }
      var spec = all[fieldSelect.value] || {};
      var value = spec.kind === 'number' ? Number(raw) : raw;
      if (spec.kind === 'number' && !isFinite(value)) { valueInput.focus(); return; }
      state.filters.push({ field: fieldSelect.value, op: opSelect.value, value: value });
      valueInput.value = '';
      saveStack();
      renderStack();
      run();
    });

    var copyButton = document.getElementById('stack-copy');
    if (copyButton) {
      copyButton.addEventListener('click', function () {
        var text = stackAsText();
        if (navigator.clipboard) {
          navigator.clipboard.writeText(text).then(function () {
            copyButton.textContent = 'Copied';
            setTimeout(function () { copyButton.textContent = 'Copy'; }, 1500);
          });
        }
      });
    }

    /* Headline figures filter the table. Clicking a card pushes its filter onto
       the stack, clicking it again removes it, so the number above and the rows
       below always describe the same set. Without this the cards state a count
       the table cannot be made to show, which is the obvious thing to try. */
    [].slice.call(document.querySelectorAll('[data-stat-filter]')).forEach(function (card) {
      var spec;
      try { spec = JSON.parse(card.getAttribute('data-stat-filter')); } catch (e) { return; }
      var wanted = [].concat(spec);
      function matches(f) {
        return wanted.some(function (w) {
          return w.field === f.field && w.op === f.op && String(w.value) === String(f.value);
        });
      }
      function sync() {
        var on = wanted.every(function (w) { return state.filters.some(function (f) {
          return w.field === f.field && w.op === f.op && String(w.value) === String(f.value); }); });
        card.setAttribute('aria-pressed', on ? 'true' : 'false');
        return on;
      }
      sync();
      card.addEventListener('click', function () {
        if (sync()) {
          state.filters = state.filters.filter(function (f) { return !matches(f); });
        } else {
          wanted.forEach(function (w) {
            if (!state.filters.some(function (f) { return matches(f); })) { state.filters.push(w); }
          });
        }
        saveStack();
        renderStack();
        run();
        [].slice.call(document.querySelectorAll('[data-stat-filter]')).forEach(function (other) {
          var s2; try { s2 = [].concat(JSON.parse(other.getAttribute('data-stat-filter'))); } catch (e) { return; }
          var on2 = s2.every(function (w) { return state.filters.some(function (f) {
            return w.field === f.field && w.op === f.op && String(w.value) === String(f.value); }); });
          other.setAttribute('aria-pressed', on2 ? 'true' : 'false');
        });
      });
    });

    var clearButton = document.getElementById('stack-clear');
    if (clearButton) {
      clearButton.addEventListener('click', function () {
        state.filters = [];
        saveStack();
        renderStack();
        run();
      });
    }

    var nlButton = document.getElementById('nl-run');
    var nlInput = document.getElementById('nl-input');
    if (nlButton && nlInput) {
      var ask = function () {
        var question = nlInput.value.trim();
        if (!question) { return; }
        var note = document.getElementById('nl-note');
        if (note) { note.textContent = 'Asking BINMAN-LM…'; }
        Util.post('/api/nl', { question: question }).then(function (result) {
          if (!result.ok) {
            if (note) {
              note.textContent = (result.data && result.data.error) ||
                'The model could not answer. Build the query below instead.';
            }
            return;
          }
          var query = result.data.query || {};
          state.filters = (query.filters || []).filter(function (f) {
            return !!fields()[f.field];
          });
          if (query.sort) {
            state.sortField = query.sort.field;
            state.sortDirection = query.sort.direction;
          }
          saveStack();
          renderStack();
          run();
          if (note) {
            note.textContent = 'Proposed by BINMAN-LM, validated by the parser. ' +
              'Every number shown is computed in Python.';
          }
        });
      };
      nlButton.addEventListener('click', ask);
      nlInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') { event.preventDefault(); ask(); }
      });
    }
  }

  /* ---------------------------------------------------------------- table --- */

  /* Columns that are displayed but not filterable, so they carry no FieldSpec.
   * Without this they would render with their raw database name as the title. */
  var DISPLAY_LABELS = {
    chain_a: 'Chain A', chain_b: 'Chain B', ligand_name: 'Ligand name',
    structure_file: 'Structure', title: 'Title', id: 'ID'
  };

  function columnDefinitions() {
    var all = fields();
    var columns = (B.defaultColumns || []).map(function (name) {
      var spec = all[name] || { label: DISPLAY_LABELS[name] || name, kind: 'text' };
      var definition = {
        title: spec.label + (spec.unit ? ' (' + spec.unit + ')' : ''),
        field: name,
        headerTooltip: spec.description || spec.label,
        resizable: true
      };
      if (spec.kind === 'number') {
        definition.hozAlign = 'right';
        definition.formatter = function (cell) { return Util.num(cell.getValue()); };
      } else if (spec.kind === 'bool') {
        definition.hozAlign = 'center';
        definition.formatter = function (cell) {
          return cell.getValue() ? Util.pill('yes', 'good') : Util.pill('no');
        };
      } else if (name === 'ccd_class') {
        definition.formatter = function (cell) {
          var value = cell.getValue();
          var tone = value === 'glue_candidate' ? 'glue'
            : (['cryoprotectant', 'buffer', 'detergent', 'metal', 'sugar'].indexOf(value) > -1
              ? 'warn' : '');
          return Util.pill(value || 'unknown', tone);
        };
      } else if (name === 'verdict') {
        definition.formatter = function (cell) {
          var value = cell.getValue();
          var tone = value === 'favourable' ? 'good'
            : value === 'marginal' ? 'warn'
            : value === 'unfavourable' ? 'bad' : '';
          return Util.pill(value || 'not scored', tone);
        };
      } else if (name === 'pdb_id') {
        definition.formatter = function (cell) {
          var value = cell.getValue();
          if (!value) { return ''; }
          return '<a href="https://www.rcsb.org/structure/' + Util.escape(value) +
            '" target="_blank" rel="noopener noreferrer">' + Util.escape(value) + '</a>';
        };
      }
      return definition;
    });
    /* chain_a and chain_b are already in the bridge record type's default
     * columns, so they are not spliced in again: doing so rendered each twice. */
    return columns;
  }

  function initTable() {
    var holder = document.getElementById('ledger-table');
    if (!holder || typeof global.Tabulator === 'undefined') { return; }
    state.table = new global.Tabulator(holder, {
      height: '560px',
      layout: 'fitDataStretch',
      placeholder: B.atlasAvailable
        ? 'No rows match this query stack.'
        : 'The atlas has not been built yet.',
      columns: columnDefinitions(),
      selectableRows: 1,
      index: 'id'
    });
    /* Tabulator 6.3.1 emits role="rowgroup" on both .tabulator-header and the
     * .tabulator-header-contents nested inside it, which makes the grid invalid:
     * a rowgroup cannot contain a rowgroup, and the columnheader cells then have
     * no row parent. axe-core reports both as critical. The library controls this
     * markup, so the roles are corrected once the table has built. */
    state.table.on('tableBuilt', function () {
      var holder = document.getElementById('ledger-table');
      if (!holder) { return; }
      var contents = holder.querySelector('.tabulator-header-contents');
      if (contents) { contents.setAttribute('role', 'row'); }
      var headers = holder.querySelector('.tabulator-headers');
      if (headers) { headers.setAttribute('role', 'presentation'); }
      // The scrollable tableholder is a focusable div sitting directly inside
      // role="grid", which is not an allowed child. role="presentation" is
      // ignored on a focusable element, so the holder becomes the row group and
      // the table inside it becomes presentational, which leaves the structure
      // grid > rowgroup > row > gridcell as ARIA requires.
      var tableholder = holder.querySelector('.tabulator-tableholder');
      if (tableholder) {
        tableholder.setAttribute('role', 'rowgroup');
        tableholder.setAttribute('aria-label', 'Table rows');
      }
      var innerTable = holder.querySelector('.tabulator-table');
      if (innerTable) { innerTable.setAttribute('role', 'presentation'); }
      // Tabulator renders header filters as bare inputs with no label.
      holder.querySelectorAll('.tabulator-header-filter input').forEach(function (input) {
        if (input.getAttribute('aria-label')) { return; }
        var column = input.closest('.tabulator-col');
        var title = column ? column.querySelector('.tabulator-col-title') : null;
        var name = title ? title.textContent.trim() : 'column';
        input.setAttribute('aria-label', 'Filter by ' + name);
        input.setAttribute('title', 'Filter by ' + name);
      });
    });
    state.table.on('rowClick', function (event, row) {
      var data = row.getData();
      /* Kept so the viewer can frame this row's own feature. The shared
       * selection deliberately carries only identifiers, and widening it
       * would change the URL fragment contract. */
      state.pinnedRow = data;
      Selection.fromRecord(state.recordType, data);
      renderDetail(data);
    });
  }

  function renderDetail(row) {
    var holder = document.getElementById(
      state.recordType === 'bridge' ? 'bridge-detail' :
      state.recordType === 'ligase' ? 'ligase-detail' : 'no-detail'
    );
    if (!holder) { return; }
    var body = holder.querySelector('tbody');
    if (!body) { return; }
    body.innerHTML = '';
    var all = fields();
    Object.keys(row).forEach(function (key) {
      if (row[key] === null || row[key] === undefined || row[key] === '') { return; }
      if (key === 'id' || key === 'status') { return; }
      var spec = all[key];
      var value = row[key];
      if (Array.isArray(value)) { value = value.join(', '); }
      var tr = document.createElement('tr');
      var th = document.createElement('td');
      th.textContent = (spec && spec.label) || DISPLAY_LABELS[key] || key;
      var td = document.createElement('td');
      td.className = 'num';
      td.textContent = spec && spec.kind === 'number' ? Util.num(value) : String(value);
      tr.appendChild(th); tr.appendChild(td);
      body.appendChild(tr);
    });
    holder.hidden = false;
  }

  /* ------------------------------------------------------------------ run --- */

  function queryObject() {
    return {
      record_type: state.recordType,
      filters: state.filters,
      sort: { field: state.sortField, direction: state.sortDirection },
      limit: 1000
    };
  }

  /* Columns the viewer needs that are not columns the table shows.
   *
   * `default_columns` is the schema's contract for what is *displayed*, and
   * the query returns exactly that set unless asked otherwise. The resolvers
   * below read `structure_file` and `best_structure`, neither of which is in
   * any default set, so both arrived undefined: every bridge viewer silently
   * fell back to fetching the entry from RCSB rather than serving the trimmed
   * file, which is why 3,839 local structures were never read, and the E3
   * viewer got `url: null` and `pdbId: null` together and could never load
   * anything at all.
   *
   * Requested here rather than added to `default_columns`, because that set is
   * also what /api/schema publishes and what the table renders from.
   */
  var VIEWER_COLUMNS = {
    bridge: ['structure_file'],
    ligase: ['structure_file', 'best_structure'],
    degron: ['structure_file'],
    /* The lysine table has no structure_file: that viewer builds an AlphaFold
     * URL from the accession, so asking for one is a SQL error. */
    lysine: []
  };

  function queryColumns() {
    var spec = state.schema[state.recordType] || {};
    var base = (spec.default_columns || []).slice();
    (VIEWER_COLUMNS[state.recordType] || []).forEach(function (name) {
      if (base.indexOf(name) === -1) { base.push(name); }
    });
    return base.length ? base : null;
  }

  var runToken = 0;

  function run() {
    if (!B.atlasAvailable) { return Promise.resolve(); }
    var token = ++runToken;
    var started = performance.now();
    return Util.post('/api/query', {
      query: queryObject(), columns: queryColumns()
    }).then(function (result) {
      if (token !== runToken) { return; }
      var countEl = document.getElementById('result-count');
      if (!result.ok) {
        if (countEl) {
          countEl.textContent = (result.data && result.data.error) || 'query failed';
        }
        return;
      }
      state.lastRows = result.data.rows || [];
      if (state.table) { state.table.replaceData(state.lastRows); }
      /* Re-apply the selection now that the rows are here.
       *
       * Selection.subscribe fires immediately, so a viewer restored from a URL
       * fragment resolves its spec before this query has returned, and the
       * residue window it needs to frame a hairpin comes from a row it cannot
       * see yet. The viewer's load() short-circuits on an unchanged spec, so
       * this reloads nothing unless the frame has actually become available.
       */
      if (state.viewer && state.resolveSpec) {
        B.applySelection(state.viewer, Selection.get(), state.resolveSpec);
      }
      var elapsed = Math.round(performance.now() - started);
      if (countEl) {
        countEl.textContent = Util.num(result.data.total) + ' rows match, showing ' +
          Util.num(result.data.returned) + ' · ' + elapsed + ' ms';
      }
      var total = document.getElementById('stack-total');
      if (total) { total.textContent = Util.num(result.data.total) + ' rows'; }
    });
  }

  /* --------------------------------------------------------------- viewer --- */

  /* How far either side of the feature to frame, in residues. A hairpin is two
   * short strands and a turn, so the tip plus six covers it; a lysine needs
   * only enough neighbours to sit in context rather than fill the frame. */
  var HAIRPIN_PAD = 6;
  var LYSINE_PAD = 4;

  /* The row the user actually clicked, when it is the one the selection names.
   *
   * The shared selection carries an accession, and a protein can hold many
   * degron candidates, so the accession alone cannot say which row is pinned.
   * The clicked row is stashed on click and used when it matches. Arriving by
   * URL fragment leaves nothing stashed, so it falls back to the first
   * matching row, which under the default sort is that protein's top-scoring
   * candidate: a defensible frame rather than a wrong one.
   */
  function pinnedRowFor(field, value) {
    if (state.pinnedRow && state.pinnedRow[field] === value) {
      return state.pinnedRow;
    }
    return state.lastRows.filter(function (row) {
      return row[field] === value;
    })[0] || null;
  }

  function resolverFor(recordType) {
    return function (selection) {
      if (recordType === 'bridge') {
        if (!selection.glue) { return null; }
        var parts = selection.glue.split(':');
        var pdbId = parts[0];
        var ccdId = parts[1] || '';
        var rowId = parts[2] || '';
        var row = state.lastRows.filter(function (r) {
          return String(r.id) === String(rowId);
        })[0];
        var overlay = row
          ? 'ΔSASA ' + Util.num(row.dsasa_a) + ' / ' + Util.num(row.dsasa_b) + ' Å²' +
            ' · balance ' + Util.num(row.bridging_balance) +
            ' · buried ' + Util.num(row.buried_fraction)
          : null;
        return {
          role: 'glue',
          url: row && row.structure_file
            ? '/api/structures/' + row.structure_file
            : null,
          pdbId: (row && row.structure_file) ? null : pdbId,
          /* The viewer frames this ligand specifically. A trimmed entry keeps
           * whatever else sat near the interface, so without the CCD the
           * camera would split the difference between the bridge and a
           * neighbouring zinc. */
          ccdId: (row && row.ccd_id) || ccdId,
          identifier: pdbId + ' · ' + ccdId,
          identifierHref: 'https://www.rcsb.org/structure/' + pdbId,
          overlay: overlay
        };
      }
      if (recordType === 'degron') {
        if (!selection.target) { return null; }
        var hairpin = pinnedRowFor('uniprot_acc', selection.target);
        return {
          role: 'degron',
          url: B.afdbCifUrl(selection.target),
          format: 'mmcif',
          /* No ligand on an AlphaFold monomer, so the viewer frames the
           * hairpin instead. HAIRPIN_PAD either side of the tip covers the
           * two strands and the turn, which is what the row describes. */
          focusResidues: (hairpin && hairpin.tip_res)
            ? [{ start: hairpin.tip_res - HAIRPIN_PAD,
                 end: hairpin.tip_res + HAIRPIN_PAD }]
            : null,
          identifier: 'AF-' + selection.target,
          identifierHref: 'https://alphafold.ebi.ac.uk/entry/' + selection.target,
          plddt: true
        };
      }
      if (recordType === 'ligase') {
        if (!selection.e3) { return null; }
        var ligase = state.lastRows.filter(function (r) {
          return r.uniprot_acc === selection.e3;
        })[0];
        var best = ligase && ligase.best_structure;
        return {
          role: 'e3',
          url: ligase && ligase.structure_file ? '/api/structures/' + ligase.structure_file : null,
          pdbId: (!ligase || !ligase.structure_file) && best && best.length === 4 ? best : null,
          identifier: (ligase && ligase.gene) || selection.e3,
          identifierHref: 'https://www.uniprot.org/uniprotkb/' + selection.e3,
          overlay: ligase && ligase.pocket_score !== null && ligase.pocket_score !== undefined
            ? 'pocket score ' + Util.num(ligase.pocket_score) +
              ' · volume ' + Util.num(ligase.pocket_volume_a3) + ' Å³'
            : null
        };
      }
      if (recordType === 'lysine') {
        if (!selection.target) { return null; }
        var lysine = pinnedRowFor('uniprot_acc', selection.target);
        return {
          role: 'degradability',
          url: B.afdbCifUrl(selection.target),
          format: 'mmcif',
          /* The lysine itself, with a little context either side so it is not
           * a single residue filling the frame. */
          focusResidues: (lysine && lysine.res_num)
            ? [{ start: lysine.res_num - LYSINE_PAD,
                 end: lysine.res_num + LYSINE_PAD }]
            : null,
          identifier: selection.target + (selection.site ? ' · ' + selection.site : ''),
          identifierHref: 'https://www.uniprot.org/uniprotkb/' + selection.target
        };
      }
      return null;
    };
  }

  function initViewer() {
    var ids = {
      bridge: 'viewer-glue', degron: 'viewer-degron',
      ligase: 'viewer-e3', lysine: 'viewer-degradability'
    };
    var element = document.getElementById(ids[state.recordType]);
    if (!element) { return; }
    state.viewer = B.mountViewer(element, { role: state.recordType });
    state.resolveSpec = resolverFor(state.recordType);
    Selection.subscribe(function () {
      B.applySelection(state.viewer, Selection.get(), state.resolveSpec);
    });
  }

  function initCompare() {
    var toggle = document.getElementById('compare-toggle');
    var panel = document.getElementById('compare-panel');
    if (!toggle || !panel) { return; }
    var a = null;
    var b = null;
    toggle.addEventListener('click', function () {
      panel.hidden = !panel.hidden;
      toggle.textContent = panel.hidden ? 'Compare two ternaries' : 'Hide comparison';
      if (!panel.hidden && !a) {
        a = B.mountViewer(document.getElementById('viewer-compare-a'), { role: 'compare-a' });
        b = B.mountViewer(document.getElementById('viewer-compare-b'), { role: 'compare-b' });
        var link = document.getElementById('link-cameras');
        if (link) {
          link.addEventListener('click', function () {
            if (a && b) { a.linkTo(b); link.textContent = 'Cameras linked'; }
          });
        }
      }
    });
  }

  function init() {
    if (!state.recordType) { return; }
    loadStack();
    initBuilder();
    renderStack();
    initTable();
    initViewer();
    initCompare();
    run();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}(window));
