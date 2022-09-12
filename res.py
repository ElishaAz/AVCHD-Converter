import importlib
import sys
from typing import Dict

_languages = {
    'en': 'res_en',
    'he': 'res_he',
}
_default_lang = "en"

_res_attributes = {
    "strings": None,
    "rtl": False
}

strings: Dict[str, str]
rtl: bool

lang_set: bool = False


def __getattr__(name):
    if name in _res_attributes:
        set_lang(_default_lang)
        return getattr(sys.modules[__name__], name)
    raise AttributeError(f"module {__name__} has no attribute {name}")


def set_lang(lang: str):
    if lang in _languages:
        global lang_set
        module = importlib.import_module(_languages[lang])
        for attr, default in _res_attributes.items():
            setattr(sys.modules[__name__], attr, getattr(module, attr, default))
        lang_set = True
