import sys
import os

# Add uzsl_bot to path so we can import from it
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uzsl_bot"))

from utils.grammar_translator import translate_uzsl_to_uzbek  # noqa: E402


def test_grammar_translator():
    test_cases = [
        (["men", "do'kon", "bormoq"], "Men do'konga boryapman."),
        (["sen", "shifoxona", "kelmoq"], "Sen shifoxonaga kelyapsan."),
        (["u", "maktab", "bormoq"], "U maktabga boryapti."),
        (["biz", "bozor", "bormoq"], "Biz bozorga boryapmiz."),
        (["men", "bank", "bormoq"], "Men bankka boryapman."),
        (["men", "qishloq", "bormoq"], "Men qishloqqa boryapman."),
        (["men", "uy", "bormoq"], "Men uyga boryapman."),
        (["men", "suv", "ichmoq"], "Men suvni ichyapman."),
        (["biz", "non", "yemoq"], "Biz nonni yeyapmiz."),
        (["kecha", "men", "ish", "bormoq"], "Kecha men ishga bordim."),
        (["o'tgan", "biz", "maktab", "bormoq"], "O'tgan biz maktabga bordik."),
        (["ertaga", "sen", "uy", "kelmoq"], "Ertaga sen uyga kelmoqchisan."),
        (["keyin", "ular", "bozor", "bormoq"], "Keyin ular bozorga bormoqchilar."),
        (["men", "sut", "ichmoq", "yo'q"], "Men sutni ichmayapman."),
        (["kecha", "u", "uy", "kelmoq", "yo'q"], "Kecha u uyga kelmadi."),
        (["ertaga", "biz", "bozor", "bormoq", "yo'q"], "Ertaga biz bozorga bormoqchimasmiz."),
        (["men", "yaxshi"], "Men yaxshiman."),
        (["biz", "xursand"], "Biz xursandmiz."),
        (["rahmat", "men", "yaxshi"], "Rahmat, men yaxshiman."),
        (["men", "do'kon"], "Men do'kondaman."),
        (["biz", "maktab"], "Biz maktabdamiz.")
    ]

    for inp, expected in test_cases:
        result = translate_uzsl_to_uzbek(inp)
        assert result == expected, f"Failed for {inp}: expected '{expected}', got '{result}'"
