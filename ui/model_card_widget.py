"""
模型卡片组件 - 显示单个模型的信息和下载状态
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal
from enum import Enum


class ModelStatus(Enum):
    """模型状态"""
    NOT_DOWNLOADED = "NOT_DOWNLOADED"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    ERROR = "ERROR"


class ModelCardWidget(QWidget):
    """模型卡片组件"""

    # 信号定义
    download_clicked = pyqtSignal(str)  # model_id
    cancel_clicked = pyqtSignal(str)    # model_id
    delete_clicked = pyqtSignal(str)    # model_id

    def __init__(self, model_id: str, model_name: str, model_size: str,
                 model_description: str, parent=None):
        super().__init__(parent)
        self.model_id = model_id
        self.model_name = model_name
        self.model_size = model_size
        self.model_description = model_description
        self.status = ModelStatus.NOT_DOWNLOADED
        self.progress = 0

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        self.setMinimumHeight(130)  # 改为最小高度，允许内容自适应

        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # 顶部行（名称 + 大小 + 状态）
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        # 模型名称
        self.name_label = QLabel(self.model_name)
        self.name_label.setStyleSheet("""
            QLabel {
                color: #c4a77d;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 0px;
                background: transparent;
            }
        """)

        # 模型大小
        self.size_label = QLabel(self.model_size)
        self.size_label.setStyleSheet("""
            QLabel {
                color: #8d7b68;
                font-size: 10px;
                letter-spacing: 0px;
                background: transparent;
            }
        """)

        # 状态标签
        self.status_label = QLabel("NOT DOWNLOADED")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #6b5c52;
                font-size: 10px;
                letter-spacing: 0px;
                background: transparent;
            }
        """)

        top_layout.addWidget(self.name_label)
        top_layout.addStretch()
        top_layout.addWidget(self.size_label)
        top_layout.addWidget(self.status_label)

        # 描述
        self.desc_label = QLabel(self.model_description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("""
            QLabel {
                color: #6b5c52;
                font-size: 10px;
                line-height: 1.4;
                background: transparent;
            }
        """)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #14100f;
                border: 2px solid #2a1d19;
                border-radius: 0px;
                height: 8px;
                text-align: center;
            }

            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #5a4339,
                                            stop:1 #8d7b68);
                border-radius: 0px;
                border: 1px solid #3d2b25;
            }
        """)

        # 进度标签
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #8d7b68;
                font-size: 9px;
                letter-spacing: 0px;
                background: transparent;
            }
        """)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # 下载/取消按钮
        self.download_btn = QPushButton("DOWNLOAD")
        self.download_btn.setFixedHeight(28)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background: #1a1412;
                color: #c4a77d;
                border: 2px solid #3d2b25;
                border-radius: 0px;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 0px;
                padding: 4px 12px;
                text-align: center;
            }

            QPushButton:hover {
                background: #3d2b25;
                color: #e8d5c4;
                border-color: #c4a77d;
            }

            QPushButton:pressed {
                background: #c4a77d;
                color: #1a1412;
                border-color: #c4a77d;
            }

            QPushButton:disabled {
                color: #6b5c52;
                border-color: #2a1d19;
            }
        """)
        self.download_btn.clicked.connect(self._on_download_clicked)

        button_layout.addStretch()
        button_layout.addWidget(self.progress_label)
        button_layout.addWidget(self.download_btn)

        # 添加到主布局
        layout.addLayout(top_layout)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(button_layout)

    def _on_download_clicked(self):
        """下载按钮点击"""
        if self.status == ModelStatus.DOWNLOADING:
            self.cancel_clicked.emit(self.model_id)
        elif self.status == ModelStatus.DOWNLOADED:
            self.delete_clicked.emit(self.model_id)
        else:
            self.download_clicked.emit(self.model_id)

    def update_status(self, status: ModelStatus, progress: int = 0,
                     error_msg: str = ""):
        """
        更新状态

        Args:
            status: 模型状态
            progress: 下载进度 (0-100)
            error_msg: 错误信息
        """
        self.status = status
        self.progress = progress

        if status == ModelStatus.NOT_DOWNLOADED:
            self.status_label.setText("NOT DOWNLOADED")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #6b5c52;
                    font-size: 10px;
                    letter-spacing: 0px;
                    background: transparent;
                }
            """)
            self.download_btn.setText("DOWNLOAD")
            self.download_btn.setEnabled(True)
            self.progress_bar.setValue(0)
            self.progress_label.setText("")

        elif status == ModelStatus.DOWNLOADING:
            self.status_label.setText("DOWNLOADING...")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #c4a77d;
                    font-size: 10px;
                    letter-spacing: 0px;
                    background: transparent;
                }
            """)
            self.download_btn.setText("CANCEL")
            self.download_btn.setEnabled(True)
            self.progress_bar.setValue(progress)
            self.progress_label.setText(f"{progress}%")

        elif status == ModelStatus.DOWNLOADED:
            self.status_label.setText("DOWNLOADED")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #5a4339;
                    font-size: 10px;
                    letter-spacing: 0px;
                    background: transparent;
                }
            """)
            self.download_btn.setText("DELETE")
            self.download_btn.setEnabled(True)
            self.download_btn.setStyleSheet("""
                QPushButton {
                    background: #1a1412;
                    color: #8b3a3a;
                    border: 2px solid #5a3a3a;
                    border-radius: 0px;
                    font-size: 10px;
                    font-weight: bold;
                    letter-spacing: 0px;
                    padding: 4px 12px;
                    text-align: center;
                }

                QPushButton:hover {
                    background: #3a2a2a;
                    color: #ab5a5a;
                    border-color: #8b4a4a;
                }

                QPushButton:pressed {
                    background: #8b3a3a;
                    color: #1a1412;
                    border-color: #8b3a3a;
                }
            """)
            self.progress_bar.setValue(100)
            self.progress_label.setText("COMPLETE")

        elif status == ModelStatus.ERROR:
            self.status_label.setText("ERROR")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #8b3a3a;
                    font-size: 10px;
                    letter-spacing: 0px;
                    background: transparent;
                }
            """)
            self.download_btn.setText("RETRY")
            self.download_btn.setEnabled(True)
            self.progress_bar.setValue(progress)
            self.progress_label.setText(error_msg[:30] if error_msg else "FAILED")
