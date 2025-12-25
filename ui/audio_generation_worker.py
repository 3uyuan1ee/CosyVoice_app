"""
音频生成工作线程 - 在后台线程执行音频生成任务
"""

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from typing import Optional, Dict, Any
from loguru import logger
import time


class GenerationSignals(QObject):
    """生成信号集合"""
    progress = pyqtSignal(int, str)  # percentage, status_text
    finished = pyqtSignal(bool, str, str)  # success, message, output_path
    error = pyqtSignal(str)  # error_message
    started = pyqtSignal()  # generation started


class AudioGenerationWorker(QThread):
    """
    音频生成工作线程

    在独立线程中执行音频生成任务，避免阻塞UI
    """

    def __init__(self, reference_audio: str, text: str, pitch_shift: int = 0,
                 model_type: str = "cosyvoice3_2512", language: Optional[str] = None, parent=None):
        super().__init__(parent)

        self.reference_audio = reference_audio
        self.text = text
        self.pitch_shift = pitch_shift
        self.model_type = model_type
        self.language = language  # 参考音频语言 (None=自动检测)

        self.signals = GenerationSignals()
        self._is_cancelled = False
        self._is_running = True

        logger.info(f"AudioGenerationWorker created for text: {text[:50]}...")

    def run(self):
        """执行音频生成任务"""
        try:
            logger.info("Starting audio generation...")
            self.signals.started.emit()

            # 阶段1: 验证输入 (10%)
            self._update_progress(10, "Validating input...")

            if not self._validate_input():
                self.signals.error.emit("Invalid input parameters")
                return

            if self._is_cancelled:
                self.signals.error.emit("Generation cancelled")
                return

            # 阶段2: 加载模型 (20%)
            self._update_progress(20, "Loading voice model...")

            voice_generator = self._get_voice_generator()
            if not voice_generator:
                self.signals.error.emit("Failed to load voice generator")
                return

            if self._is_cancelled:
                self.signals.error.emit("Generation cancelled")
                return

            # 阶段3: 预处理参考音频 (30%)
            self._update_progress(30, "Preprocessing reference audio...")

            preprocessed_audio = self._preprocess_reference_audio()
            if not preprocessed_audio:
                self.signals.error.emit("Failed to preprocess audio")
                return

            if self._is_cancelled:
                self.signals.error.emit("Generation cancelled")
                return

            # 阶段4: 生成音频 (40-80%)
            self._update_progress(40, "Generating audio...")

            output_path = self._generate_audio(voice_generator, preprocessed_audio)

            if not output_path or self._is_cancelled:
                if self._is_cancelled:
                    self.signals.error.emit("Generation cancelled")
                else:
                    self.signals.error.emit("Audio generation failed")
                return

            # 阶段5: 后处理 (90%)
            self._update_progress(90, "Post-processing audio...")

            final_output = self._post_process_audio(output_path)

            if not final_output:
                self.signals.error.emit("Post-processing failed")
                return

            # 完成 (100%)
            self._update_progress(100, "Complete!")

            if self._is_cancelled:
                self.signals.error.emit("Generation cancelled")
            else:
                self.signals.finished.emit(
                    True,
                    "Audio generated successfully",
                    final_output
                )
                logger.info(f"Audio generation completed: {final_output}")

        except Exception as e:
            logger.error(f"Audio generation error: {str(e)}", exc_info=True)
            self.signals.error.emit(f"Generation error: {str(e)}")

    def _validate_input(self) -> bool:
        """验证输入参数"""
        try:
            import os

            # 检查参考音频
            if not os.path.exists(self.reference_audio):
                logger.error(f"Reference audio not found: {self.reference_audio}")
                return False

            # 检查文本
            if not self.text or not self.text.strip():
                logger.error("Text is empty")
                return False

            # 检查音调范围
            if not -12 <= self.pitch_shift <= 12:
                logger.error(f"Pitch shift out of range: {self.pitch_shift}")
                return False

            logger.info("Input validation passed")
            return True

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    def _get_voice_generator(self):
        """获取语音生成器"""
        try:
            from backend.voice_generation_adapter import get_voice_adapter

            adapter = get_voice_adapter()

            # 检查适配器可用性
            if not adapter.is_available():
                logger.error("Voice generation adapter not available")
                return None

            logger.info(f"Voice generator loaded: {adapter.get_adapter_name()}")
            return adapter

        except Exception as e:
            logger.error(f"Error loading voice generator: {e}")
            return None

    def _preprocess_reference_audio(self) -> Optional[str]:
        """预处理参考音频"""
        try:
            # 使用适配器的预处理功能
            if hasattr(self._get_voice_generator(), 'preprocess_audio'):
                voice_generator = self._get_voice_generator()
                processed_path, success = voice_generator.preprocess_audio(self.reference_audio)

                if success:
                    logger.info(f"Audio preprocessed: {processed_path}")
                    return processed_path
                else:
                    logger.warning("Audio preprocessing failed, using original")
                    return self.reference_audio
            else:
                # 适配器不支持预处理,直接返回原始路径
                logger.info(f"Using reference audio: {self.reference_audio}")
                return self.reference_audio

        except Exception as e:
            logger.error(f"Error preprocessing audio: {e}")
            return self.reference_audio

    def _generate_audio(self, voice_generator, reference_audio: str) -> Optional[str]:
        """生成音频"""
        try:
            from backend.voice_generation_adapter import GenerationRequest
            from backend.path_manager import PathManager
            import os

            path_manager = PathManager()

            # 生成输出路径
            output_path = path_manager.get_temp_voice_path("generated")

            logger.info("Starting audio generation...")

            # 创建生成请求
            request = GenerationRequest(
                text=self.text,
                reference_audio=reference_audio,
                pitch_shift=self.pitch_shift,
                output_path=None,  # None让适配器自动生成唯一文件名
                strategy="balanced",
                enable_preprocessing=False,  # 已经在前期预处理过
                enable_pitch_shift=True,
                model_type=self.model_type,  # 传递模型类型
                language=self.language,  # 传递参考音频语言
                callback=lambda p, s: self._update_progress(p, s) if 40 <= p <= 80 else None
            )

            # 调用适配器生成音频
            result = voice_generator.generate(request)

            # 更新进度 (40% -> 80%)
            for progress in range(40, 85, 5):
                if self._is_cancelled:
                    return None
                self._update_progress(progress, f"Generating audio... {progress}%")
                time.sleep(0.1)  # 给UI更新的时间

            if result.success and result.output_path:
                logger.info(f"Audio generated to: {result.output_path}")

                # 更新元数据
                if result.metadata:
                    logger.info(f"  Duration: {result.metadata.get('duration', 'N/A')}s")
                    logger.info(f"  Sample rate: {result.metadata.get('sample_rate', 'N/A')}Hz")
                    logger.info(f"  Preprocessed: {result.metadata.get('preprocessed', False)}")
                    logger.info(f"  Pitch shifted: {result.metadata.get('pitch_shifted', False)}")

                return result.output_path
            else:
                error_msg = result.error_message or "Unknown error"
                logger.error(f"Audio generation failed: {error_msg}")
                return None

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return None

    def _post_process_audio(self, audio_path: str) -> Optional[str]:
        """后处理音频"""
        try:
            # 验证输出文件
            import os
            if not os.path.exists(audio_path):
                logger.error("Generated audio file not found")
                return None

            logger.info(f"Audio post-processing completed: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Error post-processing audio: {e}")
            return None

    def _update_progress(self, percentage: int, status_text: str):
        """更新进度"""
        if 0 <= percentage <= 100:
            self.signals.progress.emit(percentage, status_text)
            logger.debug(f"Progress: {percentage}% - {status_text}")

    def cancel(self):
        """取消生成"""
        logger.info("Cancelling audio generation...")
        self._is_cancelled = True
        self._is_running = False

    def stop(self):
        """停止线程"""
        self._is_running = False
