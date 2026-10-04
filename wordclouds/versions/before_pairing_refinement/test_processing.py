"""Focused safeguards for the scientific term processing, not pixel snapshots."""
import unittest
from generate import HERE, Rules, read_csv


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
        for term in ["socioeconomic status", "socioeconomic deprivation", "health inequality"]:
            self.assertEqual(counts[term], 1)
        self.assertNotIn("deprivation", counts)

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

    def test_ambiguity_not_silently_expanded(self):
        counts, _ = self.rules.process("CHD")
        self.assertNotIn("coronary heart disease", counts)
        self.assertIn("chd", self.rules.exclusions)

    def test_paper_frequency_counts_each_term_once_per_document(self):
        counts, _ = self.rules.process("mortality mortality mortality")
        self.assertEqual(counts["mortality"], 3)
        self.assertEqual(len([term for term in counts if term == "mortality"]), 1)


if __name__ == "__main__":
    unittest.main()
