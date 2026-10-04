"""Focused safeguards for the scientific term processing, not pixel snapshots."""
import unittest
from collections import Counter
from generate import HERE, Rules, count_terms, read_csv, select_terms


class ProcessingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = Rules(read_csv(HERE / "term_groups.csv"), read_csv(HERE / "exclusions.csv"))

    def test_longest_phrase_and_subtypes(self):
        counts, _ = self.rules.process("Type 1 diabetes and type 2 diabetes differ. Low birthweight affects quality of life.")
        for term in ["type 1 diabetes", "type 2 diabetes", "low birth weight", "quality of life"]:
            self.assertEqual(counts[term], 1)
        self.assertNotIn("diabetes", counts)
        self.assertNotIn("birth weight", counts)

    def test_preserve_distinct_social_concepts(self):
        counts, _ = self.rules.process("Socio-economic status and socioeconomic deprivation and health inequalities.")
        for term in ["socioeconomic status", "deprivation", "health inequality"]:
            self.assertEqual(counts[term], 1)
        self.assertNotIn("socioeconomic deprivation", counts)

    def test_abbreviations_and_spelling(self):
        counts, _ = self.rules.process("SIMD and Scottish Index of Multiple Deprivation; tumour tumors hospitalizations hospitalisation.")
        self.assertEqual(counts["SIMD"], 2)
        self.assertEqual(counts["tumour"], 2)
        self.assertEqual(counts["hospitalisation"], 2)
        self.assertIn("simd", self.rules.exclusions)
        self.assertNotIn("mortality", self.rules.exclusions)

    def test_no_phrases_created_by_stopword_removal(self):
        counts, _ = self.rules.process("mental and health outcomes")
        self.assertNotIn("mental health", counts)

    def test_no_pairs_across_sentence_or_section_boundaries(self):
        for text in ["mental. Health", "mental; health", "mental: health", "mental\nhealth", "mental, health", "mental (health)"]:
            counts, _ = self.rules.process(text)
            self.assertNotIn("mental health", counts)

    def test_status_keeps_its_explicit_qualifier(self):
        counts, _ = self.rules.process("Smoking status and health status were assessed alongside vaccination status and socioeconomic deprivation status.")
        for term in ["smoking status", "health status", "vaccination status", "deprivation"]:
            self.assertEqual(counts[term], 1)
        self.assertNotIn("socioeconomic status", counts)
        self.assertNotIn("status", counts)

    def test_incomplete_adjective_is_not_assigned_a_construct(self):
        counts, _ = self.rules.process("Socioeconomic factors and socioeconomic circumstances; socioeconomic.")
        self.assertEqual(counts["socioeconomic factor"], 1)
        self.assertEqual(counts["socioeconomic circumstance"], 1)
        self.assertEqual(counts["socioeconomic"], 1)
        self.assertNotIn("socioeconomic status", counts)
        self.assertIn("socioeconomic", self.rules.exclusions)
        self.assertIn("status", self.rules.exclusions)

    def test_deprivation_family_is_one_document_term(self):
        texts = ["Deprivation and social deprivation and area-based deprivation in socioeconomically deprived groups.", "Deprived areas."]
        mentions, papers, _, _ = count_terms(self.rules, texts)
        self.assertEqual(mentions["deprivation"], 5)
        self.assertEqual(papers["deprivation"], 2)
        self.assertNotIn("deprived", papers)

    def test_named_index_does_not_inflate_deprivation_topic(self):
        counts, _ = self.rules.process("Scottish Index of Multiple Deprivation (SIMD)")
        self.assertEqual(counts["SIMD"], 2)
        self.assertNotIn("deprivation", counts)

    def test_ambiguity_not_silently_expanded(self):
        counts, _ = self.rules.process("CHD")
        self.assertNotIn("coronary heart disease", counts)
        self.assertIn("chd", self.rules.exclusions)

    def test_paper_frequency_counts_each_term_once_per_document(self):
        mentions, papers, _, _ = count_terms(self.rules, ["mortality mortality mortality", "Mortality.", "survival"])
        self.assertEqual(mentions["mortality"], 4)
        self.assertEqual(papers["mortality"], 2)

    def test_ties_at_display_limit_are_not_split(self):
        weight = Counter({"a": 9, "b": 5, "c": 5, "d": 5, "e": 1})
        self.assertEqual(select_terms(weight, list(weight), 2), ["a"])
        self.assertEqual(select_terms(weight, list(weight), 4), ["a", "b", "c", "d"])
        self.assertEqual(select_terms(weight, list(weight), 10), ["a", "b", "c", "d", "e"])

    def test_plurals_merge_only_into_observed_singulars(self):
        rules = Rules(read_csv(HERE / "term_groups.csv"), read_csv(HERE / "exclusions.csv"))
        rules.fold_plurals({"hospital", "hospitals", "policy", "policies", "falls", "fall", "diabetes", "status"}, {"falls"})
        counts, _ = rules.process("Hospitals and hospital policies; falls; diabetes")
        self.assertEqual(counts["hospital"], 2)
        self.assertEqual(counts["policy"], 1)
        self.assertEqual(counts["falls"], 1)
        self.assertEqual(counts["diabetes"], 1)

    def test_hyphenated_compounds_are_kept_and_fragments_dropped(self):
        counts, _ = self.rules.process("E-cigarettes and cigarettes; well-being; self-reported pre-existing disease")
        self.assertEqual(counts["e-cigarette"], 1)
        self.assertEqual(counts["wellbeing"], 1)
        self.assertEqual(counts["cigarettes"], 1)
        for fragment in ["self", "pre"]:
            self.assertIn(fragment, self.rules.exclusions)


if __name__ == "__main__":
    unittest.main()
