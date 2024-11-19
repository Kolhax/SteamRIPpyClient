import sys
import json
import os
import zipfile
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QListWidget, QTextEdit, QLabel, 
                             QMessageBox, QProgressBar, QSplitter, QFrame, QScrollArea,
                             QFileDialog, QInputDialog, QComboBox)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import requests
from io import BytesIO
import megadbdl

class DownloadThread(QThread):
    progress_update = pyqtSignal(int)
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192  # 8 KB
            with open(self.save_path, 'wb') as file:
                downloaded = 0
                for data in response.iter_content(block_size):
                    size = file.write(data)
                    downloaded += size
                    if total_size > 0:
                        self.progress_update.emit(int(downloaded / total_size * 100))
            self.download_complete.emit(self.save_path)
        except Exception as e:
            self.download_error.emit(str(e))

class GameSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MegaDB Game Downloader")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('game_icon.png'))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.setup_ui()

        self.json_file = 'game_list.json'
        self.games = self.load_game_list(self.json_file)
        self.populate_game_list()

        self.download_thread = None
        self.current_game = None
        self.captcha_key = None

    def setup_ui(self):
        # Captcha key input
        self.captcha_key_button = QPushButton("Set 2Captcha API Key")
        self.captcha_key_button.clicked.connect(self.set_captcha_key)
        self.layout.addWidget(self.captcha_key_button)

        # Search bar
        self.search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for games...")
        self.search_layout.addWidget(self.search_input)

        # Drive selection
        self.drive_combo = QComboBox()
        self.drive_combo.addItems(self.get_available_drives())
        self.search_layout.addWidget(self.drive_combo)

        # Game list and info
        self.splitter = QSplitter(Qt.Horizontal)
        self.game_list = QListWidget()
        self.game_list.setFrameShape(QFrame.StyledPanel)
        
        self.info_scroll = QScrollArea()
        self.info_scroll.setWidgetResizable(True)
        self.info_widget = QWidget()
        self.info_layout = QVBoxLayout(self.info_widget)
        
        self.game_image = QLabel()
        self.game_image.setAlignment(Qt.AlignCenter)
        self.info_layout.addWidget(self.game_image)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFrameShape(QFrame.StyledPanel)
        self.info_layout.addWidget(self.info_text)
        
        self.screenshots_layout = QHBoxLayout()
        self.info_layout.addLayout(self.screenshots_layout)
        
        self.download_button = QPushButton("Download and Install Game")
        self.download_button.clicked.connect(self.download_game)
        self.info_layout.addWidget(self.download_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.info_layout.addWidget(self.progress_bar)
        
        self.info_scroll.setWidget(self.info_widget)
        
        self.splitter.addWidget(self.game_list)
        self.splitter.addWidget(self.info_scroll)
        self.splitter.setSizes([400, 800])

        # Add widgets to main layout
        self.layout.addLayout(self.search_layout)
        self.layout.addWidget(self.splitter)

        # Connect signals
        self.search_input.textChanged.connect(self.filter_games)
        self.game_list.itemClicked.connect(self.show_game_info)

    def get_available_drives(self):
        return [f"{d}:" for d in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:")]

    def set_captcha_key(self):
        key, ok = QInputDialog.getText(self, "2Captcha API Key", "Enter your 2Captcha API key:")
        if ok and key:
            self.captcha_key = key
            QMessageBox.information(self, "API Key Set", "2Captcha API key has been set successfully.")

    @staticmethod
    def load_game_list(json_file):
        if os.path.exists(json_file):
            with open(json_file, 'r') as file:
                return json.load(file)
        else:
            return {}

    def populate_game_list(self):
        self.game_list.clear()
        for game in sorted(self.games.keys()):
            self.game_list.addItem(game)

    def filter_games(self):
        search_term = self.search_input.text().lower()
        for i in range(self.game_list.count()):
            item = self.game_list.item(i)
            item.setHidden(search_term not in item.text().lower())

    def show_game_info(self, item):
        game_name = item.text()
        self.current_game = game_name
        game_info = self.games[game_name]

        # Set game image
        pixmap = QPixmap()
        pixmap.loadFromData(requests.get(game_info['banner_url']).content)
        self.game_image.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.game_image.setMaximumSize(300, 300)

        # Prepare info text
        info_text = f"<h2>{game_name}</h2>"
        info_text += f"<p>{game_info['text_content']}</p>"
        info_text += "<h3>System Requirements:</h3><pre>{}</pre>".format(game_info['system_requirements'])
        info_text += "<h3>Game Info:</h3><pre>{}</pre>".format(game_info['game_info'])

        self.info_text.setHtml(info_text)

        # Clear previous screenshots
        for i in reversed(range(self.screenshots_layout.count())): 
            self.screenshots_layout.itemAt(i).widget().setParent(None)

        # Load and display screenshots
        for screenshot_url in game_info['screenshots'][:4]:  # Limit to 4 screenshots
            try:
                response = requests.get(screenshot_url)
                response.raise_for_status()
                img_data = BytesIO(response.content)
                pixmap = QPixmap()
                pixmap.loadFromData(img_data.getvalue())
                scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label = QLabel()
                label.setPixmap(scaled_pixmap)
                label.setAlignment(Qt.AlignCenter)
                self.screenshots_layout.addWidget(label)
            except Exception as e:
                print(f"Error loading screenshot: {e}")

    def download_game(self):
        if not self.captcha_key:
            QMessageBox.warning(self, "No Captcha Key", "Please set your 2Captcha API key before downloading.")
            return

        if not self.current_game:
            QMessageBox.warning(self, "No Game Selected", "Please select a game to download.")
            return

        selected_drive = self.drive_combo.currentText()
        if not selected_drive:
            QMessageBox.warning(self, "No Drive Selected", "Please select a drive for download.")
            return

        game_info = self.games[self.current_game]
        megadb_url = self.get_megadb_link(game_info)
        if not megadb_url:
            QMessageBox.warning(self, "No MegaDB Link", "No MegaDB download link available for this game.")
            return

        try:
            download_url = megadbdl.retrieve_download_url(self.captcha_key, megadb_url)
        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"Failed to retrieve download URL: {str(e)}")
            return

        game_folder = os.path.join(selected_drive, self.current_game)
        os.makedirs(game_folder, exist_ok=True)
        save_path = os.path.join(game_folder, f"{self.current_game}.zip")

        self.download_thread = DownloadThread(download_url, save_path)
        self.download_thread.progress_update.connect(self.update_progress)
        self.download_thread.download_complete.connect(self.download_finished)
        self.download_thread.download_error.connect(self.download_error)

        self.progress_bar.setVisible(True)
        self.download_button.setEnabled(False)
        self.download_thread.start()

    def get_megadb_link(self, game_info):
        megadb_url_datas = game_info.get('downloads')
        if isinstance(megadb_url_datas, str) and "megadb.net" in megadb_url_datas:
            return megadb_url_datas
        elif isinstance(megadb_url_datas, list):
            return next((url for url in megadb_url_datas if "megadb.net" in url), None)
        return None

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def download_finished(self, save_path):
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        
        try:
            self.extract_and_run(save_path)
            QMessageBox.information(self, "Installation Complete", f"Game installed successfully to {os.path.dirname(save_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Installation Error", f"An error occurred during installation: {str(e)}")

    def extract_and_run(self, zip_path):
        extract_path = os.path.dirname(zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        os.remove(zip_path)  # Remove the zip file after extraction
        
        redist_folder = os.path.join(extract_path, "_Redist")
        if os.path.exists(redist_folder):
            for file in os.listdir(redist_folder):
                if file.endswith(".exe"):
                    full_path = os.path.join(redist_folder, file)
                    os.startfile(full_path)

    def download_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        QMessageBox.critical(self, "Download Error", f"An error occurred during download: {error_message}")

def main():
    app = QApplication(sys.argv)
    window = GameSearchApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    string = "The DataBase of games, has to bee updated every few days to make sure to get the updated content \nWould you like to update it, it can take up to 30min to fully update the DB"
    print(string)
    choice = input('\n\n ( Y / N ):  ')
    if choice.upper() == "Y":
        from GameList.main import start_script
        start_script()
        shutil.move('GameList\\cleaned_results.json','game_list.json')
    main()

print("Game Downloader application started successfully.")