"""
Language normalization module.
Provides mapping from ISO codes, native names, and common aliases to standardized English display names.
"""


_LANGUAGE_MAP = {
    "English": ["en", "eng", "english"],
    "Spanish": ["es", "spa", "spanish", "español", "espanol"],
    "French": ["fr", "fra", "fre", "french", "français", "francais"],
    "German": ["de", "deu", "ger", "german", "deutsch"],
    "Italian": ["it", "ita", "italian", "italiano"],
    "Portuguese": ["pt", "por", "portuguese", "português", "portugues"],
    "Russian": ["ru", "rus", "russian", "русский", "russian"],
    "Japanese": ["ja", "jpn", "japanese", "日本語", "nihongo"],
    "Korean": ["ko", "kor", "korean", "한국어", "chosŏn'gŭl"],
    "Hindi": ["hi", "hin", "hindi", "हिन्दी"],
    "Arabic": ["ar", "ara", "arabic", "العربية", "اَلْعَرَبِيَّةُ"],
    "Mandarin": ["zh", "zho", "chi", "chinese", "mandarin", "中文", "汉语", "漢語"],
    "Cantonese": ["yue", "cantonese", "粵語", "粤语"],
    "Bengali": ["bn", "ben", "bengali", "বাংলা", "bangla"],
    "Punjabi": ["pa", "pan", "punjabi", "ਪੰਜਾਬੀ", "punjabi"],
    "Urdu": ["ur", "urd", "urdu", "اُردُو"],
    "Indonesian": ["id", "ind", "indonesian", "bahasa indonesia"],
    "Filipino": ["fil", "filipino", "tagalog", "tl", "tgl"],
    "Tamil": ["ta", "tam", "tamil", "தமிழ்"],
    "Telugu": ["te", "tel", "telugu", "తెలుగు"],
    "Malayalam": ["ml", "mal", "malayalam", "മലയാളം"],
    "Kannada": ["kn", "kan", "kannada", "ಕನ್ನಡ"],
    "Gujarati": ["gu", "guj", "gujarati", "ગુજરાતી"],
    "Marathi": ["mr", "mar", "marathi", "मराठी"],
    "Turkish": ["tr", "tur", "turkish", "türkçe", "turkce"],
    "Dutch": ["nl", "nld", "dut", "dutch", "nederlands"],
    "Polish": ["pl", "pol", "polish", "polski"],
    "Swedish": ["sv", "swe", "swedish", "svenska"],
    "Danish": ["da", "dan", "danish", "dansk"],
    "Norwegian": ["no", "nor", "norwegian", "norsk"],
    "Finnish": ["fi", "fin", "finnish", "suomi"],
    "Greek": ["el", "ell", "gre", "greek", "ελληνικά"],
    "Hebrew": ["he", "heb", "hebrew", "עברית"],
    "Thai": ["th", "tha", "thai", "ไทย"],
    "Vietnamese": ["vi", "vie", "vietnamese", "tiếng việt", "tieng viet"],
    "Malay": ["ms", "msa", "may", "malay", "bahasa melayu"],
    "Persian": ["fa", "fas", "per", "persian", "farsi", "فارسی"],
    "Swahili": ["sw", "swa", "swahili", "kiswahili"],
    "Zulu": ["zu", "zul", "zulu", "isizulu"],
    "Xhosa": ["xh", "xho", "xhosa", "isixhosa"],
    "Afrikaans": ["af", "afr", "afrikaans"],
    "Czech": ["cs", "ces", "cze", "czech", "čeština", "cestina"],
    "Hungarian": ["hu", "hun", "hungarian", "magyar"],
    "Romanian": ["ro", "ron", "rum", "romanian", "română", "romana"],
    "Bulgarian": ["bg", "bul", "bulgarian", "български"],
    "Serbian": ["sr", "srp", "serbian", "српски", "srpski"],
    "Croatian": ["hr", "hrv", "croatian", "hrvatski"],
    "Slovak": ["sk", "slk", "slo", "slovak", "slovenčina", "slovencina"],
    "Ukrainian": ["uk", "ukr", "ukrainian", "українська"],
    "Latin": ["la", "lat", "latin", "latina"],
    "Yoruba": ["yo", "yor", "yoruba", "èdè yorùbá"],
    "Sicilian": ["scn", "sicilian", "sicilianu"],
    "Basque": ["eu", "eus", "baq", "basque", "euskara"],
    "Armenian": ["hy", "hye", "arm", "armenian", "հայերեն"],
    "Mixtec": ["mix", "mixtec"],
    "Galician": ["gl", "glg", "galician", "galego"],
    "Dari": ["prs", "dari", "دری"],
    "Estonian": ["et", "est", "estonian", "eesti"],
    "Wolof": ["wo", "wol", "wolof"],
    "Quechua": ["qu", "que", "quechua", "runa simi"],
    "Corsican": ["co", "cos", "corsican", "corsu"],
    "Yiddish": ["yi", "yid", "yiddish", "ייִדיש"],
    "Maya": ["myn", "maya", "mayan"],
    "Hawaiian": ["haw", "hawaiian", "ʻōlelo hawaiʻi"],
    "Flemish": ["vls", "flemish", "vlaams"],
    "Rajasthani": ["raj", "rajasthani", "राजस्थानी"],
    "Haryanvi": ["bgc", "haryanvi", "हरियाणवी"],
    "Catalan": ["ca", "cat", "catalan", "català", "catala"],
    "Sign Language": ["sgn", "sign language", "sign languages", "american sign language", "korean sign language"]
}


_LOOKUP_MAP = {}
for standard_name, variations in _LANGUAGE_MAP.items():
    for var in variations:
        _LOOKUP_MAP[var.lower()] = standard_name

def normalize_language(lang_string: str) -> str:
    """
    Normalizes a language string (e.g. 'en', 'Español', 'hin') to a standardized English name.
    If the language is unknown or cannot be normalized, it returns the capitalized input.
    """
    if not lang_string:
        return "Unknown"
    
    clean_lang = lang_string.strip().lower()
    
    
    if clean_lang in _LOOKUP_MAP:
        return _LOOKUP_MAP[clean_lang]
    
    
    return lang_string.strip().capitalize()
