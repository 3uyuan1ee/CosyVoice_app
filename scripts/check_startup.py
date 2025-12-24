#!/usr/bin/env python3
"""
启动检查脚本 - 验证环境是否满足运行要求

功能:
- Python版本检查
- 依赖包检查
- GPU/CPU可用性检查
- 模型文件完整性检查
- 配置文件检查
- 权限检查
- 磁盘空间检查

用法:
    python scripts/check_startup.py
    python -m scripts.check_startup  # 从项目根目录
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional

# 颜色输出（跨平台）
class Colors:
    """ANSI颜色代码"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

    @classmethod
    def ok(cls, msg: str) -> str:
        """绿色成功消息"""
        return f"{cls.GREEN}✓{cls.END} {msg}"

    @classmethod
    def warn(cls, msg: str) -> str:
        """黄色警告消息"""
        return f"{cls.YELLOW}⚠{cls.END} {msg}"

    @classmethod
    def error(cls, msg: str) -> str:
        """红色错误消息"""
        return f"{cls.RED}✗{cls.END} {msg}"

    @classmethod
    def info(cls, msg: str) -> str:
        """蓝色信息消息"""
        return f"{cls.BLUE}ℹ{cls.END} {msg}"


# ==================== 检查器类 ====================

class StartupChecker:
    """启动检查器"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warned = 0

        # 添加项目根目录到路径
        self.project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(self.project_root))

    def print_header(self):
        """打印标题"""
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}CosyVoice_app 启动环境检查{Colors.END}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")

    def print_summary(self):
        """打印检查摘要"""
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}检查摘要{Colors.END}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")
        print(f"通过: {Colors.ok(str(self.checks_passed))}")
        print(f"警告: {Colors.warn(str(self.checks_warned))}")
        print(f"失败: {Colors.error(str(self.checks_failed))}")

        if self.errors:
            print(f"\n{Colors.BOLD}错误列表:{Colors.END}")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")

        if self.warnings:
            print(f"\n{Colors.BOLD}警告列表:{Colors.END}")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        # 返回是否通过（允许警告）
        success = self.checks_failed == 0
        if success:
            print(f"\n{Colors.ok('环境检查通过！')}")
        else:
            print(f"\n{Colors.error('环境检查失败！请修复上述错误后重试。')}")

        return success

    # ==================== 具体检查方法 ====================

    def check_python_version(self):
        """检查Python版本"""
        print(f"{Colors.BOLD}1. Python版本检查{Colors.END}")

        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        # 最低要求: Python 3.10
        if version >= (3, 10):
            print(f"  {Colors.ok(f'Python {version_str}')}")
            self.checks_passed += 1
            return True
        else:
            print(f"  {Colors.error(f'Python {version_str} (最低要求: 3.10)')}")
            self.errors.append(f"Python版本过低: {version_str} (需要 >= 3.10)")
            self.checks_failed += 1
            return False

    def check_required_packages(self):
        """检查必需的依赖包"""
        print(f"\n{Colors.BOLD}2. 依赖包检查{Colors.END}")

        # 核心依赖（必需）
        # 注意：包名(导入名)可能与pip包名不同
        critical_packages = {
            'PyQt6': ('6.6.0', 'PyQt6'),
            'torch': ('2.3.1', 'torch'),
            'torchaudio': ('2.3.1', 'torchaudio'),
            'librosa': ('0.10.2', 'librosa'),
            'soundfile': ('0.12.1', 'soundfile'),
            'loguru': ('0.7.0', 'loguru'),
            'yaml': ('6.0', 'PyYAML'),  # 模块名yaml, 包名PyYAML
        }

        # 可选依赖
        optional_packages = {
            'psutil': '5.9.8',
        }

        missing_packages = []

        # 检查核心依赖
        for import_name, (min_version, display_name) in critical_packages.items():
            try:
                module = __import__(import_name)
                installed_version = getattr(module, '__version__', 'unknown')

                # 简单版本比较
                if installed_version != 'unknown':
                    print(f"  {Colors.ok(f'{display_name}=={installed_version}')}")
                else:
                    print(f"  {Colors.ok(f'{display_name} (已安装)')}")

                self.checks_passed += 1

            except ImportError:
                print(f"  {Colors.error(f'{display_name} 未安装')}")
                missing_packages.append(display_name)
                self.checks_failed += 1

        # 检查可选依赖
        for package, min_version in optional_packages.items():
            try:
                __import__(package)
                print(f"  {Colors.ok(f'{package} (可选)')}")
                self.checks_passed += 1
            except ImportError:
                print(f"  {Colors.warn(f'{package} (可选，未安装)')}")
                self.warnings.append(f"未安装可选包: {package}")
                self.checks_warned += 1

        if missing_packages:
            install_cmd = f"pip install {' '.join(missing_packages)}"
            self.errors.append(f"缺失必需依赖包: {', '.join(missing_packages)}")
            self.errors.append(f"修复命令: {install_cmd}")

    def check_gpu_availability(self):
        """检查GPU/CPU可用性"""
        print(f"\n{Colors.BOLD}3. 计算设备检查{Colors.END}")

        try:
            import torch

            # CUDA检查
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)

                print(f"  {Colors.ok(f'CUDA GPU: {gpu_name}')}")
                print(f"     GPU数量: {gpu_count}")
                print(f"     显存: {gpu_memory:.2f} GB")
                self.checks_passed += 1

            # MPS检查（macOS）
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                print(f"  {Colors.ok('Apple MPS (Metal Performance Shaders)')}")
                self.checks_passed += 1

            # CPU模式
            else:
                print(f"  {Colors.warn('未检测到GPU，将使用CPU模式（速度较慢）')}")
                self.warnings.append("GPU不可用，将使用CPU模式")
                self.checks_warned += 1

        except ImportError:
            print(f"  {Colors.error('无法检查GPU（PyTorch未安装）')}")
            self.checks_failed += 1

    def check_project_structure(self):
        """检查项目结构"""
        print(f"\n{Colors.BOLD}4. 项目结构检查{Colors.END}")

        required_dirs = [
            'backend',
            'ui',
            'static',
            'CosyVoice',
        ]

        required_files = [
            'main.py',
            'requirements.txt',
        ]

        # 检查目录
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                print(f"  {Colors.ok(f'{dir_name}/')}")
                self.checks_passed += 1
            else:
                print(f"  {Colors.error(f'{dir_name}/ (缺失)')}")
                self.errors.append(f"缺少目录: {dir_name}/")
                self.checks_failed += 1

        # 检查文件
        for file_name in required_files:
            file_path = self.project_root / file_name
            if file_path.exists() and file_path.is_file():
                print(f"  {Colors.ok(file_name)}")
                self.checks_passed += 1
            else:
                print(f"  {Colors.error(f'{file_name} (缺失)')}")
                self.errors.append(f"缺少文件: {file_name}")
                self.checks_failed += 1

    def check_model_files(self):
        """检查模型文件"""
        print(f"\n{Colors.BOLD}5. 模型文件检查{Colors.END}")

        try:
            from backend.path_manager import PathManager
            path_manager = PathManager()

            # 检查默认模型
            model_path = path_manager.get_cosyvoice3_2512_model_path()

            if not os.path.exists(model_path):
                print(f"  {Colors.warn('CosyVoice3 模型未下载')}")
                self.warnings.append("CosyVoice3 模型未下载，首次使用时会自动下载")
                self.checks_warned += 1
            else:
                # 检查完整性
                is_complete, missing_files, error_msg = path_manager.check_cosyvoice3_model_integrity()

                if is_complete:
                    size_bytes, size_mb = path_manager.get_model_disk_size(model_path)
                    print(f"  {Colors.ok(f'CosyVoice3 模型完整 ({size_mb:.1f} MB)')}")
                    self.checks_passed += 1
                else:
                    print(f"  {Colors.error(f'模型不完整: {error_msg}')}")
                    for missing in missing_files:
                        print(f"     - {missing}")
                    self.errors.append(f"模型文件不完整: {', '.join(missing_files)}")
                    self.checks_failed += 1

        except Exception as e:
            print(f"  {Colors.error(f'模型检查失败: {e}')}")
            self.checks_failed += 1

    def check_disk_space(self):
        """检查磁盘空间"""
        print(f"\n{Colors.BOLD}6. 磁盘空间检查{Colors.END}")

        try:
            import shutil

            # 检查项目根目录所在磁盘
            total, used, free = shutil.disk_usage(self.project_root)

            free_gb = free / (1024**3)
            total_gb = total / (1024**3)

            print(f"  总空间: {total_gb:.1f} GB")
            print(f"  可用空间: {free_gb:.1f} GB")

            # 最低要求: 5GB 可用空间
            if free_gb >= 5:
                print(f"  {Colors.ok('磁盘空间充足')}")
                self.checks_passed += 1
            else:
                print(f"  {Colors.warn('磁盘空间不足 (建议 >= 5GB)')}")
                self.warnings.append(f"磁盘空间较低: {free_gb:.1f} GB 可用")
                self.checks_warned += 1

        except Exception as e:
            print(f"  {Colors.error(f'无法检查磁盘空间: {e}')}")
            self.checks_failed += 1

    def check_permissions(self):
        """检查文件权限"""
        print(f"\n{Colors.BOLD}7. 文件权限检查{Colors.END}")

        # 检查是否有写入权限
        test_files = [
            self.project_root / 'data',
            self.project_root / 'static' / 'voices',
        ]

        all_ok = True
        for test_file in test_files:
            try:
                # 尝试创建目录
                test_file.mkdir(parents=True, exist_ok=True)

                # 尝试创建测试文件
                test_path = test_file / '.write_test'
                test_path.touch()
                test_path.unlink()

                print(f"  {Colors.ok(f'可写入: {test_file.relative_to(self.project_root)}')}")
                self.checks_passed += 1

            except Exception as e:
                print(f"  {Colors.error(f'无写入权限: {test_file.relative_to(self.project_root)}')}")
                self.errors.append(f"无写入权限: {test_file}")
                all_ok = False
                self.checks_failed += 1

    def run_all_checks(self) -> bool:
        """运行所有检查"""
        self.print_header()

        # 执行检查
        self.check_python_version()
        self.check_required_packages()
        self.check_gpu_availability()
        self.check_project_structure()
        self.check_model_files()
        self.check_disk_space()
        self.check_permissions()

        # 打印摘要
        return self.print_summary()


# ==================== 主函数 ====================

def main():
    """主函数"""
    # 禁用PyQt6应用程序警告
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'

    # 创建检查器并运行
    checker = StartupChecker()
    success = checker.run_all_checks()

    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
