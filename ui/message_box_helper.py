"""
消息框助手 - 提供统一样式的消息对话框
"""

from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtGui import QFont
from typing import Optional


class MessageBoxHelper:
    """消息框助手类 - 提供统一样式的对话框"""

    # 统一样式表
    STYLESHEET = """
        QMessageBox {
            background-color: #2b2b2b;
            color: #e0e0e0;
        }

        QMessageBox QLabel {
            color: #ffffff;
            font-size: 14px;
            min-width: 300px;
        }

        QMessageBox QPushButton {
            background-color: #3a3a3a;
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 6px 20px;
            font-size: 13px;
            font-weight: bold;
            min-width: 80px;
        }

        QMessageBox QPushButton:hover {
            background-color: #4a4a4a;
            border: 1px solid #666666;
        }

        QMessageBox QPushButton:pressed {
            background-color: #555555;
        }

        QMessageBox QPushButton:default {
            background-color: #0a84ff;
            border: 1px solid #0a84ff;
        }

        QMessageBox QPushButton:default:hover {
            background-color: #1a94ff;
        }

        QMessageBox QPushButton:default:pressed {
            background-color: #0066cc;
        }
    """

    @staticmethod
    def _apply_style(msg_box: QMessageBox) -> None:
        """应用统一样式到消息框"""
        msg_box.setStyleSheet(MessageBoxHelper.STYLESHEET)

        # 设置字体
        font = QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        msg_box.setFont(font)

    @staticmethod
    def critical(
        parent: Optional[QWidget],
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok
    ) -> QMessageBox.StandardButton:
        """
        显示错误对话框

        Args:
            parent: 父窗口
            title: 标题
            message: 消息内容
            buttons: 按钮组合

        Returns:
            用户点击的按钮
        """
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(buttons)

        MessageBoxHelper._apply_style(msg_box)
        return msg_box.exec()

    @staticmethod
    def warning(
        parent: Optional[QWidget],
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok
    ) -> QMessageBox.StandardButton:
        """
        显示警告对话框

        Args:
            parent: 父窗口
            title: 标题
            message: 消息内容
            buttons: 按钮组合

        Returns:
            用户点击的按钮
        """
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(buttons)

        MessageBoxHelper._apply_style(msg_box)
        return msg_box.exec()

    @staticmethod
    def information(
        parent: Optional[QWidget],
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok
    ) -> QMessageBox.StandardButton:
        """
        显示信息对话框

        Args:
            parent: 父窗口
            title: 标题
            message: 消息内容
            buttons: 按钮组合

        Returns:
            用户点击的按钮
        """
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(buttons)

        MessageBoxHelper._apply_style(msg_box)
        return msg_box.exec()

    @staticmethod
    def question(
        parent: Optional[QWidget],
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.No
    ) -> QMessageBox.StandardButton:
        """
        显示询问对话框

        Args:
            parent: 父窗口
            title: 标题
            message: 消息内容
            buttons: 按钮组合
            default_button: 默认按钮

        Returns:
            用户点击的按钮
        """
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(buttons)
        msg_box.setDefaultButton(default_button)

        MessageBoxHelper._apply_style(msg_box)
        return msg_box.exec()

    @staticmethod
    def with_details(
        parent: Optional[QWidget],
        title: str,
        message: str,
        icon: QMessageBox.Icon,
        details: Optional[str] = None
    ) -> None:
        """
        显示带详细信息的对话框

        Args:
            parent: 父窗口
            title: 标题
            message: 消息内容
            icon: 图标类型
            details: 详细信息（可选）
        """
        msg_box = QMessageBox(parent)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        if details:
            msg_box.setDetailedText(details)

        MessageBoxHelper._apply_style(msg_box)
        msg_box.exec()