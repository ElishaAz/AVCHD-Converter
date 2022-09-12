import sys

import res

if __name__ == '__main__':
    set_lang = False
    for a, b in zip(sys.argv, sys.argv[1:]):
        if a == "--lang":
            res.set_lang(b)
            set_lang = True
    if not set_lang:
        res.set_lang("en")

    import main_window_wx

    main_window_wx.start()
