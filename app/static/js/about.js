/* About tab behaviour: the dataset and reference tables, and the BibTeX export.
 * Every value comes from about.json; nothing here invents a number. */
(function (global) {
  'use strict';

  var B = global.BINMAN || {};
  var about = B.about || {};
  var Util = B.Util;

  function yesNo(cell) {
    return cell.getValue() ? Util.pill('yes', 'good') : Util.pill('no', 'warn');
  }

  function initDatasetTable() {
    var holder = document.getElementById('dataset-table');
    if (!holder || typeof global.Tabulator === 'undefined') { return; }
    new global.Tabulator(holder, {
      data: about.datasets || [],
      layout: 'fitColumns',
      height: '340px',
      columns: [
        { title: 'Dataset', field: 'name', widthGrow: 2,
          formatter: function (cell) {
            var row = cell.getRow().getData();
            var name = '<code>' + Util.escape(cell.getValue()) + '</code>';
            return row.homepage
              ? '<a href="' + Util.escape(row.homepage) +
                '" target="_blank" rel="noopener noreferrer">' + name + '</a>'
              : name;
          } },
        { title: 'Resolved', field: 'resolved', hozAlign: 'center', width: 100,
          formatter: yesNo },
        { title: 'Rows', field: 'rows', hozAlign: 'right', width: 110,
          formatter: function (cell) { return Util.num(cell.getValue()); } },
        { title: 'Licence', field: 'licence', widthGrow: 2 },
        { title: 'Redistributable', field: 'redistributable', hozAlign: 'center',
          width: 130, formatter: yesNo },
        { title: 'Release', field: 'version', widthGrow: 2 },
        { title: 'Retrieved', field: 'retrieved', width: 170 },
        { title: 'Used for', field: 'purpose', widthGrow: 3 }
      ]
    });
  }

  function initReferenceTable() {
    var holder = document.getElementById('reference-table');
    if (!holder || typeof global.Tabulator === 'undefined') { return; }
    new global.Tabulator(holder, {
      data: about.references || [],
      layout: 'fitColumns',
      height: '560px',
      columns: [
        { title: 'Name', field: 'name', widthGrow: 3, headerFilter: 'input' },
        { title: 'Type', field: 'type', width: 110, headerFilter: 'list',
          headerFilterParams: { values: true } },
        { title: 'Version', field: 'version', width: 150 },
        { title: 'Retrieved', field: 'retrieved', width: 160 },
        { title: 'Used for', field: 'used_for', widthGrow: 3 },
        { title: 'Licence', field: 'licence', widthGrow: 2, headerFilter: 'input',
          formatter: function (cell) {
            var value = cell.getValue();
            return (!value || value === 'not determined')
              ? Util.pill('not determined', 'warn')
              : Util.escape(value);
          } },
        { title: 'DOI', field: 'doi', widthGrow: 2,
          formatter: function (cell) {
            var row = cell.getRow().getData();
            var doi = cell.getValue();
            if (doi) {
              return '<a href="https://doi.org/' + Util.escape(doi) +
                '" target="_blank" rel="noopener noreferrer">' + Util.escape(doi) + '</a>';
            }
            /* No DOI: show the canonical URL and say so (spec 6.6.3). */
            if (row.home) {
              return '<a href="' + Util.escape(row.home) +
                '" target="_blank" rel="noopener noreferrer">URL, no DOI</a>';
            }
            return Util.pill('no DOI or URL', 'bad');
          } },
        { title: 'Verified', field: 'verified', hozAlign: 'center', width: 110,
          formatter: function (cell) {
            return cell.getValue()
              ? Util.pill('verified', 'good')
              : Util.pill('unverified', 'warn');
          },
          tooltip: function (event, cell) {
            return cell.getRow().getData().verification || '';
          } },
        { title: 'Repository', field: 'repo', widthGrow: 2,
          formatter: function (cell) {
            var value = cell.getValue();
            if (!value) { return ''; }
            return '<a href="' + Util.escape(value) +
              '" target="_blank" rel="noopener noreferrer">repo</a>';
          } }
      ]
    });
  }

  function initBibtex() {
    var button = document.getElementById('bibtex-export');
    if (!button) { return; }
    button.addEventListener('click', function () {
      /* Rebuild BibTeX from the same records the table shows, so the export and
       * the page can never disagree. */
      var lines = [
        '% BINMAN reference export, generated in the browser from about.json.',
        '% Cite BINMAN for the atlas and every resource below separately.',
        ''
      ];
      (about.references || []).forEach(function (record) {
        var type = record.type === 'software' ? 'software'
          : (record.type === 'paper' || record.type === 'database') ? 'article' : 'misc';
        var body = ['@' + type + '{' + (record.key || 'unknown') + ','];
        var add = function (name, val) {
          if (val) { body.push('  ' + name + ' = {' + String(val).replace(/[{}]/g, '') + '},'); }
        };
        add('title', record.name);
        add('author', record.authors);
        add('year', record.year);
        add('journal', record.container);
        add('doi', record.doi);
        add('url', record.home);
        add('version', record.version);
        add('license', record.licence);
        add('note', record.verification);
        body[body.length - 1] = body[body.length - 1].replace(/,$/, '');
        body.push('}');
        lines.push(body.join('\n'));
        lines.push('');
      });
      var blob = new Blob([lines.join('\n')], { type: 'text/plain' });
      var url = URL.createObjectURL(blob);
      var anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'binman-references.bib';
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    });
  }

  function initExampleViewers() {
    var example = about.worked_example || {};
    if (!example.available) { return; }
    var first = document.getElementById('viewer-example-1');
    if (first) {
      B.mountViewer(first, {
        role: 'glue',
        pdbId: example.pdb_id,
        identifier: example.pdb_id + ' · ' + example.ccd_id,
        identifierHref: 'https://www.rcsb.org/structure/' + example.pdb_id,
        overlay: 'ΔSASA ' + Util.num(example.dsasa_a) + ' / ' +
          Util.num(example.dsasa_b) + ' Å² · balance ' +
          Util.num(example.bridging_balance)
      });
    }
  }

  function init() {
    if (!about || !about.generated_at) { return; }
    initDatasetTable();
    initReferenceTable();
    initBibtex();
    initExampleViewers();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}(window));
