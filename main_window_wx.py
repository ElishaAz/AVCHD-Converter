import os.path
import subprocess
import threading
from typing import List, Optional, Tuple

import wx
import wx.adv
import wx.lib.scrolledpanel

import res
import tools
from avchd.decoder import Decoder
from avchd.playlist import Playlist
from stdout_decoder import StdOutDecoder
import signal

CODEC_NAMES = [res.strings["codec_name_copy"], res.strings["codec_name_default"], res.strings["codec_name_gpu"]]
CODECS = ["copy", None, "hevc_nvenc"]

TOAST_COLOR_ERROR: Tuple[int, int, int] = (255, 0, 0)
TOAST_COLOR_REGULAR: Tuple[int, int, int]

VIDEO_FORMATS = "MPEG-4 (*.mp4; *.m4v)|*.mp4;*.m4v" + "|" + \
                "QuickTime (*.mov)|*.mov" + "|" + \
                "AVI (*.avi)|*.avi" + "|" + \
                "Matroska (*.mkv)|*.mkv" + "|" + \
                "Windows Media Video (*.wmv)|*.wmv"

MAX_LOG_LENGTH = 1000

COMMAND_STOP_SIGNAL = signal.CTRL_C_EVENT if hasattr(signal, "CTRL_C_EVENT") else signal.SIGINT


# noinspection PyUnusedLocal
class MainWindow(wx.Frame):
    def toast(self, title=None, message=None, error=False):
        # notif = wx.adv.NotificationMessage(title=title, message=message, parent=self, flags=wx.ICON_ERROR)
        # notif.Show()
        # notif.Destroy()
        # self.log(F"\n{res.strings['error']}: {title}: {message}")
        text: str

        if title is None and message is None:
            text = ""
        elif message is None and title is not None:
            text = title
        elif message is not None and title is None:
            text = message
        else:
            text = F"{title}: {message}"

        self.label_toast.SetLabel(text)
        self.label_toast.SetForegroundColour(TOAST_COLOR_ERROR if error else TOAST_COLOR_REGULAR)
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
            self.toast(res.strings["toast_title_command"], res.strings["toast_message_command_already_running"],
                       error=True)
            return
        self.toast(res.strings['toast_title_command'], res.strings['toast_message_command_started'])
        self.log(F"Running command: '{' '.join(command)}':\n")
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
        if stdout:
            self.toast(res.strings['toast_title_command'], res.strings['toast_message_command_finished'])
            self.log("\nCommand Finished!")

    def stop_running_command(self, *args, **kwargs):
        if self.process is None or self.process.poll() is not None:
            return
        self.process.send_signal(COMMAND_STOP_SIGNAL)
        self.log("\nCommand manually stopped\n")
        self.toast(res.strings['toast_title_command'], res.strings['toast_message_command_stopped'])

    def __init__(self):
        super().__init__(parent=None, title=res.strings["title"])
        self.SetLayoutDirection(wx.Layout_RightToLeft if res.rtl else wx.Layout_LeftToRight)

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

        self.label_title = wx.StaticText(panel, label=res.strings["title"])
        main_sizer.Add(self.label_title, 0, wx.ALL | wx.LEFT, 5)

        cr_row = wx.BoxSizer(wx.HORIZONTAL)
        self.label_cr = wx.StaticText(panel, label=res.strings['content_root_label'])
        cr_row.Add(self.label_cr, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        # self.text_cr = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER | wx.TE_LEFT)
        # self.text_cr.Bind(wx.EVT_TEXT_ENTER, self.text_cr_enter)
        # cr_row.Add(self.text_cr, 1, wx.ALL | wx.EXPAND, 1)
        choices = self.combo_cr_choices()
        self.combo_cr = wx.ComboBox(panel, style=wx.CB_SORT | wx.TE_PROCESS_ENTER, choices=choices)
        self.combo_cr.Bind(wx.EVT_COMBOBOX, self.combo_cr_enter)
        self.combo_cr.Bind(wx.EVT_TEXT_ENTER, self.combo_cr_enter)
        # self.combo_cr.SetSize(wx.Size(max((len(c) for c in choices), default=-1), -1))
        cr_row.Add(self.combo_cr, 1, wx.ALL | wx.EXPAND, 1)
        self.browse_cr = wx.Button(panel, label=res.strings["browse_button"])
        self.browse_cr.Bind(wx.EVT_BUTTON, self.browse_cr_pressed)
        cr_row.Add(self.browse_cr, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        main_sizer.Add(cr_row, 0, wx.ALL | wx.EXPAND, 4)

        pl_row = wx.BoxSizer(wx.HORIZONTAL)
        self.label_pl = wx.StaticText(panel, label=res.strings['playlist_label'])
        pl_row.Add(self.label_pl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.choice_pl = wx.Choice(panel, choices=[])
        self.choice_pl.Bind(wx.EVT_CHOICE, self.choice_pl_changed)
        pl_row.Add(self.choice_pl, 1, wx.ALL | wx.EXPAND, 1)
        main_sizer.Add(pl_row, 0, wx.ALL | wx.EXPAND, 4)

        sq_row = wx.BoxSizer(wx.HORIZONTAL)
        self.label_sq = wx.StaticText(panel, label=res.strings['sequence_label'])
        sq_row.Add(self.label_sq, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.choice_sq = wx.Choice(panel, choices=[])
        sq_row.Add(self.choice_sq, 1, wx.ALL | wx.EXPAND, 1)
        main_sizer.Add(sq_row, 0, wx.ALL | wx.EXPAND, 4)

        output_row = wx.BoxSizer(wx.HORIZONTAL)
        self.label_output = wx.StaticText(panel, label=res.strings['output_file_label'])
        output_row.Add(self.label_output, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        self.text_output = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER | wx.TE_LEFT)
        output_row.Add(self.text_output, 1, wx.ALL | wx.EXPAND, 1)
        self.browse_output = wx.Button(panel, label=res.strings["browse_button"])
        self.browse_output.Bind(wx.EVT_BUTTON, self.browse_output_pressed)
        output_row.Add(self.browse_output, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 1)
        main_sizer.Add(output_row, 0, wx.ALL | wx.EXPAND, 4)

        action_row = wx.BoxSizer(wx.HORIZONTAL)
        self.button_preview = wx.Button(panel, label=res.strings['preview_button'])
        self.button_preview.Bind(wx.EVT_BUTTON, self.preview)
        action_row.Add(self.button_preview, 0, wx.ALL | wx.CENTER, 1)
        action_row.AddSpacer(10)

        self.label_codec = wx.StaticText(panel, label=res.strings['codec_label'])
        action_row.Add(self.label_codec, 0, wx.ALL | wx.CENTRE, 1)
        self.choice_codec = wx.Choice(panel, choices=CODEC_NAMES)
        self.choice_codec.SetSelection(0)
        action_row.Add(self.choice_codec, 1, wx.ALL | wx.EXPAND, 1)
        self.button_convert = wx.Button(panel, label=res.strings['convert_button'])
        self.button_convert.Bind(wx.EVT_BUTTON, self.convert)
        action_row.Add(self.button_convert, 0, wx.ALL | wx.CENTER, 1)
        main_sizer.Add(action_row, 0, wx.ALL | wx.EXPAND, 4)

        log_column = wx.BoxSizer(wx.VERTICAL)
        self.log_panel = wx.lib.scrolledpanel.ScrolledPanel(panel)
        log_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.label_log = wx.TextCtrl(self.log_panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        font = wx.Font(10, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.label_log.SetFont(font)
        log_sizer.Add(self.label_log, 1, wx.ALL | wx.EXPAND, 5)
        self.log_panel.SetSizer(log_sizer)
        self.log_panel.SetupScrolling()
        self.log_panel.SetAutoLayout(True)
        log_column.Add(self.log_panel, 1, wx.ALL | wx.EXPAND, 0)

        self.button_stop_command = wx.Button(panel, label=res.strings['stop_command_button'])
        self.button_stop_command.Bind(wx.EVT_BUTTON, self.stop_running_command)
        log_column.Add(self.button_stop_command, 0, wx.ALL | wx.EXPAND, 0)
        main_sizer.Add(log_column, 1, wx.ALL | wx.EXPAND, 5)

        self.label_toast = wx.StaticText(panel)
        global TOAST_COLOR_REGULAR
        TOAST_COLOR_REGULAR = self.label_toast.GetForegroundColour()
        main_sizer.Add(self.label_toast, 0, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(main_sizer)

        if len(choices) > 0:
            self.combo_cr.SetValue(choices[0])
            self.combo_cr_enter(None)

        self.SetSize(wx.Size(475, -1))

        self.Show()

    def preview(self, event: wx.CommandEvent):
        if self.playlist_paths is None or self.playlist is None:
            self.toast(res.strings['toast_title_preview'], res.strings['toast_message_no_playlist'], error=True)
            return
        if self.choice_sq.GetSelection() == wx.NOT_FOUND:
            self.toast(res.strings['toast_title_preview'], res.strings['toast_message_no_sequence'], error=True)
            return
        sequence = self.playlist.sequences[self.choice_sq.GetSelection()]
        command = tools.preview_sequence(self.combo_cr.GetValue(), sequence)
        self.run_command(command)

    def convert(self, event: wx.CommandEvent):
        if self.playlist_paths is None or self.playlist is None:
            self.toast(res.strings['toast_title_convert'], res.strings['toast_message_no_playlist'], error=True)
            return
        if self.choice_sq.GetSelection() == wx.NOT_FOUND:
            self.toast(res.strings['toast_title_convert'], res.strings['toast_message_no_sequence'], error=True)
            return
        if self.choice_codec.GetSelection() == wx.NOT_FOUND:
            self.toast(res.strings['toast_title_convert'], res.strings['toast_message_no_codec'], error=True)
            return
        file = self.text_output.GetValue()
        codec = CODECS[self.choice_codec.GetSelection()]
        if not os.path.exists(os.path.dirname(file)):
            self.toast(res.strings['toast_title_convert'], res.strings['toast_message_invalid_output'], error=True)
            return
        sequence = self.playlist.sequences[self.choice_sq.GetSelection()]
        command = tools.convert_sequence(self.combo_cr.GetValue(), sequence, file, codec)
        self.run_command(command)

    @staticmethod
    def combo_cr_choices() -> List[str]:
        drives = tools.external_drives()
        choices = []
        for d in drives:
            cr = tools.get_content_root(d)
            if cr is not None:
                choices.append(cr)
        return choices

    def browse_cr_pressed(self, event: wx.CommandEvent):
        dlg = wx.DirDialog(None, res.strings['dir_dialog_content_root'], "",
                           wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.combo_cr.SetValue(dlg.GetPath())
        dlg.Destroy()
        self.combo_cr_enter(None)

    def combo_cr_enter(self, event):
        is_path = os.path.exists(self.combo_cr.GetValue())
        self.playlist_paths = None
        if is_path:
            self.playlist_paths = tools.get_playlists(self.combo_cr.GetValue())
        if self.playlist_paths is None:
            is_path = False

        self.choice_pl.Clear()
        if is_path:
            self.choice_pl.AppendItems(self.playlist_paths)
        self.choice_pl.SetSelection(0 if is_path and len(self.playlist_paths) > 0 else wx.NOT_FOUND)

        self.choice_pl_changed(None)

    # def text_cr_enter(self, event):
    #     is_path = os.path.exists(self.text_cr.GetValue())
    #     self.playlist_paths = tools.get_playlists(self.text_cr.GetValue()) if is_path else None
    #     self.choice_pl.Clear()
    #     if is_path:
    #         self.choice_pl.AppendItems(self.playlist_paths)
    #     self.choice_pl.SetSelection(0 if is_path and len(self.playlist_paths) > 0 else wx.NOT_FOUND)
    #
    #     self.choice_pl_changed(None)

    def choice_pl_changed(self, event):
        selection = self.choice_pl.GetSelection()
        self.playlist = None if selection is wx.NOT_FOUND else Decoder(self.playlist_paths[selection]).to_playlist()
        self.choice_sq.Clear()
        if selection is not wx.NOT_FOUND:
            self.choice_sq.AppendItems([str(s.date) for s in self.playlist.sequences])
        self.choice_sq.SetSelection(wx.NOT_FOUND if selection is wx.NOT_FOUND else 0)

        self.toast(res.strings['toast_message_sequence_list_updated'])

        # self.choice_sq_changed(None)

    def browse_output_pressed(self, event: wx.CommandEvent):
        dlg = wx.FileDialog(self, res.strings['file_dialog_output_file'], wildcard=VIDEO_FORMATS,
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
