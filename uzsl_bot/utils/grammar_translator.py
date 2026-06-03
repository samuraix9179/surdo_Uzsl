import re

# Predicative personal endings for verbs and adjectives
# Morphotactic suffixes for Uzbek grammar
_PERSONAL_ENDINGS = {
    "present_continuous": {  # -yap + ending
        "men": "man",
        "sen": "san",
        "u": "ti",
        "biz": "miz",
        "siz": "siz",
        "ular": "tilar"
    },
    "past": {  # -di + ending
        "men": "m",
        "sen": "ng",
        "u": "",
        "biz": "k",
        "siz": "ngiz",
        "ular": "lar"
    },
    "future_intent": {  # -moqchi + ending
        "men": "man",
        "sen": "san",
        "u": "",
        "biz": "miz",
        "siz": "siz",
        "ular": "lar"
    },
    "predicate": {  # state/adjective + personal ending
        "men": "man",
        "sen": "san",
        "u": "",
        "biz": "miz",
        "siz": "siz",
        "ular": "lar"
    }
}

# Standard list of adjectives/states for predication
_ADJECTIVES = {
    "yaxshi", "yomon", "charchagan", "kasal", "xursand",
    "tayyor", "band", "sog'", "baxtli", "tinch", "och", "to'q"
}

# Motion verbs requiring dative (-ga) case on destination nouns
_MOTION_VERBS = {
    "bormoq", "kelmoq", "yugurmoq", "ketmoq", "kirmoq", "chiqmoq", "qaytmoq"
}

# Transitive verbs that can take accusative (-ni) case on direct objects
_TRANSITIVE_VERBS = {
    "ichmoq", "yemoq", "olmoq", "bermoq", "ko'rmoq", "yozmoq", "o'qimoq", "sotib olmoq"
}

# Locations/places in UZSL
_PLACES = {
    "uy", "do'kon", "shifoxona", "avtobus", "maktab", "bozor", "bank", 
    "toshkent", "ish", "o'qish", "qishloq", "shahar", "bog'", "xona", "universitet"
}

# Transitive target objects in UZSL
_OBJECTS = {
    "non", "suv", "sut", "pul", "kitob", "qalam", "choy", "ovqat", "koptok"
}

# Time anchors to set tense context
_PAST_MARKERS = {"kecha", "o'tgan", "avval", "burun"}
_FUTURE_MARKERS = {"ertaga", "keyin", "kelasi", "ertagaga"}


def get_dative_suffix(word: str) -> str:
    """O'zbek tilidagi jo'nalish kelishigi qo'shimchasi (-ga, -ka, -qa).

    Qoidalar (Consonant Harmony):
      - So'z oxiri 'k' bilan tugasa: '-ka' (masalan: bank -> bankka, sherik -> sherikka)
      - So'z oxiri 'q' bilan tugasa: '-qa' (masalan: qishloq -> qishloqqa, o'rtoq -> o'rtoqqa)
      - Boshqa hollarda: '-ga' (masalan: uy -> uyga, maktab -> maktabga, shahar -> shaharga)
    """
    word_clean = word.strip().lower()
    if not word_clean:
        return word

    # Unli va undosh tovush uyg'unligini tekshiramiz
    if word_clean.endswith("k"):
        return f"{word}ka"
    elif word_clean.endswith("q"):
        return f"{word}qa"
    else:
        return f"{word}ga"


def conjugate_verb(verb: str, pronoun: str, tense: str = "present_continuous", is_negative: bool = False) -> str:
    """Fe'lni subyekt va zamonga qarab dinamik tuslaydi, bo'lishsizlikni inobatga oladi."""
    verb_clean = verb.strip().lower()
    parts = verb_clean.split()
    conjugate_part = parts[-1]

    if not conjugate_part.endswith("moq"):
        return verb  # Agar moq bilan tugamasa, shundoq qaytaramiz

    stem = conjugate_part[:-3]  # "moq" olib tashlanadi
    neg_suffix = "ma" if is_negative else ""

    endings = _PERSONAL_ENDINGS.get(tense, _PERSONAL_ENDINGS["present_continuous"])
    personal_ending = endings.get(pronoun, endings["men"])

    if tense == "present_continuous":
        # Hozirgi zamon davom fe'li (-yap)
        # E.g.: kel + ma + yap + man = kelmayapman
        # kel + yap + man = kelyapman
        # og'ri + ma + yap + man = og'rimayapman
        return " ".join(parts[:-1] + [f"{stem}{neg_suffix}yap{personal_ending}"])

    elif tense == "past":
        # O'tgan zamon (-di)
        # E.g.: kel + ma + di + m = kelmadim
        # kel + di + m = keldim
        return " ".join(parts[:-1] + [f"{stem}{neg_suffix}di{personal_ending}"])

    elif tense == "future_intent":
        # Kelasi zamon niyat (-moqchi)
        # E.g.: bor + moqchimas + man = bormoqchimasman
        # bor + moqchiman = bormoqchiman
        if is_negative:
            return " ".join(parts[:-1] + [f"{stem}moqchimas{personal_ending}"])
        else:
            return " ".join(parts[:-1] + [f"{stem}moqchi{personal_ending}"])

    return verb


def conjugate_adjective(adjective: str, pronoun: str) -> str:
    """Sifatga subyektga mos xabar (predikativ) qo'shimchalarini ulaydi."""
    endings = _PERSONAL_ENDINGS["predicate"]
    personal_ending = endings.get(pronoun, "")
    if not personal_ending:
        return adjective
    return f"{adjective}{personal_ending}"


def translate_uzsl_to_uzbek(words: list[str]) -> str:
    """Imo-ishora so'zlar ketma-ketligini tabiiy o'zbek tiliga grammatik to'g'rilaydi.

    Qo'llaniladigan qoidalar:
      1. Gapdagi vaqt belgilariga qarab zamon aniqlanadi (kecha -> past, ertaga -> future).
      2. Gapdagi 'yo'q' inkor yuklamasi topilsa, fe'l inkor (bo'lishsiz) tuslanadi.
      3. Joy otlari harakat fe'llaridan oldin kelsa dative (-ga/-ka/-qa) qo'shimchasini oladi.
      4. Tovarlar va to'g'ri ob'ektlar o'tishli fe'llardan oldin kelsa accusative (-ni) oladi.
      5. Olmoshlarga qarab fe'llar va sifatlar shaxs-songa mos ravishda to'g'ri tuslanadi.
    """
    if not words:
        return ""

    # Clean words
    cleaned_words = [w.strip().lower() for w in words if w.strip()]
    if not cleaned_words:
        return ""

    # 1. Bo'lishsizlik (Negation) aniqlash
    is_negative = False
    if "yo'q" in cleaned_words:
        is_negative = True
        cleaned_words = [w for w in cleaned_words if w != "yo'q"]

    # 2. Zamon (Tense) aniqlash
    tense = "present_continuous"  # default hozirgi zamon
    for w in cleaned_words:
        if w in _PAST_MARKERS:
            tense = "past"
            break
        elif w in _FUTURE_MARKERS:
            tense = "future_intent"
            break

    # 3. Subyekt (Pronoun) aniqlash
    pronouns = {"men", "sen", "u", "biz", "siz", "ular"}
    subject = "men"  # default subyekt
    has_explicit_pronoun = False

    for w in cleaned_words:
        if w in pronouns:
            subject = w
            has_explicit_pronoun = True
            break

    # Fe'llar va harakat fe'llarini oldindan topib olish
    has_motion_verb = any(w in _MOTION_VERBS for w in cleaned_words)
    has_transitive_verb = any(w in _TRANSITIVE_VERBS for w in cleaned_words)

    result_words = []

    for idx, w in enumerate(cleaned_words):
        # 1. Olmoshlarni shundoq qoldiramiz (gap boshida kelsa Capitalize qilinadi)
        if w in pronouns:
            if w == subject and has_explicit_pronoun:
                result_words.append(w.capitalize() if idx == 0 else w)
            continue

        # 2. Vaqt ko'rsatkichlari
        if w in _PAST_MARKERS or w in _FUTURE_MARKERS:
            result_words.append(w.capitalize() if idx == 0 else w)
            continue

        # 3. Agar so'z fe'l bo'lsa (moq bilan tugasa) -> Dinamik tuslaymiz
        if w.endswith("moq"):
            conjugated = conjugate_verb(w, subject, tense, is_negative)
            result_words.append(conjugated)
            continue

        # 4. Agar so'z sifat bo'lsa -> Subyektga bog'lab tuslaymiz
        if w in _ADJECTIVES:
            conjugated = conjugate_adjective(w, subject)
            result_words.append(conjugated.capitalize() if idx == 0 else conjugated)
            continue

        # 5. Otlarni kelishiklarini tekshirish
        # Agar bu so'z oxirgi so'z bo'lmasa va joy/tovar otlari bo'lsa
        is_last = (idx == len(cleaned_words) - 1)
        if not is_last:
            next_word = cleaned_words[idx + 1]
            # Harakat fe'li oldidagi joy otlari (-ga)
            if next_word in _MOTION_VERBS or has_motion_verb:
                # Agar kelasi so'z to'g'ridan-to'g'ri fe'l bo'lsa yoki gapda harakat fe'li bo'lsa
                if w in _PLACES:
                    result_words.append(get_dative_suffix(w))
                    continue
            
            # O'tishli fe'l oldidagi to'g'ri ob'ektlar (-ni)
            if next_word in _TRANSITIVE_VERBS or has_transitive_verb:
                if w in _OBJECTS:
                    result_words.append(f"{w}ni")
                    continue

        # O'rin-joy predikativi sifatida kelsa (masalan: men do'kon -> Men do'kondaman)
        if w in _PLACES:
            # Agar gapda hech qanday boshqa fe'l yoki sifat bo'lmasa, demak bu joyda ekanligini bildiradi
            has_other_predicate = any(word.endswith("moq") or word in _ADJECTIVES for word in cleaned_words)
            if not has_other_predicate and has_explicit_pronoun:
                endings = _PERSONAL_ENDINGS["predicate"]
                personal_ending = endings.get(subject, "")
                result_words.append(f"{w}da{personal_ending}")
                continue

        # 6. Default: Oddiy so'zlarni o'zgarishsiz qoldiramiz
        result_words.append(w.capitalize() if idx == 0 else w)

    # Gapni birlashtirish
    if not result_words:
        return ""

    sentence = " ".join(result_words)

    # Rahmat, Yaxshiman yoki Salom, qalesiz kabi vergul qo'shish qoidalari
    if len(result_words) >= 2 and result_words[0].lower() in ["salom", "rahmat", "kechirasiz"]:
        sentence = f"{result_words[0]}, " + " ".join(result_words[1:])

    # Gap oxiriga tinish belgisi qo'yish
    if not sentence.endswith((".", "!", "?")):
        sentence += "."

    return sentence


if __name__ == "__main__":
    # Standalone Test Suite for Rule Verification
    print("[RUN] Running UZSL Dynamic Grammar Translator Self-Tests...\n")

    test_cases = [
        # 1. Base present continuous conjugations
        (["men", "do'kon", "bormoq"], "Men do'konga boryapman."),
        (["sen", "shifoxona", "kelmoq"], "Sen shifoxonaga kelyapsan."),
        (["u", "maktab", "bormoq"], "U maktabga boryapti."),
        (["biz", "bozor", "bormoq"], "Biz bozorga boryapmiz."),
        
        # 2. Case consonant harmony tests
        (["men", "bank", "bormoq"], "Men bankka boryapman."),
        (["men", "qishloq", "bormoq"], "Men qishloqqa boryapman."),
        (["men", "uy", "bormoq"], "Men uyga boryapman."),
        
        # 3. Transitive accusative object suffixes
        (["men", "suv", "ichmoq"], "Men suvni ichyapman."),
        (["biz", "non", "yemoq"], "Biz nonni yeyapmiz."),
        
        # 4. Past Tense Conjugations
        (["kecha", "men", "ish", "bormoq"], "Kecha men ishga bordim."),
        (["o'tgan", "biz", "maktab", "bormoq"], "O'tgan biz maktabga bordik."),
        
        # 5. Future Tense Conjugations
        (["ertaga", "sen", "uy", "kelmoq"], "Ertaga sen uyga kelmoqchisan."),
        (["keyin", "ular", "bozor", "bormoq"], "Keyin ular bozorga bormoqchilar."),

        # 6. Smart Negation (inkor) particle integrations
        (["men", "sut", "ichmoq", "yo'q"], "Men sutni ichmayapman."),
        (["kecha", "u", "uy", "kelmoq", "yo'q"], "Kecha u uyga kelmadi."),
        (["ertaga", "biz", "bozor", "bormoq", "yo'q"], "Ertaga biz bozorga bormoqchimasmiz."),

        # 7. Adjective / State Predication
        (["men", "yaxshi"], "Men yaxshiman."),
        (["biz", "xursand"], "Biz xursandmiz."),
        (["rahmat", "men", "yaxshi"], "Rahmat, men yaxshiman."),
        
        # 8. Place Predication (implicit locative + person)
        (["men", "do'kon"], "Men do'kondaman."),
        (["biz", "maktab"], "Biz maktabdamiz.")
    ]

    failed = 0
    for idx, (inp, expected) in enumerate(test_cases, 1):
        output = translate_uzsl_to_uzbek(inp)
        if output == expected:
            print(f"[PASS] Test {idx:02d}: {inp} -> '{output}'")
        else:
            print(f"[FAIL] Test {idx:02d}!")
            print(f"   Input:    {inp}")
            print(f"   Expected: '{expected}'")
            print(f"   Got:      '{output}'")
            failed += 1

    print(f"\n[DONE] Test Session Complete. Failed: {failed}/{len(test_cases)}")
