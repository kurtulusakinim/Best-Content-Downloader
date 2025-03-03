import sys
import os
import re
import subprocess
import threading
import yt_dlp

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QGroupBox, QProgressBar, QPushButton, QMessageBox, QMainWindow, QAction, QDialog
)


class YouTubeDownloader(QMainWindow):
    detailsFetched = pyqtSignal(dict)
    errorOccurred = pyqtSignal(str)
    progressUpdated = pyqtSignal(int)
    downloadSuccess = pyqtSignal()
    downloadReset = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Best Content Downloader v0.1.0")
        self.setFixedSize(500, 300)

        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_path, "icon.ico")
        self.setWindowIcon(QIcon(icon_path))

        self.running = False
        self.current_info = None

        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        self.downloads_path = os.path.join(application_path, 'downloads')
        os.makedirs(self.downloads_path, exist_ok=True)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.create_widgets()
        self.create_menu()

        self.detailsFetched.connect(self.update_ui_with_details)
        self.errorOccurred.connect(self.handle_title_error)
        self.progressUpdated.connect(self.progress_bar_set_value)
        self.downloadSuccess.connect(self.show_download_success)
        self.downloadReset.connect(self.reset_ui)

        self.check_dependencies()

    def create_widgets(self):    

        # URL
        url_layout = QHBoxLayout()
        url_label = QLabel("URL:")
        self.url_lineedit = QLineEdit()
        self.url_lineedit.setPlaceholderText("Video URL")
        self.url_lineedit.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_lineedit)
        self.main_layout.addLayout(url_layout)

        # Video Name
        name_layout = QHBoxLayout()
        name_label = QLabel("Video Name:")
        self.video_name_lineedit = QLineEdit()
        self.video_name_lineedit.setPlaceholderText("Video Name")
        self.video_name_lineedit.setEnabled(False)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.video_name_lineedit)
        self.main_layout.addLayout(name_layout)

        # (Video / Audio)
        media_group = QGroupBox(" Media Type ")
        media_layout = QHBoxLayout()
        self.video_radio = QRadioButton("🎥 Video")
        self.video_radio.setChecked(True)
        self.music_radio = QRadioButton("🎵 Audio")
        media_layout.addWidget(self.video_radio)
        media_layout.addWidget(self.music_radio)
        media_group.setLayout(media_layout)
        self.main_layout.addWidget(media_group)

        # (Full / Partial)
        range_group = QGroupBox(" Download Range ")
        range_layout = QHBoxLayout()
        self.full_radio = QRadioButton("📦 Full")
        self.full_radio.setChecked(True)
        self.partial_radio = QRadioButton("✄ Partial")
        self.full_radio.toggled.connect(self.toggle_time_fields)
        self.partial_radio.toggled.connect(self.toggle_time_fields)
        range_layout.addWidget(self.full_radio)
        range_layout.addWidget(self.partial_radio)
        range_group.setLayout(range_layout)
        self.main_layout.addWidget(range_group)

        # Timestamps
        time_layout = QHBoxLayout()
        start_label = QLabel("Start (SS/HH:MM:SS):")
        self.start_lineedit = QLineEdit()
        self.start_lineedit.setFixedWidth(100)
        self.start_lineedit.setEnabled(False)
        end_label = QLabel("End (SS/HH:MM:SS):")
        self.end_lineedit = QLineEdit()
        self.end_lineedit.setFixedWidth(100)
        self.end_lineedit.setEnabled(False)
        time_layout.addWidget(start_label)
        time_layout.addWidget(self.start_lineedit)
        time_layout.addWidget(end_label)
        time_layout.addWidget(self.end_lineedit)
        self.main_layout.addLayout(time_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.main_layout.addWidget(self.progress_bar)

        # Download Button
        self.download_button = QPushButton("⏬ Start Download")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.start_download_thread)
        self.main_layout.addWidget(self.download_button)

    def create_menu(self):
        menubar = self.menuBar()
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        menubar.addAction(about_action)

    def show_about(self):
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("About")

        about_dialog.setFixedSize(250, 150)
        flags = about_dialog.windowFlags()
        flags = flags & ~Qt.WindowContextHelpButtonHint 
        about_dialog.setWindowFlags(flags | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        layout = QVBoxLayout()
        
        title_font = QFont("Times New Roman", 15)
        label_title = QLabel("Best Content Downloader")
        label_title.setFont(title_font)
        label_title.setAlignment(Qt.AlignCenter)

        label_subtitle = QLabel("A multi-platform content downloader GUI\n\nVersion: 0.1.0")

        label_subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(label_title)
        layout.addWidget(label_subtitle)

        label_link = QLabel("<a href='https://github.com/kurtulusakinim'>GitHub: kurtulusakinim</a>")
        label_link.setOpenExternalLinks(True)
        label_link.setAlignment(Qt.AlignCenter)
        layout.addWidget(label_link)

        about_dialog.setLayout(layout)

        about_dialog.exec_()


    def check_dependencies(self):
        """FFmpeg checking"""
        try:
            subprocess.run(['ffmpeg', '-version'], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            QMessageBox.critical(self, "Error", "FFmpeg not found!")
            print("what")
            QApplication.quit()

    def on_url_changed(self, text):
        self.download_button.setEnabled(False)
        url = text.strip()
        self.set_fetching_state()
        threading.Thread(target=self.fetch_video_details, args=(url,), daemon=True).start()

    def set_fetching_state(self):
        self.video_name_lineedit.setEnabled(True)
        self.video_name_lineedit.setText("Fetching...")
        self.video_name_lineedit.setEnabled(False)

    def fetch_video_details(self, url):
        try:
            opts = {
                'noprogress': True,
                'format': (
                    #'bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/'
                    #'bestvideo[ext=mp4][height<=1440]+bestaudio[ext=m4a]/'
                    #'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/'
                    #'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/'
                    'best/bestvideo[vcodec^=avc1]'
                ),
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.current_info = info
                self.detailsFetched.emit(info)
        except Exception as e:
            self.errorOccurred.emit(str(e))

    def update_ui_with_details(self, info):
        title = info.get('title', 'Unknown Video')
        self.video_name_lineedit.setEnabled(True)
        self.video_name_lineedit.setText(title)
        self.video_name_lineedit.setCursorPosition(len(title))

        self.download_button.setEnabled(True)
        duration = info.get('duration', 0)
        print(f"Video Duration: {duration} seconds")
        print(f"Channel: {info.get('uploader', 'Unknown Channel')}")

    def handle_title_error(self, error_message):
        self.video_name_lineedit.setText("")
        self.download_button.setEnabled(False)

    def progress_bar_set_value(self, value):
        self.progress_bar.setValue(value)

    def show_download_success(self):
        QMessageBox.information(self, "Success", "Download completed!")

    def reset_ui(self):
        self.download_button.setEnabled(True)
        self.progress_bar.setValue(0)

    def sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

    def get_unique_filename(self, base_name, ext):
        if not os.path.exists(os.path.join(self.downloads_path, f"{base_name}.{ext}")):
            return f"{base_name}.{ext}"

        existing_files = set()
        pattern = re.compile(rf"^{re.escape(base_name)}_(\d+)\.{re.escape(ext)}$")
        for f in os.listdir(self.downloads_path):
            match = pattern.match(f)
            if match:
                existing_files.add(int(match.group(1)))

        expected_num = 1
        while True:
            if expected_num not in existing_files:
                return f"{base_name}_{expected_num}.{ext}"
            expected_num += 1

    def toggle_time_fields(self):
        state = self.partial_radio.isChecked()
        self.start_lineedit.setEnabled(state)
        self.end_lineedit.setEnabled(state)

    def parse_time(self, time_str):
        try:
            parts = list(map(int, time_str.split(':')))
            multipliers = [1, 60, 3600]
            return sum(part * mult for part, mult in zip(reversed(parts), multipliers))
        except Exception:
            return None

    def start_download_thread(self):
        if self.running:
            return
        self.running = True
        # İndirme başlarken buton pasif olsun
        self.download_button.setEnabled(False)
        self.progress_bar.setValue(0)
        threading.Thread(target=self.start_download, daemon=True).start()

    def update_progress(self, d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes']:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            elif 'fragment_index' in d and 'fragment_count' in d:
                percent = (d['fragment_index'] / d['fragment_count']) * 100
            else:
                percent = 0
            self.progressUpdated.emit(int(percent))
        elif d['status'] == 'finished':
            self.progressUpdated.emit(100)

    def get_ydl_options(self):
        custom_name = self.video_name_lineedit.text().strip()
        original_title = custom_name if custom_name else '%(title)s'
        ext = 'mp3' if self.music_radio.isChecked() else 'mp4'
        base_name = self.sanitize_filename(original_title)
        final_filename = self.get_unique_filename(base_name, ext)

        opts = {
            'outtmpl': os.path.join(self.downloads_path, final_filename),
            'progress_hooks': [self.update_progress],
            'noprogress': True,
        }

        if self.music_radio.isChecked():
            final_filename = self.get_unique_filename(base_name, 'mp3').replace('.mp3', '')
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'outtmpl': os.path.join(self.downloads_path, final_filename)
            })
        else:
            opts['format'] = (
                'bestvideo[ext=mp4][height<=2160][vcodec^=avc1]+bestaudio[ext=m4a]/'
                'bestvideo[ext=mp4][height<=1440][vcodec^=avc1]+bestaudio[ext=m4a]/'
                'bestvideo[ext=mp4][height<=1080][vcodec^=avc1]+bestaudio[ext=m4a]/'
                'bestvideo[ext=mp4][height<=720][vcodec^=avc1]+bestaudio[ext=m4a]/best'
            )

        if self.partial_radio.isChecked():
            start = self.parse_time(self.start_lineedit.text())
            end = self.parse_time(self.end_lineedit.text())
            if start is None or end is None or start >= end:
                raise ValueError("Invalid time range")
            opts.update({
                'external_downloader': 'ffmpeg',
                'external_downloader_args': {
                    'ffmpeg_i': ['-ss', str(start), '-to', str(end)],
                    'ffmpeg': ['-c:v', 'copy', '-c:a', 'copy']
                }
            })

        return opts

    def start_download(self):
        url = self.url_lineedit.text().strip()
        try:
            if not url:
                raise ValueError("Please enter a YouTube URL")

            opts = self.get_ydl_options()

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = self.current_info
                print("Downloading..")

                if self.partial_radio.isChecked():
                    duration = info.get('duration', 0)
                    start = self.parse_time(self.start_lineedit.text())
                    end = self.parse_time(self.end_lineedit.text())
                    if end > duration:
                        raise ValueError("End time exceeds video duration")

                if self.music_radio.isChecked():
                    ydl.download([url])
                else:
                    ydl.process_ie_result(info, download=True)
                print("Download completed successfully!")
            self.downloadSuccess.emit()
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            self.errorOccurred.emit(error_msg)
        finally:
            self.running = False
            self.downloadReset.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeDownloader()
    window.show()
    sys.exit(app.exec_())
