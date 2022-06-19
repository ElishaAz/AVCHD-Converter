import PySimpleGUI as sg

import tools
from avchd.decoder import Decoder

PLYER = True
try:
    import plyer
except ModuleNotFoundError:
    PLYER = False


def browse(key):
    return sg.Button('Browse', key=key) if PLYER else sg.FolderBrowse(key=key)


class MainWindow:
    def __init__(self):
        self.layout = \
            [
                [sg.Text('AVHD Converter')],
                [sg.Text('Content Root'), sg.Input(key="_CR_INPUT_", enable_events=True), browse("_CR_BROWSE_")],
                [sg.Text("Playlist"), sg.Combo([""], enable_events=True, key='_PL_COMBO_', readonly=True)],
                [sg.Text("Sequence"), sg.Combo([""], enable_events=True, key='_SQ_COMBO_', readonly=True)],
                [sg.Button("Preview", key="_AC_PREVIEW_")]
            ]
        self.window = sg.Window('File Compare', self.layout)

    def show(self):
        self.window.Finalize()
        cr_updated = False
        pl_updated = False
        self.window['_PL_COMBO_'].expand(True)
        self.window['_SQ_COMBO_'].expand(True)
        playlist = None

        while True:
            event, values = self.window.read()
            if event is None:
                print(F"content root: {self.window['_CR_INPUT_'].get()}")
                self.window.close()
                break

            if PLYER and event == "_CR_BROWSE_":
                directory = plyer.filechooser.choose_dir()[0]
                self.window["_CR_INPUT_"].Update(directory)
                values["_CR_INPUT_"] = directory
                cr_updated = True

            if event == "_CR_INPUT_" or cr_updated:
                if values["_CR_INPUT_"] != "":
                    cr_updated = False

                    content_root = values['_CR_INPUT_']

                    playlists = tools.get_playlists(content_root)
                    print(content_root, values, playlists)
                    val = playlists[0] if len(playlists) > 0 else ""
                    self.window['_PL_COMBO_'].Update(value=val, values=playlists)
                else:
                    self.window['_PL_COMBO_'].Update(value="", values=[""])
                pl_updated = True

            if event == "_PL_COMBO_" or pl_updated:
                if values["_PL_COMBO_"] != "":
                    playlist = Decoder(values['_PL_COMBO_']).to_playlist()
                    self.window['_SQ_COMBO_'].Update(value=str(playlist.sequences[0].date),
                                                     values=[str(x.date) for x in playlist.sequences])
                else:
                    playlist = None
                    self.window['_SQ_COMBO_'].Update(value="", values=[""])

            if event == "_AC_PREVIEW_" and playlist is not None:
                sequence_index = [str(x.date) for x in playlist.sequences].index(values['_SQ_COMBO_'])
                tools.preview_sequence(values['_CR_INPUT_'], playlist.sequences[sequence_index])

if __name__ == '__main__':
    window = MainWindow()
    window.show()