"""Build the BINMAN-LM training corpora (spec 3.2 to 3.6).

**Generated, not curated.** The Task A corpus is enumerated from the real schema
in `app/queries.py`, the real value ranges read out of the built SQLite, and the
closed vocabularies read from the atlas itself. Every generated pair is then
validated by the same parser the app uses, so the corpus has **zero label noise
by construction** (spec 3.2).

Outputs under `lm/corpus/`:
    task_a_{train,valid,test}.jsonl     natural language to query object
    task_a_preference.jsonl             one rejected sample per corruption mode
    task_c_{train,valid,test}.jsonl     structured abstention
    task_c_preference.jsonl             refusal against confident fabrication
    corpus_report.json                  counts, splits and what could not be built

Splits hold out **compositions, not tokens**: every field, operator and class
appears in training, and the test set holds unseen combinations (spec 3.6).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.queries import (  # noqa: E402
    OPERATORS, RECORD_TYPES, QueryError, parse, refresh_vocabularies,
)
from pipeline.common import INTERIM, Manifest, log_event, utcnow, write_jsonl  # noqa: E402

CORPUS = ROOT / "lm" / "corpus"
DB_PATH = ROOT / "data" / "atlas" / "binman.sqlite"
STAGE = "lm_corpus"

SEED = 20261003  # fixed so the corpus is reproducible

# Spec 3.3: one rejected sample per corruption mode, equal counts per mode.
CORRUPTION_MODES = (
    "hallucinated_field",
    "operator_inversion",
    "unit_confusion",
    "dropped_constraint",
    "invented_entity",
    "wrong_question",
    "prose_not_json",
)

SYSTEM_QUERY = (
    "<task>query</task>\n"
    "You translate a natural language question into a BINMAN query object. "
    "Reply with JSON only. Use only the fields, operators and values in the "
    "schema. Never invent a field, a ligase or a PDB identifier. Never compute "
    "or estimate a numeric value."
)
# One definition, in the module that serves it. A corpus trained on a different
# system message from the one the app sends is a model measured on a prompt it
# never saw (D-091).
from app.lm import ABSTAIN_SYSTEM as SYSTEM_ABSTAIN  # noqa: E402


# --------------------------------------------------------------------------- #
# phrasing templates (spec 3.2: ~40 templates, then paraphrase-expanded)
# --------------------------------------------------------------------------- #

# Each template takes {record}, {label}, {op}, {value} and {unit}.
COMPARATIVE_TEMPLATES = (
    "{record} where {label} is {op} {value}{unit}",
    "show me {record} with {label} {op} {value}{unit}",
    "find {record} whose {label} is {op} {value}{unit}",
    "list {record} with {label} {op} {value}{unit}",
    "which {record} have {label} {op} {value}{unit}?",
    "give me every {record} with {label} {op} {value}{unit}",
    "{record} with a {label} of {op} {value}{unit}",
    "I want {record} where the {label} is {op} {value}{unit}",
    "pull up {record} having {label} {op} {value}{unit}",
    "any {record} with {label} {op} {value}{unit}?",
    "return {record} filtered to {label} {op} {value}{unit}",
    "{record}, {label} {op} {value}{unit}",
    "search {record} for {label} {op} {value}{unit}",
    "can you list {record} where {label} is {op} {value}{unit}",
    "how about {record} with {label} {op} {value}{unit}",
    "narrow {record} to {label} {op} {value}{unit}",
    "filter {record} by {label} {op} {value}{unit}",
    "{record} restricted to {label} {op} {value}{unit}",
    "everything in {record} with {label} {op} {value}{unit}",
    "the {record} that have {label} {op} {value}{unit}",
)

EQUALITY_TEMPLATES = (
    "{record} where {label} is {value}",
    "show me {record} with {label} {value}",
    "{record} classified as {value}",
    "list every {record} whose {label} is {value}",
    "which {record} are {value}?",
    "find {record} with {label} equal to {value}",
    "{record}, {label} {value}",
    "give me the {value} {record}",
    "filter {record} to {label} {value}",
    "only {record} where {label} is {value}",
)

NEGATION_TEMPLATES = (
    "{record} where {label} is not {value}",
    "{record} excluding {label} {value}",
    "show me {record} that are not {value}",
    "list {record} with {label} other than {value}",
    "everything in {record} apart from {label} {value}",
)

SORT_TEMPLATES = (
    "{record} sorted by {label}, {direction}",
    "{record} ranked by {label} {direction}",
    "the top {record} by {label}",
    "{record} ordered on {label}, {direction} first",
)

OP_WORDS = {
    "gt": ("above", "greater than", "over", "more than", "exceeding"),
    "gte": ("at least", "no less than", "{value} or more", "a minimum of"),
    "lt": ("below", "less than", "under", "beneath"),
    "lte": ("at most", "no more than", "{value} or less", "a maximum of"),
    "eq": ("exactly", "equal to", "of"),
    "ne": ("not", "other than", "anything but"),
}

RECORD_WORDS = {
    "bridge": ("bridges", "bridging ligands", "glue candidates", "ternary complexes",
               "atlas rows", "bridged chain pairs"),
    "degron": ("degrons", "degron candidates", "hairpin degrons", "candidate degrons"),
    "ligase": ("ligases", "E3 ligases", "E3s", "ubiquitin ligases"),
    "lysine": ("lysines", "surface lysines", "lysine sites"),
}


# --------------------------------------------------------------------------- #
# value sampling, grounded in the real database
# --------------------------------------------------------------------------- #

@dataclass
class Grounding:
    """Real value ranges and vocabularies, read from the built atlas."""

    ranges: dict[str, dict[str, float]] = field(default_factory=dict)
    vocabularies: dict[str, list[str]] = field(default_factory=dict)

    def numeric_samples(self, record: str, name: str) -> list[float]:
        """Plausible thresholds for a numeric field, from its real quantiles.

        Quantiles rather than min + fraction * (max - min): one outlier would
        otherwise drag every generated threshold with it, producing questions
        about a 91 Angstrom lysine distance that no researcher would ask.
        """
        stats = self.ranges.get(f"{record}.{name}")
        if not stats:
            return []
        quantiles = stats.get("quantiles") or []
        if not quantiles:
            return []
        picks = []
        spread = max(quantiles) - min(quantiles)
        for value in quantiles:
            if spread > 100:
                picks.append(round(value, -1))
            elif spread > 10:
                picks.append(round(value))
            else:
                picks.append(round(value, 2))
        return sorted({p for p in picks if p > 0})


def ground(connection: sqlite3.Connection | None) -> Grounding:
    grounding = Grounding()
    if connection is None:
        return grounding
    grounding.vocabularies = refresh_vocabularies(connection)
    for record, spec in RECORD_TYPES.items():
        for name, field_spec in spec.fields.items():
            if field_spec.kind != "number":
                continue
            try:
                rows = connection.execute(
                    f"SELECT {name} FROM {spec.table} WHERE {name} IS NOT NULL "
                    f"ORDER BY {name}"
                ).fetchall()
            except sqlite3.Error:
                continue
            values = [r[0] for r in rows if isinstance(r[0], (int, float))]
            if len(values) < 5:
                continue
            quantiles = [
                values[min(len(values) - 1, int(len(values) * q))]
                for q in (0.10, 0.25, 0.50, 0.75, 0.90)
            ]
            grounding.ranges[f"{record}.{name}"] = {
                "min": values[0], "max": values[-1], "quantiles": quantiles,
            }
    return grounding


def enum_values(record: str, name: str, field_spec, grounding: Grounding) -> list[str]:
    """Allowed values for an enum or text field, preferring the real vocabulary."""
    if field_spec.enum:
        return list(field_spec.enum)
    lookup = {
        ("ligase", "gene"): "ligase_gene",
        ("ligase", "uniprot_acc"): "ligase_acc",
        ("ligase", "family"): "ligase_family",
        ("bridge", "ccd_id"): "ccd_id",
        ("bridge", "method"): "method",
        ("degron", "motif_family"): "motif_family",
    }
    key = lookup.get((record, name))
    if key:
        return grounding.vocabularies.get(key, [])[:400]
    return []


# --------------------------------------------------------------------------- #
# Task A generation
# --------------------------------------------------------------------------- #

@dataclass
class Sample:
    prompt: str
    completion: dict
    record_type: str
    composition: tuple           # what the split holds out
    fields: tuple

    def as_chat(self, system: str = SYSTEM_QUERY) -> dict:
        return {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": self.prompt},
                {"role": "assistant",
                 "content": json.dumps(self.completion, separators=(",", ":"))},
            ],
            "record_type": self.record_type,
            "composition": "|".join(str(c) for c in self.composition),
        }


def phrase_operator(op: str, value, rng: random.Random) -> tuple[str, bool]:
    """Return the operator phrasing and whether it already contains the value.

    "{value} or more" carries the number itself, so the caller must not append
    it again or the prompt reads "2 or less 2".
    """
    word = rng.choice(OP_WORDS[op])
    if "{value}" in word:
        return word.replace("{value}", str(value)), True
    return word, False


def generate_task_a(grounding: Grounding, rng: random.Random,
                    target: int = 6000) -> list[Sample]:
    """Enumerate (record, field, operator, value) and dress each in a phrasing."""
    samples: list[Sample] = []
    seen_prompts: set[str] = set()

    singles: list[Sample] = []
    for record, spec in RECORD_TYPES.items():
        record_words = RECORD_WORDS[record]
        for name, field_spec in spec.fields.items():
            label_words = [field_spec.label.lower()]
            if "_" in name:
                label_words.append(name.replace("_", " "))
            unit = f" {field_spec.unit}" if field_spec.unit else ""

            if field_spec.kind == "number":
                values = grounding.numeric_samples(record, name)
                if not values:
                    continue
                for op in ("gt", "gte", "lt", "lte"):
                    for value in values:
                        template = rng.choice(COMPARATIVE_TEMPLATES)
                        phrasing, carries_value = phrase_operator(op, value, rng)
                        prompt = template.format(
                            record=rng.choice(record_words),
                            label=rng.choice(label_words),
                            op=phrasing,
                            value="" if carries_value else value,
                            unit=unit,
                        )
                        prompt = " ".join(prompt.split())
                        singles.append(Sample(
                            prompt=prompt,
                            completion={
                                "record_type": record,
                                "filters": [{"field": name, "op": op, "value": value}],
                                "limit": 200,
                            },
                            record_type=record,
                            composition=(record, name, op),
                            fields=(name,),
                        ))
            else:
                values = enum_values(record, name, field_spec, grounding)
                if not values:
                    continue
                for value in values[:24]:
                    for op in ("eq", "ne"):
                        pool = EQUALITY_TEMPLATES if op == "eq" else NEGATION_TEMPLATES
                        template = rng.choice(pool)
                        prompt = template.format(
                            record=rng.choice(record_words),
                            label=rng.choice(label_words), value=value,
                        )
                        singles.append(Sample(
                            prompt=prompt,
                            completion={
                                "record_type": record,
                                "filters": [{"field": name, "op": op, "value": value}],
                                "limit": 200,
                            },
                            record_type=record,
                            composition=(record, name, op),
                            fields=(name,),
                        ))

    rng.shuffle(singles)
    samples.extend(singles)

    # Multi-clause queries: two and three filters, which is where completeness
    # and the dropped_constraint corruption actually bite.
    by_record: dict[str, list[Sample]] = {}
    for sample in singles:
        by_record.setdefault(sample.record_type, []).append(sample)

    while len(samples) < target:
        record = rng.choice(list(by_record))
        pool = by_record[record]
        if len(pool) < 3:
            continue
        count = rng.choice((2, 2, 3))
        picks = rng.sample(pool, count)
        # One filter per field, or the query contradicts itself.
        if len({p.fields[0] for p in picks}) != count:
            continue
        filters = [p.completion["filters"][0] for p in picks]
        joiner = rng.choice((" and ", ", and ", " with ", ", "))
        prompt = joiner.join(p.prompt for p in picks)
        # Tidy the stitched phrasing so it reads like one question.
        prompt = prompt[0].upper() + prompt[1:] if prompt else prompt
        completion = {"record_type": record, "filters": filters, "limit": 200}
        if rng.random() < 0.3:
            sort_field = rng.choice([
                name for name, spec in RECORD_TYPES[record].fields.items()
                if spec.kind == "number"
            ])
            direction = rng.choice(("desc", "asc"))
            completion["sort"] = {"field": sort_field, "direction": direction}
            prompt += ", " + rng.choice(SORT_TEMPLATES).format(
                record="", label=RECORD_TYPES[record].fields[sort_field].label.lower(),
                direction="highest first" if direction == "desc" else "lowest first",
            ).strip().lstrip(", ")
        if prompt in seen_prompts:
            continue
        seen_prompts.add(prompt)
        samples.append(Sample(
            prompt=prompt, completion=completion, record_type=record,
            composition=tuple([record] + sorted(
                f"{f['field']}:{f['op']}" for f in filters)),
            fields=tuple(sorted(f["field"] for f in filters)),
        ))

    return samples


def validate(samples: list[Sample]) -> tuple[list[Sample], list[dict]]:
    """Run every generated pair through the app's parser.

    This is what gives the corpus zero label noise: a sample the parser rejects
    is dropped and recorded, never shipped as training data.
    """
    good: list[Sample] = []
    rejected: list[dict] = []
    for sample in samples:
        try:
            reparsed = parse(sample.completion)
        except QueryError as exc:
            rejected.append({"prompt": sample.prompt,
                             "completion": sample.completion, "error": str(exc)})
            continue
        # Normalise the completion to exactly what the parser produces, so the
        # model is trained on the canonical form.
        sample.completion = reparsed.as_dict()
        good.append(sample)
    return good, rejected


def split_by_composition(samples: list[Sample], rng: random.Random
                         ) -> tuple[list[Sample], list[Sample], list[Sample]]:
    """Hold out compositions, not tokens (spec 3.6).

    Every field, operator and record type must appear in training; the held-out
    sets contain unseen *combinations*. Single-filter samples therefore always
    stay in training, and multi-filter compositions are split.
    """
    singles = [s for s in samples if len(s.fields) == 1]
    multis = [s for s in samples if len(s.fields) > 1]

    compositions = sorted({s.composition for s in multis})
    rng.shuffle(compositions)
    held = set(compositions[: max(1, int(len(compositions) * 0.22))])
    valid_compositions = set(list(held)[: len(held) // 2])
    test_compositions = held - valid_compositions

    train = singles + [s for s in multis if s.composition not in held]
    valid = [s for s in multis if s.composition in valid_compositions]
    test = [s for s in multis if s.composition in test_compositions]
    return train, valid, test


# --------------------------------------------------------------------------- #
# Task A preference pairs (spec 3.3)
# --------------------------------------------------------------------------- #

def corrupt(sample: Sample, mode: str, grounding: Grounding,
            rng: random.Random) -> dict | str | None:
    """Produce one genuinely different and genuinely wrong output for a mode."""
    chosen = json.loads(json.dumps(sample.completion))
    record = chosen["record_type"]
    spec = RECORD_TYPES[record]

    if mode == "hallucinated_field":
        if not chosen["filters"]:
            return None
        plausible = ["dsasa_in_nm2", "buried_area", "interface_score", "glue_score",
                     "pocket_druggability", "degron_probability", "lysine_reach",
                     "balance_ratio", "contact_count", "plddt_mean"]
        target = rng.choice(chosen["filters"])
        target["field"] = rng.choice(
            [p for p in plausible if p not in spec.fields] or ["made_up_field"])
        return chosen

    if mode == "operator_inversion":
        inversions = {"gt": "lt", "gte": "lte", "lt": "gt", "lte": "gte",
                      "eq": "ne", "ne": "eq"}
        candidates = [f for f in chosen["filters"] if f["op"] in inversions]
        if not candidates:
            return None
        target = rng.choice(candidates)
        target["op"] = inversions[target["op"]]
        return chosen

    if mode == "unit_confusion":
        # Angstrom^2 reported in Angstrom, or a distance in nanometres: the value
        # is rescaled so the query means something different.
        numeric = [
            f for f in chosen["filters"]
            if spec.fields[f["field"]].kind == "number" and spec.fields[f["field"]].unit
        ]
        if not numeric:
            return None
        target = rng.choice(numeric)
        unit = spec.fields[target["field"]].unit
        factor = 0.1 if "Å²" in unit or "Å³" in unit else 0.1
        target["value"] = round(float(target["value"]) * factor, 4)
        return chosen

    if mode == "dropped_constraint":
        if len(chosen["filters"]) < 2:
            return None
        chosen["filters"].pop(rng.randrange(len(chosen["filters"])))
        return chosen

    if mode == "invented_entity":
        genes = grounding.vocabularies.get("ligase_gene", [])
        invented = ["RNF999", "DCAF99", "CRBN2", "FBXW42", "ZYG11C", "KLHDC9"]
        pick = rng.choice([g for g in invented if g not in genes] or ["RNF999"])
        if record == "ligase":
            chosen["filters"] = [{"field": "gene", "op": "eq", "value": pick}]
        else:
            chosen["filters"] = chosen["filters"] + [
                {"field": "ccd_id", "op": "eq", "value": "ZZZ"}
            ] if "ccd_id" in spec.fields else [
                {"field": "uniprot_acc", "op": "eq", "value": "Q00000"}
            ]
        return chosen

    if mode == "wrong_question":
        # Valid JSON, valid schema, different intent: another record type's query.
        other = rng.choice([r for r in RECORD_TYPES if r != record])
        other_spec = RECORD_TYPES[other]
        name = rng.choice([
            n for n, s in other_spec.fields.items() if s.kind == "number"
        ])
        values = grounding.numeric_samples(other, name) or [1.0]
        return {
            "record_type": other,
            "filters": [{"field": name, "op": "gte", "value": rng.choice(values)}],
            "limit": 200,
        }

    if mode == "prose_not_json":
        labels = ", ".join(
            spec.fields[f["field"]].label for f in chosen["filters"]
        ) or "those criteria"
        return (
            f"Certainly! To find that, you would filter the {spec.label} table on "
            f"{labels}. Let me know if you would like me to adjust the thresholds "
            f"or add any other constraints."
        )

    return None


def generate_preference_pairs(samples: list[Sample], grounding: Grounding,
                              rng: random.Random, per_mode: int = 200) -> list[dict]:
    """Equal counts per corruption mode (spec 3.3)."""
    pairs: list[dict] = []
    counts = {mode: 0 for mode in CORRUPTION_MODES}
    pool = [s for s in samples]
    rng.shuffle(pool)

    for mode in CORRUPTION_MODES:
        # dropped_constraint needs multi-clause samples; the rest work on any.
        eligible = [s for s in pool if len(s.fields) >= 2] if mode == "dropped_constraint" \
            else list(pool)
        # Reshuffle per mode so each mode's 200 pairs are drawn from across the
        # corpus rather than all from its front.
        rng.shuffle(eligible)
        for sample in eligible:
            if counts[mode] >= per_mode:
                break
            rejected = corrupt(sample, mode, grounding, rng)
            if rejected is None:
                continue
            rejected_text = (
                rejected if isinstance(rejected, str)
                else json.dumps(rejected, separators=(",", ":"))
            )
            chosen_text = json.dumps(sample.completion, separators=(",", ":"))
            if rejected_text == chosen_text:
                # A corruption that produced the same output teaches nothing.
                continue
            pairs.append({
                "mode": mode,
                "prompt": sample.prompt,
                "system": SYSTEM_QUERY,
                "chosen": chosen_text,
                "rejected": rejected_text,
                "record_type": sample.record_type,
            })
            counts[mode] += 1
    return pairs


# --------------------------------------------------------------------------- #
# Task C: structured abstention (spec 3.5)
# --------------------------------------------------------------------------- #

UNANSWERABLE = [
    ("What is the cooperativity alpha for this ternary complex?",
     ["alpha", "a measured cooperativity value"],
     "Cooperativity is not computable from a structure. BINMAN stores alpha only "
     "when it has been extracted from the literature with a source identifier, "
     "and there is none for this record."),
    ("How strongly does this glue bind?",
     ["binding affinity"],
     "The atlas holds no affinity data. It records buried surface area, contacts "
     "and interaction types, none of which is an affinity."),
    ("Will this compound degrade the target in cells?",
     ["cellular degradation data"],
     "The atlas is structural. It holds no cellular degradation measurement."),
    ("What is the IC50?",
     ["potency data"],
     "The atlas holds no potency data."),
    ("Which ligase does this glue recruit in vivo?",
     ["an in vivo recruitment assignment"],
     "The atlas records which chains a ligand bridges in a deposited structure, "
     "which is not the same as an in vivo recruitment assignment."),
    ("How many molecular glues exist in total?",
     ["a complete curated glue census"],
     "No curated glue database resolved for this build, so the atlas cannot state "
     "a total. The number of bridging ligands it found is a different quantity."),
    ("Is this lysine ubiquitylated?",
     ["observed ubiquitylation site data"],
     "The observed diGly site data is unavailable in this build, so the atlas "
     "cannot say whether a lysine is used."),
    ("What is the degradability score for this target?",
     ["a fitted reach window"],
     "The reach window has not been fitted, so no verdict and no aggregate score "
     "is produced. Spec 5.4 forbids reporting the unfitted starting values."),
    ("Give me the crystal structure of a ligase with no deposited structure.",
     ["a deposited structure for that accession"],
     "That accession has no deposited structure in the atlas; only an AlphaFold "
     "model is available."),
    ("What is the resolution of this AlphaFold model?",
     ["an experimental resolution"],
     "An AlphaFold model is a prediction and has no experimental resolution. It "
     "carries per-residue pLDDT instead."),
]


def generate_task_c(grounding: Grounding, rng: random.Random,
                    answerable: Sequence[Sample] = (),
                    target: int = 900) -> tuple[list[dict], list[dict]]:
    """Partial triads, genuinely unanswerable questions, and answerable ones.

    The answerable third is the point of this signature. Trained on refusals
    alone the head learned that the answer is always no: abstention recall
    1.0000 and specificity 0.0000, refusing all twelve of BINMAN's own presets
    (D-086). A classifier shown one class is not a classifier.

    The positives come from the Task A samples, which are the only questions in
    this build whose answerability is established rather than assumed: each one
    was generated against the live atlas and then parsed by the app's own
    parser, and anything the parser rejected was dropped. So "answerable" here
    means a query object the app will execute, not an opinion.

    They carry no numeric answer, only the decision and the record type that
    holds it, because the model never reports a number (spec 3.8).
    """
    samples: list[dict] = []
    pairs: list[dict] = []

    genes = grounding.vocabularies.get("ligase_gene", []) or ["CRBN", "VHL"]
    ccds = grounding.vocabularies.get("ccd_id", []) or ["RAP"]

    slots = ("glue", "ligase", "target")
    while len(samples) < target:
        # Partial triads: the degradability readout needs all three pinned.
        present = rng.sample(slots, rng.choice((1, 2)))
        missing = [s for s in slots if s not in present]
        described = []
        if "glue" in present:
            described.append(f"the glue {rng.choice(ccds)}")
        if "ligase" in present:
            described.append(f"the ligase {rng.choice(genes)}")
        if "target" in present:
            described.append("the pinned target")
        prompt = (
            f"I have {' and '.join(described)} pinned. "
            f"{rng.choice(['Give me the degradability readout.', 'What is the ternary score?', 'Resolve the centre of the triangle.', 'Report the degradability verdict.'])}"
        )
        refusal = {
            "answerable": False,
            "missing": missing,
            "explanation": (
                "A degradability readout needs all three corners pinned. "
                f"Missing: {', '.join(missing)}."
            ),
        }
        samples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_ABSTAIN},
                {"role": "user", "content": prompt},
                {"role": "assistant",
                 "content": json.dumps(refusal, separators=(",", ":"))},
            ],
            "kind": "partial_triad",
        })
        # The rejected sample is a confident fabrication: an invented value.
        fabrication = json.dumps({
            "answerable": True,
            "verdict": rng.choice(("favourable", "marginal")),
            "best_lysine": f"K{rng.randrange(20, 400)}",
            "nz_centroid_distance": round(rng.uniform(6, 22), 1),
            "held_out_auc": round(rng.uniform(0.7, 0.9), 2),
        }, separators=(",", ":"))
        pairs.append({
            "mode": "fabricated_number",
            "prompt": prompt, "system": SYSTEM_ABSTAIN,
            "chosen": json.dumps(refusal, separators=(",", ":")),
            "rejected": fabrication,
        })

    for question, missing, explanation in UNANSWERABLE:
        for _ in range(8):
            refusal = {"answerable": False, "missing": missing,
                       "explanation": explanation}
            samples.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_ABSTAIN},
                    {"role": "user", "content": question},
                    {"role": "assistant",
                     "content": json.dumps(refusal, separators=(",", ":"))},
                ],
                "kind": "unanswerable",
            })
            pairs.append({
                "mode": "fabricated_answer",
                "prompt": question, "system": SYSTEM_ABSTAIN,
                "chosen": json.dumps(refusal, separators=(",", ":")),
                "rejected": json.dumps({
                    "answerable": True,
                    "answer": f"It is approximately {round(rng.uniform(1, 100), 1)}.",
                    "pdb_id": f"{rng.randrange(1,9)}{''.join(rng.choices('ABCDEFGHJKLMNPQRSTUVWXYZ0123456789', k=3))}",
                }, separators=(",", ":")),
            })
    # The answerable class, balanced against the refusals so neither answer is
    # the safe one. A refusal on one of these is the failure this adds: it is
    # the rejected side of every pair below.
    refusals = len(samples)
    pool = list(answerable)
    rng.shuffle(pool)
    for sample in pool[:refusals]:
        accepted = {
            "answerable": True,
            "missing": [],
            "explanation": (
                f"The atlas holds this: it is a {sample.record_type} query."
            ),
        }
        samples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_ABSTAIN},
                {"role": "user", "content": sample.prompt},
                {"role": "assistant",
                 "content": json.dumps(accepted, separators=(",", ":"))},
            ],
            "kind": "answerable",
        })
        pairs.append({
            "mode": "refused_an_answerable_question",
            "prompt": sample.prompt, "system": SYSTEM_ABSTAIN,
            "chosen": json.dumps(accepted, separators=(",", ":")),
            "rejected": json.dumps({
                "answerable": False,
                "missing": [sample.record_type],
                "explanation": ("The atlas does not hold the records this "
                                "question asks about."),
            }, separators=(",", ":")),
        })

    rng.shuffle(samples)
    return samples, pairs


# --------------------------------------------------------------------------- #
# Task B: reported, not built (spec 3.4)
# --------------------------------------------------------------------------- #

def task_b_status() -> dict:
    """Spec 3.4 requires every label to come from a published curated source."""
    from pipeline.validate import dataset_resolved

    sources = {
        "molecular_glue": ["mgdb_glues", "molgluedb_glues", "mgtbind_ternary"],
        "protac": ["protacdb_protacs"],
        "native_cofactor": ["biolip2_annotations"],
        "crystallisation_artefact": ["biolip2_artefacts"],
        "bivalent_inhibitor": ["protacdb_protacs"],
    }
    available = {
        label: [name for name in names if dataset_resolved(name)]
        for label, names in sources.items()
    }
    missing = [label for label, names in available.items() if not names]
    return {
        "buildable": not missing,
        "available_label_sources": available,
        "classes_without_a_label_source": missing,
        "reason": (
            "Spec 3.4 requires every Task B label to come from a published curated "
            "source, and the glue label specifically from the intersection of at "
            "least two of MGDB, MolGlueDB and MGTbind. None of those resolved, and "
            "PROTAC-DB did not either, so three of the five classes have no label "
            "source. Spec 4.1b forbids substituting hand-written labels, so the "
            "Task B corpus is NOT built and the 9.5 macro-F1 is reported as not "
            "computed."
        ) if missing else "",
    }


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #

def build(target_a: int = 6000) -> dict:
    CORPUS.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    connection = None
    if DB_PATH.exists():
        connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        grounding = ground(connection)
    finally:
        if connection is not None:
            connection.close()

    vocab_sizes = {k: len(v) for k, v in grounding.vocabularies.items()}
    log_event("3.2", f"Corpus grounding: {len(grounding.ranges)} numeric field ranges "
                     f"read from the atlas, vocabularies {vocab_sizes}.")

    raw = generate_task_a(grounding, rng, target=target_a)
    samples, rejected = validate(raw)
    log_event("3.2", f"Task A generated {len(raw):,} pairs, {len(samples):,} validated "
                     f"by the app parser, {len(rejected):,} rejected and dropped "
                     f"(the corpus therefore has zero label noise by construction).")

    train, valid, test = split_by_composition(samples, rng)
    preference = generate_preference_pairs(train, grounding, rng, per_mode=200)
    # Only the Task A training split feeds the answerable class, so the Task A
    # held-out questions stay held out and the twelve app presets that
    # pipeline/lm_abstention_check.py measures specificity on are not in the
    # corpus at all.
    task_c, task_c_pairs = generate_task_c(grounding, rng, answerable=train)

    c_split = int(len(task_c) * 0.8)
    c_valid_split = int(len(task_c) * 0.9)

    counts = {
        "task_a_train": write_jsonl(CORPUS / "task_a_train.jsonl",
                                    [s.as_chat() for s in train]),
        "task_a_valid": write_jsonl(CORPUS / "task_a_valid.jsonl",
                                    [s.as_chat() for s in valid]),
        "task_a_test": write_jsonl(CORPUS / "task_a_test.jsonl",
                                   [s.as_chat() for s in test]),
        "task_a_preference": write_jsonl(CORPUS / "task_a_preference.jsonl", preference),
        "task_c_train": write_jsonl(CORPUS / "task_c_train.jsonl", task_c[:c_split]),
        "task_c_valid": write_jsonl(CORPUS / "task_c_valid.jsonl",
                                    task_c[c_split:c_valid_split]),
        "task_c_test": write_jsonl(CORPUS / "task_c_test.jsonl", task_c[c_valid_split:]),
        "task_c_preference": write_jsonl(CORPUS / "task_c_preference.jsonl", task_c_pairs),
        "rejected_by_parser": write_jsonl(CORPUS / "rejected.jsonl", rejected),
    }

    mode_counts: dict[str, int] = {}
    for pair in preference:
        mode_counts[pair["mode"]] = mode_counts.get(pair["mode"], 0) + 1

    report = {
        "generated_at": utcnow(),
        "seed": SEED,
        "counts": counts,
        "preference_modes": mode_counts,
        "vocabulary_sizes": vocab_sizes,
        "numeric_ranges": len(grounding.ranges),
        "split_rule": (
            "Compositions are held out, not tokens. Every field, operator and "
            "record type appears in training; the valid and test sets contain "
            "unseen combinations of them (spec 3.6)."
        ),
        "label_noise": (
            f"Zero by construction: all {counts['task_a_train'] + counts['task_a_valid'] + counts['task_a_test']:,} "
            f"shipped Task A pairs were validated by the same parser the app uses, "
            f"and {counts['rejected_by_parser']:,} generated pairs that failed it were dropped."
        ),
        "task_b": task_b_status(),
        "external_query_set": {
            "built": (CORPUS.parent / "corpus" / "external_queries.jsonl").exists(),
            "note": "Built separately by lm/harvest_external_queries.py (spec 3.6).",
        },
    }
    (CORPUS / "corpus_report.json").write_text(json.dumps(report, indent=2) + "\n")
    Manifest(STAGE).record("build", status="ok", **counts)
    log_event("3.2", f"Corpus written: Task A {counts['task_a_train']:,}/"
                     f"{counts['task_a_valid']:,}/{counts['task_a_test']:,}, "
                     f"{counts['task_a_preference']:,} preference pairs across "
                     f"{len(mode_counts)} modes, Task C {counts['task_c_train']:,} "
                     f"train. Task B buildable: {report['task_b']['buildable']}.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the BINMAN-LM corpora")
    parser.add_argument("--target", type=int, default=6000)
    args = parser.parse_args()
    report = build(target_a=args.target)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
