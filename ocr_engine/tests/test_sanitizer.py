"""Parametrized tests for LineSanitizer — GATE for Phase 2.

Every re.sub() from pradones/process_padron.py:sanitize_line() must have
at least one test case here. Tests use real-looking OCR input strings.
"""

import pytest

from ocr_engine.parsing.sanitizer import LineSanitizer


@pytest.fixture
def san() -> LineSanitizer:
    return LineSanitizer("069")


@pytest.fixture
def san_base() -> LineSanitizer:
    return LineSanitizer()


# ============================================================
# BASE RULES — DNI cleanup (4 rules)
# ============================================================

class TestBaseDniCleanup:
    """Tests for base sanitization rules (not distrito-specific)."""

    @pytest.mark.parametrize("input_line,expected", [
        # Trailing punctuation on DNI
        ("DNI 14009185. PEREZ JUAN", "DNI 14009185 PEREZ JUAN"),
        ("DNI 27241872, VILLAFAÑE JORGE", "DNI 27241872 VILLAFAÑE JORGE"),
        ('DNI 12345678" GARCIA', 'DNI 12345678 GARCIA'),
        ("DNI 14009185; LOPEZ ANA", "DNI 14009185 LOPEZ ANA"),
        ("LC 7654321' MARTINEZ", "LC 7654321 MARTINEZ"),
        ("LE 8765432_ RODRIGUEZ", "LE 8765432 RODRIGUEZ"),
        # Multiple trailing chars
        ("DNI 14009185., PEREZ", "DNI 14009185 PEREZ"),
    ])
    def test_dni_trailing_punctuation(self, san_base, input_line, expected):
        assert san_base.sanitize(input_line) == expected

    @pytest.mark.parametrize("input_line,expected", [
        # Extra digit before DNI
        ("DNI 2 14819326 GARCIA MARIA", "DNI 14819326 GARCIA MARIA"),
        ("DNI 5 27241872 PEREZ JUAN", "DNI 27241872 PEREZ JUAN"),
        ("LC 1 7654321 MARTINEZ ANA", "LC 7654321 MARTINEZ ANA"),
    ])
    def test_extra_digit_before_dni(self, san_base, input_line, expected):
        assert san_base.sanitize(input_line) == expected

    @pytest.mark.parametrize("input_line,expected", [
        # Extra chars appended to DNI
        ("DNI 21548468B_ LOPEZ ANA", "DNI 21548468 LOPEZ ANA"),
        ("DNI 27241872XY PEREZ", "DNI 27241872 PEREZ"),
    ])
    def test_extra_chars_after_dni(self, san_base, input_line, expected):
        assert san_base.sanitize(input_line) == expected

    @pytest.mark.parametrize("input_line,expected", [
        # Space before dash in code letters
        ("DNI 12345678 PEREZ JUAN 0-069-MT -0004 1", "DNI 12345678 PEREZ JUAN 0-069-MT-0004 1"),
    ])
    def test_space_before_dash(self, san_base, input_line, expected):
        assert san_base.sanitize(input_line) == expected


# ============================================================
# DISTRITO 069 — District number fixes (3 rules)
# ============================================================

class TestDistritoNumberFixes:

    @pytest.mark.parametrize("input_line,expected", [
        ("DNI 12345678 PEREZ D-069-MS-0001 1", "DNI 12345678 PEREZ 0-069-MS-0001 1"),
    ])
    def test_d_instead_of_zero(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected

    @pytest.mark.parametrize("input_line,expected", [
        ("DNI 12345678 PEREZ 0-0692-MS-0001 1", "DNI 12345678 PEREZ 0-069-MS-0001 1"),
    ])
    def test_extra_digit_in_distrito(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected

    @pytest.mark.parametrize("input_line,expected", [
        ("DNI 12345678 PEREZ 0-D69-MS-0001 1", "DNI 12345678 PEREZ 0-069-MS-0001 1"),
    ])
    def test_d_in_section_number(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected


# ============================================================
# DISTRITO 069 — Space inside codes (1 rule)
# ============================================================

class TestSpaceInsideCodes:

    @pytest.mark.parametrize("input_line,expected", [
        ("DNI 12345678 PEREZ 0-069- MS-0001 1", "DNI 12345678 PEREZ 0-069-MS-0001 1"),
        ("DNI 12345678 PEREZ 0-069-  PP-0042 2", "DNI 12345678 PEREZ 0-069-PP-0042 2"),
    ])
    def test_space_after_distrito(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected


# ============================================================
# DISTRITO 069 — J1/JI OCR corruption (11 rules)
# ============================================================

class TestJ1JiFixes:

    @pytest.mark.parametrize("input_line,expected", [
        # J| → J1
        ("DNI 12345678 PEREZ 0-069-J|-0001 1", "DNI 12345678 PEREZ 0-069-J1-0001 1"),
        # J! → J1
        ("DNI 12345678 PEREZ 0-069-J!-0001 1", "DNI 12345678 PEREZ 0-069-J1-0001 1"),
        # )1 → J1
        ("DNI 12345678 PEREZ 0-069-)1-0001 1", "DNI 12345678 PEREZ 0-069-J1-0001 1"),
        # ,1- → J1-
        ("DNI 12345678 PEREZ 0-069-,1-0001 1", "DNI 12345678 PEREZ 0-069-J1-0001 1"),
        # .1- → J1-
        ("DNI 12345678 PEREZ 0-069-.1-0001 1", "DNI 12345678 PEREZ 0-069-J1-0001 1"),
        # ;1- → J1-
        ("DNI 12345678 PEREZ 0-069-;1-0001 1", "DNI 12345678 PEREZ 0-069-J1-0001 1"),
        # ,I- → JI-
        ("DNI 12345678 PEREZ 0-069-,I-0001 1", "DNI 12345678 PEREZ 0-069-JI-0001 1"),
        # .I- → JI-
        ("DNI 12345678 PEREZ 0-069-.I-0001 1", "DNI 12345678 PEREZ 0-069-JI-0001 1"),
        # .J1 → J1
        ("DNI 12345678 PEREZ 0-069-.J1-0001 1", "DNI 12345678 PEREZ 0-069-J1-0001 1"),
        # Bare 1- (missing J)
        ("DNI 12345678 PEREZ 0-069-1-0001 1", "DNI 12345678 PEREZ 0-069-J1-0001 1"),
        # ,)I- → JI-
        ("DNI 12345678 PEREZ 0-069-,)I-0001 1", "DNI 12345678 PEREZ 0-069-JI-0001 1"),
    ])
    def test_j1_ji_corruptions(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected

    @pytest.mark.parametrize("input_line,expected", [
        # .J → J (dot before J in code)
        ("DNI 12345678 PEREZ 0-069-.JI-0001 1", "DNI 12345678 PEREZ 0-069-JI-0001 1"),
    ])
    def test_dot_before_j(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected


# ============================================================
# DISTRITO 069 — Pound sign fixes (4 rules, literal)
# ============================================================

class TestPoundSignFixes:

    @pytest.mark.parametrize("input_line,expected", [
        ("DNI 12345678 PEREZ 0-069-£E-0001 1", "DNI 12345678 PEREZ 0-069-EE-0001 1"),
        ("DNI 12345678 PEREZ 0-069-E£-0001 1", "DNI 12345678 PEREZ 0-069-EE-0001 1"),
        ("DNI 12345678 PEREZ 0-069-A£-0001 1", "DNI 12345678 PEREZ 0-069-AE-0001 1"),
        ("DNI 12345678 PEREZ 0-069-££-0001 1", "DNI 12345678 PEREZ 0-069-EE-0001 1"),
    ])
    def test_pound_sign_to_letters(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected


# ============================================================
# DISTRITO 069 — Letter code fixes (2 rules)
# ============================================================

class TestLetterCodeFixes:

    @pytest.mark.parametrize("input_line,expected", [
        ("DNI 12345678 PEREZ 0-069-EL.-0001 1", "DNI 12345678 PEREZ 0-069-EL-0001 1"),
        ("DNI 12345678 PEREZ 0-069-T.J-0001 1", "DNI 12345678 PEREZ 0-069-TJ-0001 1"),
    ])
    def test_dot_in_letter_code(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected


# ============================================================
# DISTRITO 069 — Doubled/extra chars in 2-letter code (12 rules)
# ============================================================

class TestDoubledCharFixes:

    @pytest.mark.parametrize("input_line,expected", [
        ("DNI 12345678 PEREZ 0-069-MS5-0042 1", "DNI 12345678 PEREZ 0-069-MS-0042 1"),
        ("DNI 12345678 PEREZ 0-069-M3S-0042 1", "DNI 12345678 PEREZ 0-069-MS-0042 1"),
        ("DNI 12345678 PEREZ 0-069-8B5-0003 1", "DNI 12345678 PEREZ 0-069-BS-0003 1"),
        ("DNI 12345678 PEREZ 0-069-8BS-0003 1", "DNI 12345678 PEREZ 0-069-BS-0003 1"),
        ("DNI 12345678 PEREZ 0-069-85S-0003 1", "DNI 12345678 PEREZ 0-069-BS-0003 1"),
        ("DNI 12345678 PEREZ 0-069-A4A-0003 1", "DNI 12345678 PEREZ 0-069-AA-0003 1"),
        ("DNI 12345678 PEREZ 0-069-D0F-0003 1", "DNI 12345678 PEREZ 0-069-DF-0003 1"),
        ("DNI 12345678 PEREZ 0-069-D0M-0003 1", "DNI 12345678 PEREZ 0-069-DM-0003 1"),
        ("DNI 12345678 PEREZ 0-069-0DM-0003 1", "DNI 12345678 PEREZ 0-069-DM-0003 1"),
        ("DNI 12345678 PEREZ 0-069-S5C-0003 1", "DNI 12345678 PEREZ 0-069-SC-0003 1"),
        ("DNI 12345678 PEREZ 0-069-0F-0003 1", "DNI 12345678 PEREZ 0-069-DF-0003 1"),
        ("DNI 12345678 PEREZ 0-069-1S5-0003 1", "DNI 12345678 PEREZ 0-069-1S-0003 1"),
    ])
    def test_doubled_chars_in_code(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected


# ============================================================
# DISTRITO 069 — Single letter code fix (1 rule)
# ============================================================

class TestSingleLetterCode:

    def test_missing_s_in_ms(self, san):
        assert san.sanitize("DNI 12345678 PEREZ 0-069-M-0042 1") == "DNI 12345678 PEREZ 0-069-MS-0042 1"


# ============================================================
# DISTRITO 069 — Dot instead of dash (1 rule)
# ============================================================

class TestDotInsteadOfDash:

    def test_dot_separator(self, san):
        assert san.sanitize("DNI 12345678 PEREZ 0-069.MS-0042 1") == "DNI 12345678 PEREZ 0-069-MS-0042 1"

    def test_dot_separator_other_code(self, san):
        assert san.sanitize("DNI 12345678 PEREZ 0-069.PP-0042 1") == "DNI 12345678 PEREZ 0-069-PP-0042 1"


# ============================================================
# DISTRITO 069 — D instead of 0 in number part (2 rules)
# ============================================================

class TestDInNumberPart:

    @pytest.mark.parametrize("input_line,expected", [
        ("DNI 12345678 PEREZ 0-069-DM-D454 1", "DNI 12345678 PEREZ 0-069-DM-0454 1"),
        ("DNI 12345678 PEREZ 0-069-PP-D0037 1", "DNI 12345678 PEREZ 0-069-PP-00037 1"),
    ])
    def test_d_to_zero_in_number(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected


# ============================================================
# DISTRITO 069 — Space in code number (2 rules)
# ============================================================

class TestSpaceInCodeNumber:

    @pytest.mark.parametrize("input_line,expected", [
        ("DNI 12345678 PEREZ 0-069-J1- 1004 1", "DNI 12345678 PEREZ 0-069-J1-1004 1"),
        ("DNI 12345678 PEREZ 0-069-MS-01 14 1", "DNI 12345678 PEREZ 0-069-MS-0114 1"),
    ])
    def test_space_in_code_number(self, san, input_line, expected):
        assert san.sanitize(input_line) == expected


# ============================================================
# DISTRITO 069 — Cross-distrito catch-alls (2 rules)
# ============================================================

class TestCrossDistrito:

    def test_089_dot_one(self, san):
        assert san.sanitize("DNI 12345678 PEREZ 0-089-.1-0001 1") == "DNI 12345678 PEREZ 0-089-J1-0001 1"

    def test_generic_comma_one(self, san):
        assert san.sanitize("DNI 12345678 PEREZ 0-069-,1-0001 1") == "DNI 12345678 PEREZ 0-069-J1-0001 1"
        assert san.sanitize("DNI 12345678 PEREZ 0-079-,1-0001 1") == "DNI 12345678 PEREZ 0-079-J1-0001 1"


# ============================================================
# MULTI-RULE CHAINS (input that triggers 2+ rules)
# ============================================================

class TestMultiRuleChains:

    def test_dni_cleanup_plus_code_fix(self, san):
        """DNI trailing punct + MS5 → MS."""
        result = san.sanitize("DNI 14009185. PEREZ JUAN 0-069-MS5-0042 1")
        assert result == "DNI 14009185 PEREZ JUAN 0-069-MS-0042 1"

    def test_extra_digit_plus_d069(self, san):
        """Extra digit before DNI + D-069."""
        result = san.sanitize("DNI 2 14819326 GARCIA MARIA D-069-J1-0001 5")
        assert result == "DNI 14819326 GARCIA MARIA 0-069-J1-0001 5"

    def test_extra_chars_plus_8b5(self, san):
        """Extra chars after DNI + 8B5 → BS."""
        result = san.sanitize("DNI 21548468B_ LOPEZ ANA 0-069-8B5-0003 2")
        assert result == "DNI 21548468 LOPEZ ANA 0-069-BS-0003 2"

    def test_d069_plus_pound_sign(self, san):
        """D-069 + £E → EE."""
        result = san.sanitize("DNI 12345678 PEREZ D-069-£E-0001 1")
        assert result == "DNI 12345678 PEREZ 0-069-EE-0001 1"

    def test_space_plus_dot_j(self, san):
        """Space after distrito + .J → J."""
        result = san.sanitize("DNI 12345678 PEREZ 0-069- .J1-0001 1")
        assert result == "DNI 12345678 PEREZ 0-069-J1-0001 1"


# ============================================================
# EDGE CASES
# ============================================================

class TestEdgeCases:

    def test_empty_string(self, san):
        assert san.sanitize("") == ""

    def test_whitespace_only(self, san):
        assert san.sanitize("   ") == ""

    def test_no_matches(self, san):
        line = "DNI 27241872 VILLAFAÑE JORGE 0-069-MT-0001 1"
        assert san.sanitize(line) == line

    def test_non_dni_line(self, san):
        line = "MESA 42 ESCUELA N°5"
        assert san.sanitize(line) == line

    def test_short_line(self, san):
        assert san.sanitize("ABC") == "ABC"

    def test_unknown_distrito_uses_base_only(self):
        san = LineSanitizer("999")
        assert san.rule_count == 4  # base only
        # Base rules still work
        assert san.sanitize("DNI 12345678. PEREZ") == "DNI 12345678 PEREZ"

    def test_no_distrito_uses_base_only(self):
        san = LineSanitizer()
        assert san.rule_count == 4

    def test_rule_count_069(self, san):
        assert san.rule_count == 45  # 4 base + 41 distrito
