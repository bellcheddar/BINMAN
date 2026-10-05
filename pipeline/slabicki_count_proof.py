"""Proof that the Slabicki screen can be recounted from SRA, and where it stops.

NOT a finished stage. It is the evidence behind D-084, kept so the next attempt
starts from what was measured rather than from the same three dead ends.

**What works.** Reads match the library by k-mer: 8,069 of the 9,097 constructs
appear in a 38 MB slice of one run, forward orientation only, and 94.8% of
reads in that slice are assigned to a construct. The demultiplexing key is in
each run's BioSample description, which lists the stagger sequences in order
beside the sample names.

**Where it stops.** Cilantro and Lavender carry *identical* insert DNA for all
9,097 constructs, and a run multiplexes both libraries reusing the same
staggers. So stagger plus insert cannot say which library a read came from, and
six of the fourteen samples in a run are ambiguous. The synthesis primers do
differ between libraries but appear in 206 of 300,000 reads, and the
amplification primers are identical, so neither separates them.

Three dead ends, so they are not retried: an AgeI anchor (present in 3% of
reads), the upstream context of the insert (15,343 distinct 14-mers, no clean
two-way split), and the library amplification primers.
"""

import xlrd, gzip, collections, sys
S='/private/tmp/claude-501/-Users-dellboy-Documents-Vibe-Coding-BINMAN/02d5f083-d26f-4b61-8c6c-1bb61949dddf/scratchpad'
K = 25

wb = xlrd.open_workbook('data/validation/raw/NIHMS2104733-supplement-4.xls', on_demand=True)
kmer = {}
for sheet, lib in (('ZF.Primary.Cilantro','Cil'), ('ZF.Primary.Lavender','Lav')):
    ann = wb.sheet_by_name(sheet)
    h = {ann.cell_value(0,c): c for c in range(ann.ncols)}
    for r in range(1, ann.nrows):
        name = str(ann.cell_value(r, h['Name']))
        s = str(ann.cell_value(r, h['ZnF.Sequence'])).upper()
        for o in range(0, len(s)-K+1):
            kmer.setdefault(s[o:o+K], (lib, name))
    wb.unload_sheet(sheet)
print('k-mer index: %d entries' % len(kmer))

# SAMN50185851, the key for SRR34701548.
STAG = ['', 'A', 'GA', 'CGA', 'ACGA', 'CTAGAA', 'GACGACA', 'TGGACACA',
        '', 'A', 'GA', 'CGA', 'ACGA', 'CTAGAA']
SAMPLES = ['Cil_ALV1_C_Rep3','Cil_ALV2_G_Rep3','Cil_NH2.4.Ph.Glu.Amide_C_Rep3',
           'Cil_Ace.4.Ph.Glu.Amide_C_Rep3','Cil_Ph.Glu.Amide_C_Rep3',
           'Cil_OCH3.4.Ph.Glu.Amide_C_Rep3','Cil_Br.4.Ph.Glu.Amide_C_Rep3',
           'Cil_DMSO_C_Rep3','Lav_ALV1_C_Rep3','Lav_ALV2_G_Rep3',
           'Lav_Br.4.Ph.Glu.Amide_C_Rep3','Lav_OCH3.4.Glu.Amide_C_Rep3',
           'Lav_Ph.Glu.Amide_C_Rep3','Lav_Ace.4.Ph.Glu.Amide_C_Rep3']
# Longest stagger first so CTAGAA is not read as the empty stagger.
ORDER = sorted(range(len(STAG)), key=lambda i: -len(STAG[i]))

counts = collections.defaultdict(collections.Counter)
seen = matched = 0
try:
  with gzip.open(f'{S}/slice.fastq.gz','rt',errors='replace') as f:
    for i, line in enumerate(f):
        if i % 4 != 1: continue
        r = line.strip(); seen += 1
        hit = None
        for o in range(0, len(r)-K+1):
            v = kmer.get(r[o:o+K])
            if v: hit = v; break
        if not hit: continue
        lib, name = hit
        for j in ORDER:
            st = STAG[j]
            if SAMPLES[j].startswith(lib) and (st == '' or r.startswith(st)):
                counts[SAMPLES[j]][name] += 1
                matched += 1
                break
except EOFError:
    # The slice is a byte range, so the stream ends mid-record. Everything read
    # before that point is complete and is kept.
    pass
print('reads %d, assigned %d (%.1f%%)' % (seen, matched, 100*matched/max(1,seen)))
print()
for s in SAMPLES:
    c = counts[s]
    print('   %-34s %7d reads over %5d constructs' % (s, sum(c.values()), len(c)))
import json, io
io.open(f'{S}/proof_counts.json','w').write(json.dumps(
    {k: dict(v) for k, v in counts.items()}))
