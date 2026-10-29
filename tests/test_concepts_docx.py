import os
import re
import tempfile
import unittest

import docx

from agent_system import producer, story


def _facts():
    f = story.Facts(firm_name="GSP Law Firm")
    f.items["years_experience"] = story.Fact("years_experience", "16", "OPERATOR", "", "CORROBORATED")
    f.items["team_size"] = story.Fact("team_size", "15", "S05", "", "SINGLE-SOURCE")
    f.items["address"] = story.Fact("address", "Toshkent sh., Mirobod ko'chasi, 46a-uy", "S05", "", "SINGLE-SOURCE")
    f.items["partners"] = story.Fact("partners", '[{"name": "A B", "role": "Основатель, Управляющий партнёр", '
        '"specialties": "Корпоративное право; M&A", "experience": "15+ лет"}]', "S05", "", "SINGLE-SOURCE")
    return f


def _text(lang, facts):
    with tempfile.TemporaryDirectory() as d:
        path = producer.write_concepts_docx(os.path.join(d, "c.docx"), "GSP", facts, lang)
        return "\n".join(p.text for p in docx.Document(path).paragraphs)


class ConceptsDocx(unittest.TestCase):
    def test_uzbek_has_no_cyrillic(self):
        self.assertIsNone(re.search("[А-Яа-яЁё]", _text("uz", _facts())))

    def test_unknown_language_falls_back_to_russian(self):
        self.assertIn("Концепции", _text("en", _facts()))

    def test_only_ledger_facts_and_gaps_are_listed(self):
        t = _text("ru", _facts())
        self.assertIn("16 лет (подтверждено оператором)", t)
        self.assertIn("не подтверждено", t.lower())
        self.assertNotIn("Клиентов", t)          # no clients fact -> no line

    def test_empty_facts_do_not_invent(self):
        t = _text("ru", None)
        self.assertIn("Данных пока нет.", t)
        self.assertNotIn("лет (", t)


if __name__ == "__main__":
    unittest.main()
