const Map<String, Map<String, String>> personalEndings = {
  "present_continuous": {
    "men": "man",
    "sen": "san",
    "u": "ti",
    "biz": "miz",
    "siz": "siz",
    "ular": "tilar"
  },
  "past": {
    "men": "m",
    "sen": "ng",
    "u": "",
    "biz": "k",
    "siz": "ngiz",
    "ular": "lar"
  },
  "future_intent": {
    "men": "man",
    "sen": "san",
    "u": "",
    "biz": "miz",
    "siz": "siz",
    "ular": "lar"
  },
  "predicate": {
    "men": "man",
    "sen": "san",
    "u": "",
    "biz": "miz",
    "siz": "siz",
    "ular": "lar"
  }
};

const Set<String> adjectives = {
  "yaxshi", "yomon", "charchagan", "kasal", "xursand",
  "tayyor", "band", "sog'", "baxtli", "tinch", "och", "to'q"
};

const Set<String> motionVerbs = {
  "bormoq", "kelmoq", "yugurmoq", "ketmoq", "kirmoq", "chiqmoq", "qaytmoq"
};

const Set<String> transitiveVerbs = {
  "ichmoq", "yemoq", "olmoq", "bermoq", "ko'rmoq", "yozmoq", "o'qimoq", "sotib olmoq"
};

const Set<String> places = {
  "uy", "do'kon", "shifoxona", "avtobus", "maktab", "bozor", "bank",
  "toshkent", "ish", "o'qish", "qishloq", "shahar", "bog'", "xona", "universitet"
};

const Set<String> objects = {
  "non", "suv", "sut", "pul", "kitob", "qalam", "choy", "ovqat", "koptok"
};

const Set<String> pastMarkers = {"kecha", "o'tgan", "avval", "burun"};
const Set<String> futureMarkers = {"ertaga", "keyin", "kelasi", "ertagaga"};

String getDativeSuffix(String word) {
  final clean = word.trim().toLowerCase();
  if (clean.isEmpty) return word;
  if (clean.endsWith('k')) {
    return '${word}ka';
  } else if (clean.endsWith('q')) {
    return '${word}qa';
  } else {
    return '${word}ga';
  }
}

String conjugateVerb(String verb, String pronoun, {String tense = "present_continuous", bool isNegative = false}) {
  final verbClean = verb.trim().toLowerCase();
  final parts = verbClean.split(' ');
  final conjugatePart = parts.last;
  if (!conjugatePart.endsWith('moq')) return verb;

  final stem = conjugatePart.substring(0, conjugatePart.length - 3);
  final negSuffix = isNegative ? "ma" : "";

  final endings = personalEndings[tense] ?? personalEndings["present_continuous"]!;
  final personalEnding = endings[pronoun] ?? endings["men"]!;

  if (tense == "present_continuous") {
    parts[parts.length - 1] = "$stem${negSuffix}yap$personalEnding";
    return parts.join(' ');
  } else if (tense == "past") {
    parts[parts.length - 1] = "$stem${negSuffix}di$personalEnding";
    return parts.join(' ');
  } else if (tense == "future_intent") {
    if (isNegative) {
      parts[parts.length - 1] = "${stem}moqchimas$personalEnding";
    } else {
      parts[parts.length - 1] = "${stem}moqchi$personalEnding";
    }
    return parts.join(' ');
  }
  return verb;
}

String conjugateAdjective(String adjective, String pronoun) {
  final endings = personalEndings["predicate"]!;
  final personalEnding = endings[pronoun] ?? "";
  return "$adjective$personalEnding";
}

String translateUzslToUzbek(List<String> words) {
  if (words.isEmpty) return "";
  final cleanedWords = words.map((w) => w.trim().toLowerCase()).where((w) => w.isNotEmpty).toList();
  if (cleanedWords.isEmpty) return "";

  // 1. Negation
  bool isNegative = false;
  if (cleanedWords.contains("yo'q")) {
    isNegative = true;
    cleanedWords.removeWhere((w) => w == "yo'q");
  }

  // 2. Tense
  String tense = "present_continuous";
  for (var w in cleanedWords) {
    if (pastMarkers.contains(w)) {
      tense = "past";
      break;
    } else if (futureMarkers.contains(w)) {
      tense = "future_intent";
      break;
    }
  }

  // 3. Subject
  const pronouns = {"men", "sen", "u", "biz", "siz", "ular"};
  String subject = "men";
  bool hasExplicitPronoun = false;
  for (var w in cleanedWords) {
    if (pronouns.contains(w)) {
      subject = w;
      hasExplicitPronoun = true;
      break;
    }
  }

  bool hasMotionVerb = cleanedWords.any((w) => motionVerbs.contains(w));
  bool hasTransitiveVerb = cleanedWords.any((w) => transitiveVerbs.contains(w));

  final List<String> resultWords = [];

  for (int idx = 0; idx < cleanedWords.length; idx++) {
    final w = cleanedWords[idx];

    // Pronouns
    if (pronouns.contains(w)) {
      if (w == subject && hasExplicitPronoun) {
        resultWords.add(idx == 0 ? w[0].toUpperCase() + w.substring(1) : w);
      }
      continue;
    }

    // Time markers
    if (pastMarkers.contains(w) || futureMarkers.contains(w)) {
      resultWords.add(idx == 0 ? w[0].toUpperCase() + w.substring(1) : w);
      continue;
    }

    // Verbs
    if (w.endsWith("moq")) {
      final conjugated = conjugateVerb(w, subject, tense: tense, isNegative: isNegative);
      resultWords.add(conjugated);
      continue;
    }

    // Adjectives
    if (adjectives.contains(w)) {
      final conjugated = conjugateAdjective(w, subject);
      resultWords.add(idx == 0 ? conjugated[0].toUpperCase() + conjugated.substring(1) : conjugated);
      continue;
    }

    // Places and Objects
    bool isLast = (idx == cleanedWords.length - 1);
    if (!isLast) {
      final nextWord = cleanedWords[idx + 1];
      if (motionVerbs.contains(nextWord) || hasMotionVerb) {
        if (places.contains(w)) {
          resultWords.add(getDativeSuffix(w));
          continue;
        }
      }
      if (transitiveVerbs.contains(nextWord) || hasTransitiveVerb) {
        if (objects.contains(w)) {
          resultWords.add("${w}ni");
          continue;
        }
      }
    }

    // Place predication
    if (places.contains(w)) {
      bool hasOtherPredicate = cleanedWords.any((word) => word.endsWith("moq") || adjectives.contains(word));
      if (!hasOtherPredicate && hasExplicitPronoun) {
        final endings = personalEndings["predicate"]!;
        final personalEnding = endings[subject] ?? "";
        resultWords.add("${w}da$personalEnding");
        continue;
      }
    }

    // Default
    resultWords.add(idx == 0 ? w[0].toUpperCase() + w.substring(1) : w);
  }

  if (resultWords.isEmpty) return "";
  var sentence = resultWords.join(' ');

  if (resultWords.length >= 2) {
    final first = resultWords[0].toLowerCase();
    if (first == "salom" || first == "rahmat" || first == "kechirasiz") {
      sentence = "${resultWords[0]}, ${resultWords.sublist(1).join(' ')}";
    }
  }

  if (!sentence.endsWith('.') && !sentence.endsWith('!') && !sentence.endsWith('?')) {
    sentence += '.';
  }
  return sentence;
}
