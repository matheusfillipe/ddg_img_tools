#!/usr/bin/env python3

from inspect import signature
import shutil
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import *

from DuckDuckGoImages import _download, get_image_urls
# from images_sample import IMAGES


def search_arg_images():
    return get_image_urls(" ".join(sys.argv[1:]))


class Runner(QThread):
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs

    def run(self):
        if len(self._kwargs.keys()) == 0 and len(self._args) == 0:
            self._target()
        else:
            if len(signature(self._target).parameters) > 0:
                self._target(*self._args, **self._kwargs)
            else:
                self._target()

def nogui(func):
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        runner = Runner(func, *args, **kwargs)
        # Keep the runner somewhere or it will be destroyed
        func.__runner = runner
        runner.start()

    return async_func


class MainWindow(QMainWindow):
    n_images = 12
    n_columns = 4
    setloading=pyqtSignal(bool)
    reloadui=pyqtSignal(list)

    def __init__(self, images: [str], start_index: int = 0):
        """__init__.

        :param images: list of urls
        :type images: [str]
        :param start_index: number to begin at
        :type page: int
        """
        super().__init__()
        self.images = images
        self.page = 0
        self.lbl_loading = QLabel(self)
        self.selected_widget = None
        self.setloading.connect(self.set_loading)
        self.reloadui.connect(self.render)
        self.render(images, self.page)

    def render(self, images: [str] = None, start_index: int = 0):
        """Renders UI and image grid.

        :param images: List of urls
        :type images: [str]
        :param start_index: start_index number
        :type start_index: int
        """
        n_images = self.n_images
        n_columns = self.n_columns

        images = self.images if images is None else images
        start_index = self.start_index if start_index is None else start_index
        self.images = images
        self.start_index = start_index

        vlayout = QVBoxLayout()
        grid_layout = QGridLayout()
        self.image_grid_widgets = [[] for _ in range(int(n_images / n_columns) + 1)]
        for i, url in enumerate(images[start_index : n_images + start_index]):
            # HACK multiple QWebEngines really?
            border_widget = QWidget()
            border_widget.setStyleSheet("background-color: black; margin: 5px")
            grid = QGridLayout()
            img = QWebEngineView(border_widget)
            img.load(QUrl(url))
            grid.addWidget(img)
            border_widget.setLayout(grid)
            border_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            pos = (int(i / n_columns), i % n_columns)
            grid_layout.addWidget(border_widget, *pos)
            self.image_grid_widgets[pos[1]].append(border_widget)

        btn_next, btn_prev, btn_first, btn_last = [
            QPushButton(lbl) for lbl in ["&Next", "&Prev", "&First", "&Last"]
        ]

        def render_next(offset):
            self.render(start_index=self.start_index + offset)

        btn_first.clicked.connect(lambda: self.render(start_index=0))
        btn_prev.clicked.connect(lambda: render_next(-n_images))
        btn_next.clicked.connect(lambda: render_next(n_images))
        btn_last.clicked.connect(
            lambda: self.render(start_index=len(images) - len(images) % n_images)
        )
        if start_index <= 0:
            btn_prev.setDisabled(True)
        if start_index + len(images) % n_images >= len(images) - 1:
            btn_next.setDisabled(True)

        if start_index <= 0:
            btn_first.setDisabled(True)
        if start_index + len(images) % n_images >= len(images) - 1:
            btn_last.setDisabled(True)

        self.btn_next = btn_next
        self.btn_prev = btn_prev
        self.btn_first = btn_first
        self.btn_last = btn_last

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(btn_first)
        bottom_row.addWidget(btn_prev)
        bottom_row.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding))
        bottom_row.addWidget(
            QLabel(
                f"page {int(start_index/n_images) + 1} out of {int(len(images)/n_images) + (1 if len(images) % n_images == 0 else 0) + (1 if len(images) > 0 else 0)} -- {len(images)} results"
            )
        )
        bottom_row.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding))
        bottom_row.addWidget(btn_next)
        bottom_row.addWidget(btn_last)

        @nogui
        def search_images():
            self.setloading.emit(True)
            self.reloadui.emit(get_image_urls(self.searchbar.text()))
            self.setloading.emit(False)

        searchbar = QLineEdit()
        searchbar.setPlaceholderText("Search for images...")
        searchbar.returnPressed.connect(search_images)
        btn_search = QPushButton("&Search")
        btn_search.clicked.connect(search_images)

        top_row = QHBoxLayout()
        top_row.addWidget(searchbar)
        top_row.addWidget(btn_search)
        self.btn_search = btn_search
        self.searchbar = searchbar

        vlayout.addLayout(top_row)
        vlayout.addLayout(grid_layout)
        vlayout.addItem(
            QSpacerItem(
                1,
                1,
                vPolicy=QSizePolicy.Expanding
                if len(images) <= 0
                else QSizePolicy.Minimum,
            )
        )
        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        label_row = QHBoxLayout()
        label_row.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.lbl_loading.setText("Opened.")
        self.lbl_loading.setSizePolicy(sizePolicy)
        label_row.addWidget(self.lbl_loading)

        vlayout.addLayout(bottom_row)
        vlayout.addLayout(label_row)
        main_wid = QWidget()
        main_wid.setLayout(vlayout)
        self.setCentralWidget(main_wid)

        if len(images) > 0:
            self.select_item(0, 0)

    def set_loading(self, is_loading: bool):
        QApplication.processEvents()
        if is_loading:
            self.lbl_loading.setText("Loading....")
        else:
            self.lbl_loading.setText("")

    def select_item(self, x, y):
        self.xpos = x
        self.ypos = y
        if hasattr(self, "border_widget"):
            self.border_widget.setStyleSheet("background-color: black; margin: 3px")
        border_widget = self.image_grid_widgets[x][y]
        img_widget = border_widget.layout().itemAt(0).widget()
        border_widget.setStyleSheet("background-color: cyan; margin: 3px")
        self.border_widget = border_widget
        self.selected_widget = img_widget
        self.selected_widget.setFocus(True)

    def selection_move(self, x, y):
        n_columns = self.n_columns
        n_rows = int(self.n_images / self.n_columns)
        xpos = self.xpos
        ypos = self.ypos
        xpos += x
        ypos += y
        xpos = xpos if xpos < n_columns else 0
        xpos = n_columns - 1 if xpos < 0 else xpos
        ypos = ypos if ypos < n_rows else 0
        ypos = n_rows - 1 if ypos < 0 else ypos
        self.select_item(xpos, ypos)

    def get_key_modifiers(self, e):
        QModifiers = e.modifiers()
        modifiers = []
        if QModifiers & Qt.ShiftModifier:
            modifiers.append("shift")
        if QModifiers & Qt.ControlModifier:
            modifiers.append("control")
        if QModifiers & Qt.AltModifier:
            modifiers.append("alt")
        return modifiers

    def keyPressEvent(self, e):
        modifiers = self.get_key_modifiers(e)

        # Focus searchbar
        if e.key() == Qt.Key_L and modifiers == ["control"] or e.key() == Qt.Key_Slash:
            self.searchbar.setFocus(True)

        elif e.key() == Qt.Key_Y:
            self.copy_image()
        elif e.key() == Qt.Key_Return:
            if self.selected_widget and self.selected_widget.hasFocus():
                self.save_image()

        # Image navigation
        elif e.key() == Qt.Key_G and "shift" in modifiers:
            self.select_item(
                self.n_columns - 1, int(self.n_images / self.n_columns) - 1
            )
        elif e.key() == Qt.Key_G and "shift" not in modifiers:
            self.select_item(0, 0)
        elif e.key() in [Qt.Key_0, Qt.Key_Bar]:
            self.select_item(0, self.ypos)
        elif e.key() in [Qt.Key_Dollar]:
            self.select_item(self.n_columns - 1, self.ypos)
        elif e.key() in [Qt.Key_Down, Qt.Key_J]:
            self.selection_move(0, 1)
        elif e.key() in [Qt.Key_Up, Qt.Key_K]:
            self.selection_move(0, -1)
        elif e.key() in [Qt.Key_Left, Qt.Key_H, Qt.Key_B]:
            self.selection_move(-1, 0)
        elif e.key() in [Qt.Key_Right, Qt.Key_L, Qt.Key_W]:
            self.selection_move(1, 0)

        # Page navigation
        elif e.key() == Qt.Key_N:
            self.btn_next.click()
        elif e.key() == Qt.Key_P:
            self.btn_prev.click()
        elif e.key() == Qt.Key_Home:
            self.btn_first.click()
        elif e.key() == Qt.Key_End:
            self.btn_last.click()

    def download_current_img(self) -> Path:
        url = self.selected_widget.url().url()
        f = NamedTemporaryFile(prefix="image_explorer_cpy_")
        file = Path(f.name)
        f.close()
        _download(url, str(file.parent), file.name)
        return Path(f"{str(file)}.jpg")

    def save_image(self):
        filename = QFileDialog.getSaveFileName(directory=str(Path.home()), filter="jpeg file(*.jpeg)")[0]
        if not filename:
            return
        filename = filename if filename.endswith(".jpeg") else filename + ".jpeg"
        @nogui
        def download_and_process_image(filename):
            self.setloading.emit(True)
            img = self.download_current_img()
            shutil.copyfile(str(img), filename)
            try:
                img.unlink()
            except:
                print("Failed to remove temp file")
            self.setloading.emit(False)
        download_and_process_image(filename)

    @nogui
    def copy_image(self):
        self.setloading.emit(True)
        img = self.download_current_img()
        pixmap = QPixmap(str(img))
        QApplication.clipboard().setPixmap(pixmap)
        try:
            img.unlink()
        except:
            print("Failed to remove temp file")
        self.setloading.emit(False)


def main():
    print("loading....")
    # images = IMAGES
    # images = []
    images = search_arg_images()
    app = QApplication(sys.argv)
    window = MainWindow(images)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
