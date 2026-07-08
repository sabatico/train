"""Sourced raw word inventory, per phonics pattern (the corpus).

Assembled 2026-07-08 from public phonics/word-list resources (see SOURCES below),
cleaned: lowercased, proper nouns removed, deduped. This is the RAW input; the
schema fields (phonemes, difficulty, distractors) are computed by
`scripts/build_wordbanks.py`, and phrase/sentence/emoji are enriched by AI later.

SOURCES:
  short_vowels — cvc-words.com, literacylearn.com (CVC families)
  magic_e      — search corpora (tejedastots, superteacherworksheets, games4esl) + curated long o/u/e
  vowel_teams  — weareteachers.com/vowel-team-words
  r_controlled — literacylearn.com/150-r-controlled-vowel-words
  digraphs     — curated (sh/ch/th/wh/ck common words)
  blends       — curated (standard onset/coda blends)
  doubling_endings, suffixes, heart_words — curated (Dolch/Fry irregulars)
"""

RAW: dict[str, list[str]] = {
    "short_vowels": [
        # a
        "bad", "bag", "bat", "cap", "cat", "dad", "fan", "fat", "gap", "ham", "hat",
        "jam", "lap", "mad", "man", "map", "nap", "pan", "pat", "rag", "ran", "rat",
        "sad", "sat", "tag", "tap", "van", "wag", "yam", "zap",
        # e
        "bed", "beg", "bet", "den", "fed", "get", "hem", "hen", "jet", "led", "leg",
        "let", "men", "met", "net", "peg", "pen", "pet", "red", "set", "ten", "web", "wet", "yes",
        # i
        "big", "bin", "bit", "dig", "dim", "dip", "fin", "fit", "hip", "hit", "kid",
        "kit", "lid", "lip", "lit", "mix", "pig", "pin", "pit", "rib", "rip", "sip",
        "sit", "tin", "tip", "wig", "win", "zip", "six", "fix",
        # o
        "bog", "box", "cob", "cod", "cop", "cot", "dog", "dot", "fog", "fox", "got",
        "hop", "hot", "job", "jog", "log", "lot", "mob", "mop", "nod", "not", "pod",
        "pop", "pot", "rob", "rod", "rot", "sob", "top",
        # u
        "bug", "bun", "bus", "but", "cup", "cut", "dug", "fun", "gum", "gun", "gut",
        "hug", "hum", "hut", "jug", "mud", "mug", "nut", "pup", "run", "rug", "sub",
        "sun", "tub", "tug",
    ],
    "digraphs": [
        "ship", "shop", "shed", "shin", "shell", "fish", "wish", "cash", "dash",
        "rush", "brush", "trash", "fresh", "shut",
        "chat", "chip", "chin", "chop", "chest", "chick", "much", "rich", "such",
        "lunch", "bench", "munch", "chill",
        "thin", "that", "this", "then", "them", "with", "bath", "path", "moth",
        "cloth", "thick", "thump",
        "when", "whip", "whiz", "which", "whim",
        "duck", "sock", "rock", "lock", "kick", "pick", "sick", "back", "pack",
        "neck", "deck", "truck", "black", "clock", "stick", "quick",
    ],
    "magic_e": [
        "bake", "cake", "fake", "lake", "make", "rake", "take", "wake", "came",
        "fame", "game", "name", "same", "tame", "cape", "tape", "base", "case",
        "cave", "gave", "save", "wave", "made", "shade", "trade", "late", "gate",
        "hate", "rate", "date", "mate", "skate", "plate", "place", "space", "face",
        "race", "grade",
        "bike", "hike", "like", "dime", "lime", "time", "dine", "fine", "line",
        "mine", "nine", "pine", "vine", "wine", "bite", "kite", "site", "dive",
        "five", "hive", "ride", "hide", "side", "wide", "slide", "bride", "pride",
        "file", "mile", "pile", "smile", "tile", "fire", "hire", "tire", "wire",
        "ice", "dice", "mice", "nice", "rice",
        "bone", "cone", "hole", "home", "hope", "nose", "note", "rope", "rose",
        "stone", "drove", "stove", "close", "woke", "joke", "poke", "smoke", "code",
        "cube", "cute", "tube", "tune", "mute", "huge", "rude", "rule", "flute",
    ],
    "vowel_teams": [
        "wait", "paint", "train", "gain", "chain", "braid", "snail", "grain",
        "plain", "aim", "fail", "aid", "laid", "rain", "brain", "drain", "main",
        "pain", "sail", "tail", "mail", "nail", "trail",
        "day", "say", "pay", "may", "ray", "way", "clay", "gray", "play", "spray",
        "stray", "tray", "stay", "hay",
        "need", "keep", "sheep", "queen", "speed", "sleep", "street", "sweet",
        "feet", "teeth", "green", "meet", "seem", "tree", "three", "free", "week",
        "teach", "beach", "team", "eat", "mean", "leaf", "bead", "sea", "read", "meal",
        "high", "night", "might", "light", "bright", "fight", "flight", "tight",
        "boat", "soap", "float", "goat", "road", "coat", "toast", "coach", "goal", "load",
        "coin", "join", "oil", "boil", "soil", "point", "spoil",
        "boy", "joy", "toy", "enjoy",
        "moon", "soon", "room", "food", "cool", "pool", "tooth", "boot", "zoo",
        "book", "look", "took", "good", "foot", "wood", "hook",
        "out", "loud", "found", "round", "sound", "mouth", "house", "cloud",
        "down", "town", "cow", "now", "how", "owl",
        "snow", "grow", "show", "slow", "blow", "low", "glow",
        "saw", "claw", "draw", "paw", "law", "yawn", "jaw",
    ],
    "r_controlled": [
        "car", "bar", "far", "part", "hard", "start", "arm", "jar", "dark", "farm",
        "star", "yard", "spark", "yarn", "party", "cart", "sharp", "chart", "barn", "scarf",
        "her", "herd", "fern", "term", "germ", "clerk", "jerk", "stern", "serve",
        "nerve", "butter", "sister", "ever", "person", "perfect", "expert", "verb",
        "bird", "girl", "first", "third", "sir", "shirt", "dirt", "birth", "firm",
        "stir", "skirt", "twirl", "dirty", "thirty", "circle", "thirsty",
        "corn", "for", "born", "north", "horse", "torn", "short", "sort", "storm",
        "force", "horn", "form", "order", "corner", "story", "morning", "fork", "sport",
        "nurse", "turn", "fur", "hurt", "church", "purse", "burst", "burn", "curve",
        "curl", "surf", "blur", "turkey", "purple", "turtle", "return", "curb",
    ],
    "blends": [
        "stop", "step", "stem", "stamp", "stand", "spin", "spot", "spill", "snap",
        "sled", "slip", "slim", "swim", "skip", "skin", "scan", "smell", "snack",
        "crab", "crib", "drum", "drop", "frog", "grab", "grin", "trap", "trip",
        "brick", "bring", "print", "plan", "plug", "clap", "clip", "flag", "flat",
        "glad", "block", "clam", "crop", "grass", "press", "dress", "twin",
        "hand", "land", "band", "sand", "bend", "send", "pond", "wind", "jump",
        "lamp", "camp", "bump", "tent", "hunt", "mint", "nest", "best", "fast",
        "last", "list", "must", "milk", "silk", "belt", "melt", "gift", "soft",
        "pink", "sink", "wink", "bank", "junk", "desk", "mask",
    ],
    "doubling_endings": [
        "off", "puff", "cuff", "cliff", "stuff", "sniff",
        "ball", "call", "fall", "tall", "wall", "bell", "fell", "tell", "well",
        "sell", "yell", "hill", "will", "fill", "bill", "pill", "spill", "doll", "roll",
        "pass", "mess", "less", "kiss", "miss", "boss", "loss", "dress", "grass", "class",
        "buzz", "fuzz", "jazz", "fizz", "egg", "add",
    ],
    "suffixes": [
        "cats", "dogs", "pigs", "cups", "hats", "beds", "pins",
        "jumps", "runs", "sits", "digs", "hops",
        "jumping", "running", "playing", "eating", "reading", "singing", "helping",
        "jumped", "played", "helped", "wanted", "landed", "planted",
        "boxes", "wishes", "dishes", "buses", "foxes",
        "faster", "bigger", "taller", "smaller", "longer",
    ],
    "heart_words": [
        "the", "of", "to", "you", "was", "said", "are", "they", "have", "one",
        "two", "who", "what", "where", "there", "here", "were", "does", "come",
        "some", "gone", "could", "would", "should", "put", "pull", "full", "been",
        "from", "want", "water", "love", "give", "live", "move", "done", "once",
        "only", "people", "because", "friend", "again", "any", "many", "eye",
        "buy", "your", "very", "every", "little", "know", "your", "walk", "talk",
    ],
}
