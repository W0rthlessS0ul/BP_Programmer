import sys
import serial.tools.list_ports
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QComboBox, QPushButton, QLabel, QLineEdit, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QStatusBar,
                             QFileDialog, QProgressBar, QTextEdit, QSplitter,
                             QFrame, QSizePolicy, QFormLayout, QAction,
                             QMenu, QToolBar, QAbstractItemView, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QPalette, QIcon, QKeySequence, QFont
import pyBusPirateLite
import time

class HexEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #2d2d30;
                border-bottom: 1px solid #2d2d30;
                padding: 4px;
            }
            QToolButton {
                background-color: transparent;
                color: #d4d4d4;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #2d2d30;
            }
            QToolButton:pressed {
                background-color: #3c3c3c;
            }
        """)

        self.copy_action = QAction(QIcon.fromTheme("edit-copy"), "Copy", self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        
        self.paste_action = QAction(QIcon.fromTheme("edit-paste"), "Paste", self)
        self.paste_action.setShortcut(QKeySequence.Paste)
        
        self.fill_action = QAction(QIcon.fromTheme("edit-fill"), "Fill", self)
        self.fill_menu = QMenu()
        self.fill_00 = QAction("Fill with 00", self)
        self.fill_ff = QAction("Fill with FF", self)
        self.fill_menu.addAction(self.fill_00)
        self.fill_menu.addAction(self.fill_ff)
        self.fill_action.setMenu(self.fill_menu)
        
        self.clear_action = QAction(QIcon.fromTheme("edit-clear"), "Clear", self)
        
        self.toolbar.addAction(self.copy_action)
        self.toolbar.addAction(self.paste_action)
        self.toolbar.addAction(self.fill_action)
        self.toolbar.addAction(self.clear_action)
        
        main_layout.addWidget(self.toolbar)

        self.hex_view = HexTableView()
        self.ascii_view = AsciiTableView()

        self.hex_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ascii_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.hex_view)
        splitter.addWidget(self.ascii_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 400])
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2d2d30;
            }
        """)

        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main_layout.addWidget(splitter, 1)  
        
        main_layout.addWidget(splitter)

        self.hex_view.itemChanged.connect(self.hex_data_changed)
        self.ascii_view.itemChanged.connect(self.ascii_data_changed)
        
        self.clear_action.triggered.connect(self.clear_data)
        self.fill_00.triggered.connect(lambda: self.fill_data(0x00))
        self.fill_ff.triggered.connect(lambda: self.fill_data(0xFF))
        
    def load_data(self, data):
        self.hex_view.load_data(data)
        self.ascii_view.load_data(data)
        
    def get_data(self):
        return self.hex_view.get_data()
        
    def hex_data_changed(self, item):
        if item.column() > 0:
            row = item.row()
            col = item.column() - 1
            self.ascii_view.update_ascii_row(row)
            
    def ascii_data_changed(self, item):
        if item.column() == 1:
            row = item.row()
            self.hex_view.update_hex_row(row)
            
    def clear_data(self):
        for _ in range(2):
            self.hex_view.clear_data()
            self.ascii_view.clear_data()
        
    def fill_data(self, value):
        for _ in range(2):
            self.hex_view.fill_data(value)
            self.ascii_view.fill_data(value)

class HexTableView(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(17)
        self.setHorizontalHeaderLabels(["Address"] + [f"{i:02X}" for i in range(16)])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.setSelectionMode(QTableWidget.ContiguousSelection)
        self.setShowGrid(False)
        self.setFont(QtGui.QFont("Consolas", 10))
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTableWidget {
                background-color: #161616;
                color: #d4d4d4;
                border: none;
                gridline-color: #2d2d30;
                selection-background-color: #264f78;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #2d2d30;
                color: #9cdcfe;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #2d2d30;
            }
        """)
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  

        self.setColumnWidth(0, 80)
        for i in range(1, 17):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        palette = self.palette()
        palette.setColor(QPalette.Base, QColor("#161616"))
        palette.setColor(QPalette.AlternateBase, QColor("#2d2d30"))
        self.setPalette(palette)
        
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            current_row = self.currentRow()
            current_col = self.currentColumn()

            if 1 <= current_col <= 16:
                if event.key() == Qt.Key_Backspace:
                    if current_col > 1:
                        new_col = current_col - 1
                        new_row = current_row
                    else:
                        if current_row > 0:
                            new_row = current_row - 1
                            new_col = 16
                        else:
                            new_row = 0
                            new_col = 1
                    self.setCurrentCell(new_row, new_col)

                else:
                    item = self.item(current_row, current_col)
                    if item:
                        item.setText("00")
                        item.setForeground(QColor("#d4d4d4"))
                        self.itemChanged.emit(item)
            event.accept()
            return

        super().keyPressEvent(event)

    def load_data(self, data):
        self.clearContents()
        rows = (len(data) + 15) // 16
        self.setRowCount(rows)
        
        for i in range(rows):
            addr = i * 16
            addr_item = QTableWidgetItem(f"{addr:06X}")
            addr_item.setFlags(addr_item.flags() & ~Qt.ItemIsEditable)
            addr_item.setForeground(QColor("#4ec9b0"))
            self.setItem(i, 0, addr_item)
            
            start = addr
            end = min(start + 16, len(data))

            for j in range(16):
                col = j + 1
                idx = start + j
                if idx < end:
                    byte = data[idx]
                    hex_item = QTableWidgetItem(f"{byte:02X}")
                    hex_item.setTextAlignment(Qt.AlignCenter)
                    hex_item.setFlags(hex_item.flags() | Qt.ItemIsEditable)

                    if byte != 0:
                        hex_item.setForeground(QColor("#dcdcaa"))
                    
                    self.setItem(i, col, hex_item)
                else:
                    hex_item = QTableWidgetItem("")
                    hex_item.setFlags(hex_item.flags() & ~Qt.ItemIsEditable)
                    self.setItem(i, col, hex_item)
    
    def update_hex_row(self, row):
        ascii_item = self.parent().parent().ascii_view.item(row, 1)
        if not ascii_item:
            return
            
        ascii_text = ascii_item.text()
        if len(ascii_text) > 16:
            ascii_text = ascii_text[:16]

        for j in range(len(ascii_text)):
            char = ascii_text[j]
            byte = ord(char)
            hex_item = self.item(row, j+1)
            if hex_item:
                hex_item.setText(f"{byte:02X}")
    
    def get_data(self):
        data = bytearray()
        for i in range(self.rowCount()):
            for j in range(1, 17):
                item = self.item(i, j)
                if item and item.text():
                    try:
                        data.append(int(item.text(), 16))
                    except ValueError:
                        data.append(0)
        return bytes(data)
        
    def clear_data(self):
        for i in range(self.rowCount()):
            for j in range(1, 17):
                item = self.item(i, j)
                if item:
                    item.setText("00")
        
    def fill_data(self, value):
        for i in range(self.rowCount()):
            for j in range(1, 17):
                item = self.item(i, j)
                if item:
                    item.setText(f"{value:02X}")

class AsciiTableView(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(17)
        self.setHorizontalHeaderLabels(["Address"] + [f"{i:02X}" for i in range(16)])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.setSelectionMode(QTableWidget.ContiguousSelection)
        self.setShowGrid(False)
        self.setFont(QtGui.QFont("Consolas", 10))
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTableWidget {
                background-color: #161616;
                color: #d4d4d4;
                border: none;
                gridline-color: #2d2d30;
                selection-background-color: #264f78;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #2d2d30;
                color: #9cdcfe;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #2d2d30;
            }
        """)
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  

        self.setColumnWidth(0, 80)
        for i in range(1, 17):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        palette = self.palette()
        palette.setColor(QPalette.Base, QColor("#161616"))
        palette.setColor(QPalette.AlternateBase, QColor("#2d2d30"))
        self.setPalette(palette)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            current_row = self.currentRow()
            current_col = self.currentColumn()

            if 1 <= current_col <= 16:
                item = self.item(current_row, current_col)
                if item:
                    item.setText(" ")
                    self.itemChanged.emit(item)

                    hex_item = self.parent().parent().hex_view.item(current_row, current_col)
                    if hex_item:
                        hex_item.setText("20")
            event.accept()
            return

        elif event.key() >= Qt.Key_Space and event.key() <= Qt.Key_AsciiTilde:
            current_row = self.currentRow()
            current_col = self.currentColumn()
            
            if 1 <= current_col <= 16:
                item = self.item(current_row, current_col)
                if not item:
                    item = QTableWidgetItem()
                    self.setItem(current_row, current_col, item)
                
                char = event.text()
                item.setText(char)
                item.setTextAlignment(Qt.AlignCenter)

                hex_item = self.parent().parent().hex_view.item(current_row, current_col)
                if hex_item:
                    hex_item.setText(f"{ord(char):02X}")

                if current_col < 16:
                    self.setCurrentCell(current_row, current_col + 1)
                elif current_row < self.rowCount() - 1:
                    self.setCurrentCell(current_row + 1, 1)
                
                self.itemChanged.emit(item)
            event.accept()
            return

        super().keyPressEvent(event)
        
    def load_data(self, data):
        self.clearContents()
        rows = (len(data) + 15) // 16
        self.setRowCount(rows)
        
        for i in range(rows):
            addr = i * 16
            addr_item = QTableWidgetItem(f"{addr:06X}")
            addr_item.setFlags(addr_item.flags() & ~Qt.ItemIsEditable)
            addr_item.setForeground(QColor("#4ec9b0"))
            self.setItem(i, 0, addr_item)
            
            start = addr
            end = min(start + 16, len(data))

            for j in range(16):
                col = j + 1
                idx = start + j
                if idx < end:
                    byte = data[idx]
                    if 32 <= byte <= 126:
                        char = chr(byte)
                    else:
                        char = "."
                    
                    char_item = QTableWidgetItem(char)
                    char_item.setTextAlignment(Qt.AlignCenter)
                    char_item.setFlags(char_item.flags() | Qt.ItemIsEditable)
                    char_item.setForeground(QColor("#ce9178"))
                    self.setItem(i, col, char_item)
                else:
                    char_item = QTableWidgetItem(" ")
                    char_item.setFlags(char_item.flags() & ~Qt.ItemIsEditable)
                    self.setItem(i, col, char_item)
    
    def update_ascii_row(self, row):
        pass
            
    def clear_data(self):
        for i in range(self.rowCount()):
            for j in range(1, 17):
                item = self.item(i, j)
                if item:
                    item.setText(" ")
        
    def fill_data(self, value):
        char = '.' if value < 32 or value > 126 else chr(value)
        for i in range(self.rowCount()):
            for j in range(1, 17):
                item = self.item(i, j)
                if item:
                    item.setText(char)

class I2CWorker(QThread):
    operation_complete = pyqtSignal(bool, str)
    progress_updated = pyqtSignal(int)
    data_ready = pyqtSignal(bytes)
    log_message = pyqtSignal(str)
    
    def __init__(self, operation, params):
        super().__init__()
        self.operation = operation
        self.params = params
        self.running = True
        self.i2c = None
        
    def run(self):
        try:
            port = self.params['port']
            baudrate = 115200
            speed = self.params['speed']
            address = self.params['address']
            data = self.params.get('data', b'')
            page_size = self.params.get('page_size', 4)
            power = self.params['power'].isChecked()
            pull_up = self.params['pull-up'].isChecked()

            self.log_message.emit(f"Connecting to Bus Pirate on {port}...")

            self.i2c = pyBusPirateLite.I2C(port, baudrate)
            self.i2c.enter_bb()
            self.i2c.enter()
            self.i2c.configure(power=power, pullup=pull_up)
            self.i2c.speed = speed
            self.log_message.emit(f"Connected at {speed} mode")
            
            if self.operation == 'read':
                size = self.params['size']
                self.read_eeprom(address, size)
            elif self.operation == 'write':
                self.write_eeprom(address, page_size, data)
            elif self.operation == 'erase':
                size = self.params['size']
                self.erase_eeprom(address, page_size, size)
                
            self.operation_complete.emit(True, f"{self.operation.capitalize()} completed successfully!")
            
        except Exception as e:
            self.log_message.emit(f"Error: {str(e)}")
            self.operation_complete.emit(False, f"Error: {str(e)}")
        finally:
            self.reset_to_normal()
            self.running = False
            
    def reset_to_normal(self):
        if self.i2c:
            try:
                self.log_message.emit("Resetting Bus Pirate to normal mode...")
                self.i2c.hw_reset()
                self.log_message.emit("Bus Pirate reset to normal mode")
            except Exception as e:
                self.log_message.emit(f"Reset error: {str(e)}")
            
    def read_eeprom(self, address, size):
        self.log_message.emit(f"Reading {size} bytes from address {address:02X}")
        data = self.i2c.write_then_read(1, size, [address | 0x01])
        self.data_ready.emit(bytes(data))
        self.progress_updated.emit(100)
        
    def write_eeprom(self, address, page_size, data):
        hex_list = list(data)
        m_lsb = 0
        hex_number = 0
        final_command = []
        total_bytes = len(hex_list)
        
        self.log_message.emit(f"Writing {total_bytes} bytes to EEPROM with page size {page_size}")

        full_pages = total_bytes // page_size
        
        for i in range(full_pages):
            if not self.running:
                return
                
            final_command.append(address)
            final_command.append(m_lsb)
            
            for j in range(page_size):
                final_command.append(hex_list[hex_number])
                hex_number += 1
                
            m_lsb += page_size

            try:
                self.i2c.write_then_read(len(final_command), 0, final_command)
            except Exception as e:
                self.log_message.emit(f"Write error: {str(e)}")
                raise
                
            self.progress_updated.emit(int(hex_number / total_bytes * 100))
            final_command.clear()
            time.sleep(0.01)

        remaining_bytes = total_bytes % page_size
        if remaining_bytes != 0:
            final_command.append(address)
            final_command.append(m_lsb)
            final_command.extend(hex_list[hex_number:hex_number + remaining_bytes])
            
            try:
                self.i2c.write_then_read(len(final_command), 0, final_command)
            except Exception as e:
                self.log_message.emit(f"Write error: {str(e)}")
                raise
                
            self.progress_updated.emit(100)
            final_command.clear()
            time.sleep(0.01)
            
    def erase_eeprom(self, address, page_size, size):
        data = b'\xFF' * size
        self.write_eeprom(address, page_size, data)
            
    def stop(self):
        self.running = False
        self.reset_to_normal()

class ModernButton(QPushButton):
    def __init__(self, text, icon=None, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(32)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        if icon:
            self.setIcon(icon)
            
        self.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #1c97ea;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #333344;
                color: #888888;
            }
        """)

class EEPROMProgrammer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BP Programmer")
        self.setGeometry(100, 100, 1200, 800)
        self.setup_styles()
        self.init_ui()
        
    def setup_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2d2d30;
                color: #d4d4d4;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #3c3c3c;
                border-radius: 8px;
                margin-top: 1ex;
                padding: 15px;
                background-color: #2d2d30;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #9cdcfe;
            }
            QLineEdit, QComboBox {
                background-color: #333333;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 5px;
                min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #0078d7;
            }
            QProgressBar {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                background-color: #2d2d30;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
            }
            QLabel {
                color: #9cdcfe;
            }
            QTabWidget::pane {
                border: none;
                background-color: #2d2d30;
            }
            QTabBar::tab {
                background-color: #2d2d30;
                color: #d4d4d4;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2d2d30;
                border-bottom: 2px solid #0078d7;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
        """)

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#2d2d30"))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor("#2d2d30"))
        palette.setColor(QPalette.AlternateBase, QColor("#2d2d30"))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor("#333333"))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor("#0078d7"))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        self.setPalette(palette)
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.tab_widget = QTabWidget()

        device_tab = QWidget()
        device_tab_layout = QVBoxLayout(device_tab)

        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
    
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
    
        refresh_btn = ModernButton("Refresh Ports")
        refresh_btn.clicked.connect(self.refresh_ports)
    
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["400kHz", "100kHz", "50kHz", "5kHz"])
        self.speed_combo.setCurrentIndex(1)

        self.power_check = QtWidgets.QCheckBox("Power")
        self.power_check.setChecked(True)
        self.pullup_check = QtWidgets.QCheckBox("Pull-up")
        self.pullup_check.setChecked(True)

        checkbox_style = """
            QCheckBox {
                color: #d4d4d4;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #3c3c3c;
                background: #333333;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #3c3c3c;
                background: #0078d7;
            }
        """
        self.power_check.setStyleSheet(checkbox_style)
        self.pullup_check.setStyleSheet(checkbox_style)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #3c3c3c;")
    
        top_layout.addWidget(QLabel("Serial Port:"))
        top_layout.addWidget(self.port_combo)
        top_layout.addWidget(refresh_btn)
        top_layout.addSpacing(20)
        top_layout.addWidget(QLabel("I2C Speed:"))
        top_layout.addWidget(self.speed_combo)
        top_layout.addSpacing(20)
        top_layout.addWidget(separator)
        top_layout.addSpacing(20)
        top_layout.addWidget(self.power_check)
        top_layout.addWidget(self.pullup_check)
        top_layout.addStretch()

        device_group = QGroupBox()
        device_layout_form = QFormLayout(device_group)
        device_layout_form.setLabelAlignment(Qt.AlignRight)
        
        self.address_edit = QLineEdit("0xA0")
        self.address_edit.setMaxLength(4)
        self.address_edit.setAlignment(Qt.AlignCenter)
        
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "1K (128B)", "2K (256B)", "4K (512B)", 
            "8K (1KB)", "16K (2KB)", "32K (4KB)", 
            "64K (8KB)", "128K (16KB)", "256K (32KB)",
            "Custom"
        ])
        self.size_combo.setCurrentIndex(1)
        
        self.custom_size_label = QLabel("Custom Size (bytes):")
        self.custom_size_edit = QLineEdit()
        self.custom_size_label.setVisible(False)
        self.custom_size_edit.setVisible(False)
        self.size_combo.currentIndexChanged.connect(self.toggle_custom_size)
        
        self.page_size_edit = QLineEdit("4")
        self.page_size_edit.setValidator(QtGui.QIntValidator(1, 256))
        
        device_layout_form.addRow("I2C Address (hex):", self.address_edit)
        device_layout_form.addRow("EEPROM Size:", self.size_combo)
        device_layout_form.addRow(self.custom_size_label, self.custom_size_edit)
        device_layout_form.addRow("Page Size (bytes):", self.page_size_edit)

        operations_group = QGroupBox()
        operations_layout = QHBoxLayout(operations_group)
        operations_layout.setSpacing(8)
        
        self.read_btn = ModernButton("Read EEPROM")
        self.read_btn.clicked.connect(self.read_eeprom)
        
        self.write_btn = ModernButton("Write EEPROM")
        self.write_btn.clicked.connect(self.write_eeprom)
        
        self.erase_btn = ModernButton("Erase EEPROM")
        self.erase_btn.clicked.connect(self.erase_eeprom)
        
        operations_layout.addWidget(self.read_btn, 1)
        operations_layout.addWidget(self.write_btn, 1)
        operations_layout.addWidget(self.erase_btn, 1)
        operations_layout.addStretch()

        file_ops_group = QGroupBox()
        file_ops_layout = QHBoxLayout(file_ops_group)
        
        self.save_btn = ModernButton("Save to File")
        self.save_btn.clicked.connect(self.save_to_file)
        
        self.load_btn = ModernButton("Load from File")
        self.load_btn.clicked.connect(self.load_from_file)
        
        file_ops_layout.addWidget(self.save_btn, 1)
        file_ops_layout.addWidget(self.load_btn, 1) 
        file_ops_layout.addStretch()

        log_group = QGroupBox()
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(5, 15, 5, 5)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(120)
        log_layout.addWidget(self.log_area)

        device_tab_layout.addWidget(top_bar)
        device_tab_layout.addWidget(device_group)
        device_tab_layout.addWidget(operations_group)
        device_tab_layout.addWidget(file_ops_group)
        device_tab_layout.addWidget(log_group)

        self.tab_widget.addTab(device_tab, "Programmer")

        hex_tab = QWidget()
        hex_layout = QVBoxLayout(hex_tab)
        hex_layout.setContentsMargins(0, 0, 0, 0)

        self.hex_editor = HexEditor()
        hex_layout.addWidget(self.hex_editor)

        self.tab_widget.addTab(hex_tab, "Hex Editor")

        main_layout.addWidget(self.tab_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.worker = None
        self.current_file = None

        QtCore.QTimer.singleShot(100, self.refresh_ports)
        
    def toggle_custom_size(self, index):
        is_custom = self.size_combo.currentText() == "Custom"
        self.custom_size_edit.setVisible(is_custom)
        self.custom_size_label.setVisible(is_custom)
        
    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)
        
        if not ports:
            self.port_combo.addItem("No ports found")
            self.log("No serial ports found. Connect Bus Pirate and click Refresh.")
        else:
            self.log(f"Found {len(ports)} serial port(s)")
    
    def get_eeprom_size(self):
        if self.size_combo.currentText() == "Custom":
            try:
                return int(self.custom_size_edit.text())
            except:
                return 256
                
        size_str = self.size_combo.currentText()
        size_map = {
            "1K (128B)": 128,
            "2K (256B)": 256,
            "4K (512B)": 512,
            "8K (1KB)": 1024,
            "16K (2KB)": 2048,
            "32K (4KB)": 4096,
            "64K (8KB)": 8192,
            "128K (16KB)": 16384,
            "256K (32KB)": 32768
        }
        return size_map.get(size_str, 256)
    
    def get_page_size(self):
        try:
            return int(self.page_size_edit.text())
        except:
            return 4
    
    def get_i2c_address(self):
        try:
            address_str = self.address_edit.text().strip()
            if address_str.startswith("0x"):
                return int(address_str[2:], 16)
            return int(address_str, 16)
        except:
            return 0xA0
    
    def log(self, message):
        timestamp = QtCore.QDateTime.currentDateTime().toString("hh:mm:ss")
        self.log_area.append(f"[{timestamp}] {message}")
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )
        
    def read_eeprom(self):
        if not self.port_combo.currentText() or "No ports" in self.port_combo.currentText():
            self.log("Error: No valid port selected!")
            return
            
        size = self.get_eeprom_size()
        address = self.get_i2c_address()
        self.log(f"Starting EEPROM read: {size} bytes from address 0x{address:02X}")
        
        params = {
            'port': self.port_combo.currentText(),
            'speed': self.speed_combo.currentText(),
            'address': address,
            'size': size,
            'power': self.power_check,
            'pull-up': self.pullup_check
        }
        
        self.worker = I2CWorker('read', params)
        self.worker.operation_complete.connect(self.operation_finished)
        self.worker.data_ready.connect(self.eeprom_data_ready)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.log_message.connect(self.log)
        
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.worker.start()
    
    def write_eeprom(self):
        if not self.port_combo.currentText() or "No ports" in self.port_combo.currentText():
            self.log("Error: No valid port selected!")
            return
            
        address = self.get_i2c_address()
        page_size = self.get_page_size()
        data = self.hex_editor.get_data()
        
        if not data:
            self.log("Error: No data to write!")
            return
            
        self.log(f"Starting EEPROM write: {len(data)} bytes to address 0x{address:02X}")
        
        params = {
            'port': self.port_combo.currentText(),
            'speed': self.speed_combo.currentText(),
            'address': address,
            'page_size': page_size,
            'data': data,
            'power': self.power_check,
            'pull-up': self.pullup_check
        }
        
        self.worker = I2CWorker('write', params)
        self.worker.operation_complete.connect(self.operation_finished)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.log_message.connect(self.log)
        
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.worker.start()
    
    def erase_eeprom(self):
        if not self.port_combo.currentText() or "No ports" in self.port_combo.currentText():
            self.log("Error: No valid port selected!")
            return
            
        size = self.get_eeprom_size()
        address = self.get_i2c_address()
        page_size = self.get_page_size()
        self.log(f"Starting EEPROM erase: {size} bytes at address 0x{address:02X}")
        
        params = {
            'port': self.port_combo.currentText(),
            'speed': self.speed_combo.currentText(),
            'address': address,
            'page_size': page_size,
            'size': size,
            'power': self.power_check,
            'pull-up': self.pullup_check
        }
        
        self.worker = I2CWorker('erase', params)
        self.worker.operation_complete.connect(self.operation_finished)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.log_message.connect(self.log)
        
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.worker.start()
    
    def save_to_file(self):
        data = self.hex_editor.get_data()
        if not data:
            self.log("Error: No data to save!")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save EEPROM Data", "", "Binary Files (*.bin);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, "wb") as f:
                    f.write(data)
                self.log(f"Data saved to {file_path}")
                self.status_bar.showMessage(f"Saved to {file_path}")
            except Exception as e:
                self.log(f"Save error: {str(e)}")
    
    def load_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load EEPROM Data", "", "Binary Files (*.bin);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    data = f.read()
                self.hex_editor.load_data(data)
                self.current_file = file_path
                self.log(f"Data loaded from {file_path}")
                self.status_bar.showMessage(f"Loaded {len(data)} bytes from {file_path}")
                self.tab_widget.setCurrentIndex(1)
            except Exception as e:
                self.log(f"Load error: {str(e)}")
    
    def eeprom_data_ready(self, data):
        self.hex_editor.load_data(data)
        self.log(f"EEPROM data loaded: {len(data)} bytes")
        self.status_bar.showMessage(f"Read {len(data)} bytes from EEPROM")
        self.tab_widget.setCurrentIndex(1)
    
    def operation_finished(self, success, message):
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.log(message)
            self.status_bar.showMessage(message)
        else:
            self.log(f"Operation failed: {message}")
            self.status_bar.showMessage("Operation failed")
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def set_ui_enabled(self, enabled):
        self.port_combo.setEnabled(enabled)
        self.speed_combo.setEnabled(enabled)
        self.address_edit.setEnabled(enabled)
        self.size_combo.setEnabled(enabled)
        self.custom_size_edit.setEnabled(enabled)
        self.page_size_edit.setEnabled(enabled)
        self.read_btn.setEnabled(enabled)
        self.write_btn.setEnabled(enabled)
        self.erase_btn.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)
        self.load_btn.setEnabled(enabled)
        self.hex_editor.setEnabled(enabled)
    
    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        event.accept()

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    
    app = QApplication(sys.argv)

    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = EEPROMProgrammer()
    window.show()
    sys.exit(app.exec_())