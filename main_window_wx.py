import os.path
import subprocess
import threading
from typing import List, Optional

import wx
import wx.adv
import wx.lib.scrolledpanel

import tools
from avchd.decoder import Decoder
from avchd.playlist import Playlist
from stdout_decoder import StdOutDecoder

CODEC_NAMES = ["Copy", "Default", "GPU"]
CODECS = ["copy", None, "hevc_nvenc"]

VIDEO_FORMATS = "MPEG-4 (*.mp4; *.m4v)|*.mp4;*.m4v" + "|" + \
                "QuickTime (*.mov)|*.mov" + "|" + \
                "AVI (*.avi)|*.avi" + "|" + \
                "Matroska (*.mkv)|*.mkv" + "|" + \
                "Windows Media Video (*.wmv)|*.wmv"

MAX_LOG_LENGTH = 1000


# noinspection PyUnusedLocal
class MainWindow(wx.Frame):
    def toast(self, title, message):
        # notif = wx.adv.NotificationMessage(title=title, message=message, parent=self, flags=wx.ICON_ERROR)
        # notif.Show()
        # notif.Destroy()
        self.log(F"\nError: {title}: {message}")
        pass

    def log(self, line: str):
        with self.log_lock:
            self.current_log.print(line)
            if not self.update_log:
                self.update_log = True
                wx.CallAfter(self.update_log_in_ui)

    def update_log_in_ui(self):
        with self.log_lock:
            if self.update_log:
                self.label_log.Clear()
                self.label_log.AppendText(str(self.current_log))
                # self.log_panel.Scroll()
                self.update_log = False

    def run_command(self, command: List[str]):
        if self.process is not None and self.process.poll() is None:
            self.toast("Run Command", "Another command is running. Please end it first.")
            return
        self.log(F"Running command: '{' '.join(command)}':")
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.output_thread_stdout = threading.Thread(target=self.command_output_loop, args=[self.process, True])
        self.output_thread_stdout.start()
        self.output_thread_stderr = threading.Thread(target=self.command_output_loop, args=[self.process, False])
        self.output_thread_stderr.start()

    def command_output_loop(self, process: subprocess.Popen, stdout: bool):
        pipe = process.stdout if stdout else process.stderr
        while process.poll() is None:
            char = pipe.read(1)
            if char != b'':
                self.log(char.decode())
        rest = pipe.read()
        self.log(rest.decode())

    def __init__(self):
        super().__init__(parent=None, title='AVCHD Converter')
        self.playlist_paths: Optional[List[str]] = None
        self.playlist: Optional[Playlist] = None
        self.process: Optional[subprocess.Popen] = None
        self.output_thread_stdout: Optional[threading.Thread] = None
        self.output_thread_stderr: Optional[threading.Thread] = None

        self.log_lock = threading.Lock()
        self.update_log = False
        self.current_log = StdOutDecoder()

        self.Bind(wx.EVT_CLOSE, self.on_close)

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.label_title = wx.StaticText(panel, label="AVCHD Converter")
        main_sizer.Add(self.label_title, 0, wx.ALL | wx.LEFT, 5)

        cr_row = wx.BoxSizer(wx.HORIZONTAL)
        self.label_cr = wx.StaticText(panel, label="Content Root:")
        cr_row.Add(self.label_cr, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.text_cr = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER | wx.TE_LEFT)
        self.text_cr.Bind(wx.EVT_TEXT_ENTER, self.text_cr_enter)
        cr_row.Add(self.text_cr, 1, wx.ALL | wx.EXPAND, 1)
        self.browse_cr = wx.Button(panel, label="Browse")
        self.browse_cr.Bind(wx.EVT_BUTTON, self.browse_cr_pressed)
        cr_row.Add(self.browse_cr, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        main_sizer.Add(cr_row, 0, wx.ALL | wx.EXPAND, 4)

        pl_row = wx.BoxSizer(wx.HORIZONTAL)
        self.label_pl = wx.StaticText(panel, label="Playlist:")
        pl_row.Add(self.label_pl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.choice_pl = wx.Choice(panel, choices=[])
        self.choice_pl.Bind(wx.EVT_CHOICE, self.choice_pl_changed)
        pl_row.Add(self.choice_pl, 1, wx.ALL | wx.EXPAND, 1)
        main_sizer.Add(pl_row, 0, wx.ALL | wx.EXPAND, 4)

        sq_row = wx.BoxSizer(wx.HORIZONTAL)
        self.label_sq = wx.StaticText(panel, label="Sequence:")
        sq_row.Add(self.label_sq, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.choice_sq = wx.Choice(panel, choices=[])
        sq_row.Add(self.choice_sq, 1, wx.ALL | wx.EXPAND, 1)
        main_sizer.Add(sq_row, 0, wx.ALL | wx.EXPAND, 4)

        output_row = wx.BoxSizer(wx.HORIZONTAL)
        self.label_output = wx.StaticText(panel, label="Output File:")
        output_row.Add(self.label_output, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.text_output = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER | wx.TE_LEFT)
        output_row.Add(self.text_output, 1, wx.ALL | wx.EXPAND, 1)
        self.browse_output = wx.Button(panel, label="Browse")
        self.browse_output.Bind(wx.EVT_BUTTON, self.browse_output_pressed)
        output_row.Add(self.browse_output, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        main_sizer.Add(output_row, 0, wx.ALL | wx.EXPAND, 4)

        action_row = wx.BoxSizer(wx.HORIZONTAL)
        self.button_preview = wx.Button(panel, label='Preview')
        self.button_preview.Bind(wx.EVT_BUTTON, self.preview)
        action_row.Add(self.button_preview, 0, wx.ALL | wx.CENTER, 1)
        action_row.AddSpacer(10)

        self.label_codec = wx.StaticText(panel, label="Codec:")
        action_row.Add(self.label_codec, 0, wx.ALL | wx.CENTRE, 1)
        self.choice_codec = wx.Choice(panel, choices=CODEC_NAMES)
        self.choice_codec.SetSelection(0)
        action_row.Add(self.choice_codec, 1, wx.ALL | wx.EXPAND, 1)
        self.button_convert = wx.Button(panel, label="Convert")
        self.button_convert.Bind(wx.EVT_BUTTON, self.convert)
        action_row.Add(self.button_convert, 0, wx.ALL | wx.CENTRE, 1)
        main_sizer.Add(action_row, 0, wx.ALL | wx.EXPAND, 4)

        self.log_panel = wx.lib.scrolledpanel.ScrolledPanel(panel)
        log_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label_log = wx.TextCtrl(self.log_panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        font = wx.Font(10, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.label_log.SetFont(font)
        log_sizer.Add(self.label_log, 1, wx.ALL | wx.EXPAND, 5)
        self.log_panel.SetSizer(log_sizer)
        self.log_panel.SetupScrolling()
        self.log_panel.SetAutoLayout(True)
        main_sizer.Add(self.log_panel, 1, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(main_sizer)

        self.Show()

    def preview(self, event: wx.CommandEvent):
        if self.playlist_paths is None or self.playlist is None:
            self.toast("Preview", "No playlist selected!")
            return
        if self.choice_sq.GetSelection() == wx.NOT_FOUND:
            self.toast("Preview", "No sequence selected!")
            return
        sequence = self.playlist.sequences[self.choice_sq.GetSelection()]
        command = tools.preview_sequence(self.text_cr.GetValue(), sequence)
        self.run_command(command)

    def convert(self, event: wx.CommandEvent):
        if self.playlist_paths is None or self.playlist is None:
            self.toast("Convert", "No playlist selected!")
            return
        if self.choice_sq.GetSelection() == wx.NOT_FOUND:
            self.toast("Convert", "No sequence selected!")
            return
        if self.choice_codec.GetSelection() == wx.NOT_FOUND:
            self.toast("Convert", "No codec selected!")
            return
        file = self.text_output.GetValue()
        codec = CODECS[self.choice_codec.GetSelection()]
        if not os.path.exists(os.path.dirname(file)):
            self.toast("Convert", "Output path not valid!")
            return
        sequence = self.playlist.sequences[self.choice_sq.GetSelection()]
        command = tools.convert_sequence(self.text_cr.GetValue(), sequence, file, codec)
        self.run_command(command)

    def browse_cr_pressed(self, event: wx.CommandEvent):
        dlg = wx.DirDialog(None, "Choose content root directory", "", wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.text_cr.SetValue(dlg.GetPath())
        dlg.Destroy()
        self.text_cr_enter(None)

    def text_cr_enter(self, event):
        is_path = os.path.exists(self.text_cr.GetValue())
        self.playlist_paths = tools.get_playlists(self.text_cr.GetValue()) if is_path else None
        self.choice_pl.Clear()
        if is_path:
            self.choice_pl.AppendItems(self.playlist_paths)
        self.choice_pl.SetSelection(0 if is_path and len(self.playlist_paths) > 0 else wx.NOT_FOUND)

        self.choice_pl_changed(None)

    def choice_pl_changed(self, event):
        selection = self.choice_pl.GetSelection()
        self.playlist = None if selection is wx.NOT_FOUND else Decoder(self.playlist_paths[selection]).to_playlist()
        self.choice_sq.Clear()
        if selection is not wx.NOT_FOUND:
            self.choice_sq.AppendItems([str(s.date) for s in self.playlist.sequences])
        self.choice_sq.SetSelection(wx.NOT_FOUND if selection is wx.NOT_FOUND else 0)

        # self.choice_sq_changed(None)

    def browse_output_pressed(self, event: wx.CommandEvent):
        dlg = wx.FileDialog(self, "Output file", wildcard=VIDEO_FORMATS,
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.text_output.SetValue(dlg.GetPath())
        dlg.Destroy()

    def on_close(self, event: wx.CloseEvent):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            self.output_thread_stdout.join()
            self.output_thread_stderr.join()
        event.Skip()


def start():
    app = wx.App()
    frame = MainWindow()
    app.MainLoop()
