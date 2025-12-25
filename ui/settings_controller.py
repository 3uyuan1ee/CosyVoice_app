"""
Settings页面控制器 - 管理应用设置

职责:
- 隐私政策显示
- 配置文件编辑
- GitHub版本更新检查
- 反馈邮件发送
- License信息显示
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QDialog, QTextBrowser
from PyQt6.QtCore import Qt, pyqtSlot, QThread, pyqtSignal
from PyQt6.uic import loadUi
import os
import sys
from loguru import logger
from typing import Optional

from backend.config_manager import get_config_manager
from backend.version_service import get_version_service, UpdateInfo
from backend.feedback_service import get_feedback_service
from ui.message_box_helper import MessageBoxHelper


class UpdateCheckWorker(QThread):
    """更新检查工作线程"""

    finished = pyqtSignal(object)  # UpdateInfo
    error = pyqtSignal(str)

    def __init__(self, version_service, parent=None):
        super().__init__(parent)
        self.version_service = version_service

    def run(self):
        """执行更新检查"""
        try:
            update_info = self.version_service.check_for_updates()
            self.finished.emit(update_info)
        except Exception as e:
            logger.error(f"Update check error: {e}")
            self.error.emit(str(e))


class LicenseDialog(QDialog):
    """License显示对话框"""

    def __init__(self, title: str, file_path: str, parent=None):
        """
        初始化License对话框

        Args:
            title: 对话框标题
            file_path: License文件路径
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 500)
        self.license_file = file_path
        self._init_ui()
        self._load_license()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 文本浏览器
        self.text_browser = QTextBrowser()
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background: #1a1412;
                color: #e8d5c4;
                border: 1px solid #2a1d19;
                padding: 12px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.text_browser)

        # 关闭按钮
        from PyQt6.QtWidgets import QPushButton
        btn_close = QPushButton("Close")
        btn_close.setMinimumHeight(32)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #3d2b25;
                color: #e8d5c4;
                border: 2px solid #5a4339;
                border-radius: 0px;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #5a4339;
                color: #c4a77d;
            }
            QPushButton:pressed {
                background: #c4a77d;
                color: #1a1412;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _load_license(self):
        """加载License文件"""
        try:
            if os.path.exists(self.license_file):
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 根据文件扩展名判断是否为Markdown
                if self.license_file.endswith('.md'):
                    # 转换为HTML格式以支持Markdown
                    html_content = self._markdown_to_html(content)
                    self.text_browser.setHtml(html_content)
                else:
                    # 纯文本显示
                    self.text_browser.setPlainText(content)
            else:
                self.text_browser.setPlainText("License file not found.")
        except Exception as e:
            logger.error(f"Error loading license: {e}")
            self.text_browser.setPlainText(f"Error loading license: {str(e)}")

    def _markdown_to_html(self, markdown_text: str) -> str:
        """简单的Markdown转HTML"""
        html = markdown_text

        # 转换标题
        html = html.replace('### ', '<h3>').replace('\n', '</h3>\n')
        html = html.replace('## ', '<h2>').replace('</h3>', '</h2>')
        html = html.replace('# ', '<h1>').replace('</h2>', '</h1>')

        # 转换粗体
        html = html.replace('**', '<b>').replace('**', '</b>')

        # 转换链接
        import re
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

        # 转换换行
        html = html.replace('\n\n', '<br><br>')

        return f"<html><body style='color: #e8d5c4;'>{html}</body></html>"


class SettingsPanel(QWidget):
    """Settings页面控制器"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 加载UI文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, 'settings.ui')
        loadUi(ui_path, self)

        # 服务层
        self.config_manager = get_config_manager()
        self.version_service = get_version_service()
        self.feedback_service = get_feedback_service()

        # 当前版本
        self.current_version = "1.0.0"

        # 初始化
        self._init_ui()
        self._connect_signals()
        self._load_config()

        logger.info("SettingsPanel initialized")

    def _init_ui(self):
        """初始化UI"""
        # 设置版本信息
        self.versionLabel.setText(f"Version: {self.current_version}")

        self.github_url = "https://github.com/3uyuan1ee/CosyVoice_app"

    def _connect_signals(self):
        """连接信号槽"""
        self.btnReloadConfig.clicked.connect(self._load_config)
        self.btnSaveConfig.clicked.connect(self._save_config)
        self.btnCheckUpdate.clicked.connect(self._check_for_updates)
        self.btnOpenGitHub.clicked.connect(self._open_github)
        self.btnSendFeedback.clicked.connect(self._send_feedback)
        self.btnViewLicense.clicked.connect(self._view_license)
        self.btnViewThirdPartyLicense.clicked.connect(self._view_third_party_license)
        self.btnViewPrivacy.clicked.connect(self._view_privacy)

    def _load_config(self):
        """加载配置文件"""
        try:
            logger.info("Loading configuration...")

            # 获取当前配置
            config = self.config_manager.get_config()
            config_dict = config.to_dict()

            # 格式化为YAML
            import yaml
            config_text = yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)

            # 显示在文本编辑器
            self.configTextEdit.setPlainText(config_text)

            logger.info("Configuration loaded successfully")

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to load configuration: {str(e)}")

    def _save_config(self):
        """保存配置文件"""
        try:
            logger.info("Saving configuration...")

            # 获取文本内容
            config_text = self.configTextEdit.toPlainText()

            # 解析YAML
            import yaml
            config_dict = yaml.safe_load(config_text)

            # 验证配置
            from backend.config_manager import AppConfig
            new_config = AppConfig.from_dict(config_dict)
            errors = new_config.validate()

            if errors:
                error_msg = "\n".join(errors)
                MessageBoxHelper.warning(
                    self,
                    "Invalid Configuration",
                    f"Configuration validation failed:\n{error_msg}"
                )
                return

            # 更新配置
            for key, value in config_dict.items():
                if hasattr(new_config, key):
                    self.config_manager.set(key, value, notify=False)

            # 保存到文件
            if self.config_manager.save_user_config():
                MessageBoxHelper.information(self, "Success", "Configuration saved successfully. Changes will take effect on next restart.")
                logger.info("Configuration saved successfully")
            else:
                MessageBoxHelper.critical(self, "Error", "Failed to save configuration file")

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            MessageBoxHelper.critical(self, "Error", f"Invalid YAML format:\n{str(e)}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to save configuration: {str(e)}")

    def _check_for_updates(self):
        """检查更新"""
        try:
            logger.info("Checking for updates...")

            # 禁用按钮
            self.btnCheckUpdate.setEnabled(False)
            self.updateStatusLabel.setText("Checking for updates...")

            # 启动工作线程
            self._update_worker = UpdateCheckWorker(self.version_service)
            self._update_worker.finished.connect(self._on_update_check_finished)
            self._update_worker.error.connect(self._on_update_check_error)
            self._update_worker.start()

        except Exception as e:
            logger.error(f"Error starting update check: {e}")
            self.btnCheckUpdate.setEnabled(True)
            self.updateStatusLabel.setText("Update check failed")

    @pyqtSlot(object)
    def _on_update_check_finished(self, update_info: UpdateInfo):
        """更新检查完成"""
        try:
            self.btnCheckUpdate.setEnabled(True)

            if update_info.has_update:
                # 有新版本
                self.updateStatusLabel.setText(
                    f"New version available: {update_info.latest_version} (current: {update_info.current_version})\n"
                    f"Download: {update_info.download_url}"
                )
                self.updateStatusLabel.setStyleSheet("""
                    QLabel {
                        color: #c4a77d;
                        font-size: 11px;
                        background: transparent;
                    }
                """)

                # 询问是否下载
                reply = MessageBoxHelper.question(
                    self,
                    "Update Available",
                    f"A new version ({update_info.latest_version}) is available!\n\n"
                    f"Current version: {update_info.current_version}\n\n"
                    f"Do you want to download the update?"
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # 打开下载页面
                    import webbrowser
                    webbrowser.open(update_info.download_url)
            else:
                # 无更新
                self.updateStatusLabel.setText(
                    f"You are using the latest version ({update_info.current_version})"
                )
                self.updateStatusLabel.setStyleSheet("""
                    QLabel {
                        color: #6b5c52;
                        font-size: 10px;
                        background: transparent;
                    }
                """)

            logger.info(f"Update check complete: has_update={update_info.has_update}")

        except Exception as e:
            logger.error(f"Error handling update check finished: {e}")
            self.btnCheckUpdate.setEnabled(True)
            self.updateStatusLabel.setText("Update check failed")

    @pyqtSlot(str)
    def _on_update_check_error(self, error_msg: str):
        """更新检查错误"""
        logger.error(f"Update check error: {error_msg}")
        self.btnCheckUpdate.setEnabled(True)
        self.updateStatusLabel.setText("Failed to check for updates")
        MessageBoxHelper.warning(self, "Error", f"Failed to check for updates:\n{error_msg}")

    def _open_github(self):
        """打开GitHub项目页面"""
        try:
            import webbrowser
            webbrowser.open(self.github_url)
            logger.info(f"Opened GitHub: {self.github_url}")
        except Exception as e:
            logger.error(f"Error opening GitHub: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to open GitHub:\n{str(e)}")

    def _send_feedback(self):
        """发送反馈"""
        try:
            logger.info("Sending feedback...")

            # 获取是否包含日志
            include_logs = self.chkIncludeLogs.isChecked()

            # 发送反馈
            success = self.feedback_service.send_feedback(
                subject="CosyVoice_app Feedback",
                message="",
                include_logs=include_logs,
                include_stats=True
            )

            if success:
                MessageBoxHelper.information(
                    self,
                    "Feedback",
                    f"Your email client has been opened with the feedback information.\n\n"
                    f"Please send the email to: {self.feedback_service.get_feedback_email()}"
                )
            else:
                MessageBoxHelper.warning(
                    self,
                    "Error",
                    "Failed to open email client. Please send your feedback manually to:\n"
                    f"{self.feedback_service.get_feedback_email()}"
                )

        except Exception as e:
            logger.error(f"Error sending feedback: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to send feedback:\n{str(e)}")

    def _view_license(self):
        """查看MIT License"""
        try:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(__file__))
            license_file = os.path.join(project_root, "LICENSE")

            dialog = LicenseDialog("MIT License", license_file, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error viewing license: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to view license:\n{str(e)}")

    def _view_third_party_license(self):
        """查看第三方License"""
        try:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(__file__))
            license_file = os.path.join(project_root, "THIRD_PARTY_LICENSES.md")

            dialog = LicenseDialog("Third-Party Licenses", license_file, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error viewing third-party license: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to view third-party license:\n{str(e)}")

    def _view_privacy(self):
        """查看隐私政策"""
        try:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(__file__))
            privacy_file = os.path.join(project_root, "PRIVACY_POLICY.md")

            dialog = LicenseDialog("Privacy Policy", privacy_file, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error viewing privacy policy: {e}")
            MessageBoxHelper.critical(self, "Error", f"Failed to view privacy policy:\n{str(e)}")

    def refresh_all(self):
        """刷新所有数据"""
        try:
            logger.info("Refreshing settings...")
            self._load_config()
            logger.info("Settings refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing settings: {e}")

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up SettingsPanel")
