#!/usr/bin/env python3
"""
CosyVoice_app - PyQt6 主程序入口
"""
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_controller import MainWindow


def main():
    """主函数"""
    # 创建应用实例
    app = QApplication(sys.argv)

    # 设置应用信息
    app.setApplicationName("CosyVoice_app")
    app.setApplicationVersion("1.0.0")

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    # 运行事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()