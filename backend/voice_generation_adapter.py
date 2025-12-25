"""
语音生成适配器 - 统一后端接口

设计模式:
- 适配器模式: 将CV_clone的接口适配到UI层需要的格式
- 策略模式: 支持不同的生成策略
- 依赖注入: 通过工厂方法注入依赖

架构:
VoiceGenerationAdapter (适配器)
    ├── CVCloneAdapter (CosyVoice适配器)
    └── MockAdapter (模拟适配器,用于测试)
"""

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Any, Callable, List, Tuple
from pathlib import Path
from loguru import logger
import threading


class GenerationStrategy(Enum):
    """生成策略枚举"""
    QUALITY = "quality"        # 质量优先
    BALANCED = "balanced"      # 平衡模式
    SPEED = "speed"            # 速度优先


@dataclass
class GenerationRequest:
    """生成请求"""
    text: str
    reference_audio: str
    pitch_shift: float = 0.0
    output_path: Optional[str] = None
    prompt_text: Optional[str] = None
    speed: float = 1.0
    strategy: GenerationStrategy = GenerationStrategy.BALANCED
    enable_preprocessing: bool = True
    enable_pitch_shift: bool = True
    callback: Optional[Callable[[int, str], None]] = None


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    generation_time: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ==================== 抽象适配器接口 ====================

class VoiceGenerationAdapter(ABC):
    """语音生成适配器抽象基类"""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        生成语音

        Args:
            request: 生成请求

        Returns:
            GenerationResult: 生成结果
        """
        pass

    @abstractmethod
    def get_adapter_name(self) -> str:
        """获取适配器名称"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查适配器是否可用"""
        pass

    def preprocess_audio(self, audio_path: str) -> Tuple[str, bool]:
        """
        预处理音频（可选实现）

        Args:
            audio_path: 音频路径

        Returns:
            (处理后的路径, 是否成功)
        """
        return audio_path, True

    def postprocess_audio(self, audio_path: str, pitch_shift: float) -> Tuple[str, bool]:
        """
        后处理音频（可选实现）

        Args:
            audio_path: 音频路径
            pitch_shift: 音调调整值

        Returns:
            (处理后的路径, 是否成功)
        """
        return audio_path, True


# ==================== CosyVoice适配器实现 ====================

class CVCloneAdapter(VoiceGenerationAdapter):
    """
    CosyVoice适配器

    将CV_clone.CosyService适配到我们的接口
    """

    def __init__(self):
        self._service = None
        self._lock = threading.Lock()
        self._initialize_service()

    def _initialize_service(self):
        """初始化CosyVoice服务"""
        try:
            from backend.CV_clone import get_cosy_service

            logger.info("[CVCloneAdapter] 初始化CosyVoice服务...")
            self._service = get_cosy_service()
            logger.info("[CVCloneAdapter] CosyVoice服务初始化成功")

        except Exception as e:
            logger.error(f"[CVCloneAdapter] CosyVoice服务初始化失败: {e}")
            self._service = None

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """生成语音"""
        start_time = time.time()

        try:
            if not self.is_available():
                return GenerationResult(
                    success=False,
                    error_message="CosyVoice服务不可用"
                )

            logger.info(f"[CVCloneAdapter] 开始语音生成")
            logger.info(f"  文本: {request.text[:50]}...")
            logger.info(f"  参考音频: {request.reference_audio}")
            logger.info(f"  音调调整: {request.pitch_shift}")

            # 预处理参考音频
            ref_audio = request.reference_audio
            if request.enable_preprocessing:
                ref_audio, preprocess_ok = self.preprocess_audio(ref_audio)
                if preprocess_ok:
                    logger.info(f"[CVCloneAdapter] 使用预处理后的音频: {ref_audio}")
                else:
                    logger.warning("[CVCloneAdapter] 预处理失败,使用原始音频")
                    ref_audio = request.reference_audio

            # 调用CosyVoice服务
            cosy_result = self._service.clone_voice(
                text=request.text,
                reference_audio_path=ref_audio,
                prompt_text=request.prompt_text,
                output_filename=request.output_path,
                speed=request.speed
            )

            generation_time = time.time() - start_time

            # 检查生成结果
            if cosy_result.is_valid:
                output_path = cosy_result.audio_path

                # 后处理音频（音调调整）
                if request.enable_pitch_shift and request.pitch_shift != 0:
                    output_path, pitch_ok = self.postprocess_audio(
                        output_path,
                        request.pitch_shift
                    )
                    if pitch_ok:
                        logger.info(f"[CVCloneAdapter] 音调调整完成: {request.pitch_shift}")
                    else:
                        logger.warning("[CVCloneAdapter] 音调调整失败,使用原始音频")

                # 构建元数据
                metadata = {
                    "duration": cosy_result.audio_metadata.duration if cosy_result.audio_metadata else 0,
                    "sample_rate": cosy_result.audio_metadata.sample_rate if cosy_result.audio_metadata else 24000,
                    "file_size": cosy_result.audio_metadata.file_size if cosy_result.audio_metadata else 0,
                    "preprocessed": request.enable_preprocessing,
                    "pitch_shifted": request.enable_pitch_shift and request.pitch_shift != 0,
                    "pitch_value": request.pitch_shift,
                }

                logger.info(f"[CVCloneAdapter] 语音生成成功: {output_path}")
                logger.info(f"  耗时: {generation_time:.2f}s")

                return GenerationResult(
                    success=True,
                    output_path=output_path,
                    generation_time=generation_time,
                    metadata=metadata
                )
            else:
                error_msg = cosy_result.error_message or "生成失败"
                logger.error(f"[CVCloneAdapter] 语音生成失败: {error_msg}")

                return GenerationResult(
                    success=False,
                    error_message=error_msg,
                    generation_time=generation_time
                )

        except Exception as e:
            logger.error(f"[CVCloneAdapter] 生成异常: {e}", exc_info=True)
            return GenerationResult(
                success=False,
                error_message=str(e),
                generation_time=time.time() - start_time
            )

    def preprocess_audio(self, audio_path: str) -> Tuple[str, bool]:
        """预处理音频"""
        try:
            # 检查是否需要预处理
            # 如果已经预处理过（文件名包含_preprocessed_），跳过
            if "_preprocessed_" in Path(audio_path).name:
                logger.debug("[CVCloneAdapter] 音频已预处理,跳过")
                return audio_path, True

            logger.info(f"[CVCloneAdapter] 跳过预处理，直接使用原始音频: {audio_path}")
            # 暂时跳过预处理以避免bus error
            # CosyVoice内置了音频处理功能，可以直接使用原始音频
            return audio_path, True

        except Exception as e:
            logger.error(f"[CVCloneAdapter] 预处理异常: {e}")
            return audio_path, False

    def postprocess_audio(self, audio_path: str, pitch_shift: float) -> Tuple[str, bool]:
        """后处理音频（音调调整）"""
        try:
            if pitch_shift == 0:
                return audio_path, True

            logger.info(f"[CVCloneAdapter] 开始音调调整: {pitch_shift}")

            # 导入pitch_shift模块
            from backend.pitch_shift import shift_audio_pitch

            # 执行音调调整
            result = shift_audio_pitch(
                audio_path=audio_path,
                pitch_steps=pitch_shift,
                quality="balanced"
            )

            if result.success:
                logger.info(f"[CVCloneAdapter] 音调调整成功: {result.output_path}")
                return result.output_path, True
            else:
                logger.warning(f"[CVCloneAdapter] 音调调整失败: {result.error_message}")
                return audio_path, False

        except ImportError:
            logger.warning("[CVCloneAdapter] pitch_shift模块不可用,跳过音调调整")
            return audio_path, False
        except Exception as e:
            logger.error(f"[CVCloneAdapter] 音调调整异常: {e}")
            return audio_path, False

    def get_adapter_name(self) -> str:
        return "CosyVoice"

    def is_available(self) -> bool:
        """检查CosyVoice是否可用"""
        try:
            if self._service is None:
                return False

            status = self._service.get_service_status()
            return status.get('cosyvoice_available', False)

        except Exception as e:
            logger.error(f"[CVCloneAdapter] 可用性检查失败: {e}")
            return False

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            if self._service is None:
                return {"available": False, "error": "Service not initialized"}

            return self._service.get_comprehensive_status()

        except Exception as e:
            logger.error(f"[CVCloneAdapter] 获取服务状态失败: {e}")
            return {"available": False, "error": str(e)}


# ==================== 模拟适配器（用于测试） ====================

class MockAdapter(VoiceGenerationAdapter):
    """
    模拟适配器

    用于测试和开发,不需要真实的模型
    """

    def __init__(self, simulate_delay: float = 2.0):
        self.simulate_delay = simulate_delay

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """模拟生成语音"""
        start_time = time.time()

        try:
            logger.info(f"[MockAdapter] 模拟语音生成")
            logger.info(f"  文本: {request.text[:50]}...")
            logger.info(f"  参考音频: {request.reference_audio}")

            # 模拟处理时间
            time.sleep(self.simulate_delay)

            # 生成模拟输出文件
            from backend.path_manager import PathManager
            path_manager = PathManager()
            output_path = path_manager.get_temp_voice_path("mock")

            # 创建模拟音频文件
            with open(output_path, 'wb') as f:
                f.write(b'MOCK_AUDIO_DATA')

            generation_time = time.time() - start_time

            logger.info(f"[MockAdapter] 模拟生成完成: {output_path}")
            logger.info(f"  耗时: {generation_time:.2f}s")

            return GenerationResult(
                success=True,
                output_path=output_path,
                generation_time=generation_time,
                metadata={
                    "duration": 5.0,
                    "sample_rate": 24000,
                    "mock": True
                }
            )

        except Exception as e:
            logger.error(f"[MockAdapter] 模拟生成失败: {e}")
            return GenerationResult(
                success=False,
                error_message=str(e),
                generation_time=time.time() - start_time
            )

    def get_adapter_name(self) -> str:
        return "Mock"

    def is_available(self) -> bool:
        return True


# ==================== 适配器工厂 ====================

class VoiceAdapterFactory:
    """语音生成适配器工厂"""

    _adapters: Dict[str, VoiceGenerationAdapter] = {}
    _default_adapter: Optional[str] = None
    _lock = threading.Lock()

    @classmethod
    def register_adapter(cls, name: str, adapter: VoiceGenerationAdapter):
        """注册适配器"""
        with cls._lock:
            cls._adapters[name] = adapter
            logger.info(f"[VoiceAdapterFactory] 注册适配器: {name}")

            # 设置默认适配器（第一个注册的）
            if cls._default_adapter is None:
                cls._default_adapter = name
                logger.info(f"[VoiceAdapterFactory] 设置默认适配器: {name}")

    @classmethod
    def get_adapter(cls, name: Optional[str] = None) -> Optional[VoiceGenerationAdapter]:
        """
        获取适配器

        Args:
            name: 适配器名称,None表示使用默认适配器

        Returns:
            适配器实例或None
        """
        with cls._lock:
            if name is None:
                name = cls._default_adapter

            if name is None:
                logger.warning("[VoiceAdapterFactory] 没有可用的适配器")
                return None

            adapter = cls._adapters.get(name)
            if adapter is None:
                logger.warning(f"[VoiceAdapterFactory] 适配器不存在: {name}")
                return None

            return adapter

    @classmethod
    def create_best_adapter(cls) -> VoiceGenerationAdapter:
        """
        创建最佳可用适配器

        优先级: CosyVoice > Mock

        Returns:
            可用的适配器实例
        """
        # 尝试CosyVoice适配器
        try:
            cv_adapter = CVCloneAdapter()
            if cv_adapter.is_available():
                cls.register_adapter("cosyvoice", cv_adapter)
                logger.info("[VoiceAdapterFactory] 使用CosyVoice适配器")
                return cv_adapter
        except Exception as e:
            logger.warning(f"[VoiceAdapterFactory] CosyVoice适配器不可用: {e}")

        # 回退到模拟适配器
        logger.warning("[VoiceAdapterFactory] 回退到模拟适配器")
        mock_adapter = MockAdapter()
        cls.register_adapter("mock", mock_adapter)
        return mock_adapter

    @classmethod
    def get_available_adapters(cls) -> List[str]:
        """获取可用适配器列表"""
        with cls._lock:
            return list(cls._adapters.keys())


# ==================== 全局适配器实例 ====================

_global_adapter: Optional[VoiceGenerationAdapter] = None
_adapter_lock = threading.Lock()


def get_voice_adapter() -> VoiceGenerationAdapter:
    """
    获取全局语音生成适配器

    Returns:
        语音生成适配器实例
    """
    global _global_adapter

    with _adapter_lock:
        if _global_adapter is None:
            logger.info("[get_voice_adapter] 创建全局语音适配器...")
            _global_adapter = VoiceAdapterFactory.create_best_adapter()

        return _global_adapter


def set_voice_adapter(adapter: VoiceGenerationAdapter, name: str = "custom"):
    """设置全局语音生成适配器"""
    global _global_adapter

    with _adapter_lock:
        VoiceAdapterFactory.register_adapter(name, adapter)
        _global_adapter = adapter
        logger.info(f"[set_voice_adapter] 设置全局适配器: {name}")


# ==================== 便捷函数 ====================

def quick_generate(
    text: str,
    reference_audio: str,
    pitch_shift: float = 0.0,
    output_path: Optional[str] = None
) -> GenerationResult:
    """
    快速生成语音

    Args:
        text: 要生成的文本
        reference_audio: 参考音频路径
        pitch_shift: 音调调整值
        output_path: 输出路径

    Returns:
        GenerationResult: 生成结果
    """
    adapter = get_voice_adapter()

    if adapter is None:
        return GenerationResult(
            success=False,
            error_message="没有可用的语音生成适配器"
        )

    request = GenerationRequest(
        text=text,
        reference_audio=reference_audio,
        pitch_shift=pitch_shift,
        output_path=output_path
    )

    return adapter.generate(request)


if __name__ == "__main__":
    # 测试适配器
    print("=" * 60)
    print("语音生成适配器测试")
    print("=" * 60)

    # 创建适配器
    adapter = VoiceAdapterFactory.create_best_adapter()
    print(f"\n适配器名称: {adapter.get_adapter_name()}")
    print(f"适配器可用: {adapter.is_available()}")

    # 获取服务状态
    if hasattr(adapter, 'get_service_status'):
        status = adapter.get_service_status()
        print(f"\n服务状态:")
        for key, value in status.items():
            print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
