"""
음성 파일(MP4/WAV 등)을 텍스트로 변환하는 모듈
faster-whisper를 사용하여 로컬에서 실행
"""
import os
from pathlib import Path
from faster_whisper import WhisperModel
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# faster-whisper 모델 크기 옵션
# tiny, base, small, medium, large-v2, large-v3
# CPU 환경에서는 small 또는 medium 권장
DEFAULT_MODEL_SIZE = "large-v3"


class Transcriber:
    def __init__(self, model_size: str = DEFAULT_MODEL_SIZE):
        self.model_size = model_size
        self.model = None

    def _load_model(self):
        if self.model is None:
            console.print(f"[cyan]Whisper 모델 로딩 중: {self.model_size}[/cyan]")
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",  # CPU에서 속도/메모리 최적화
            )
            console.print("[green]모델 로드 완료[/green]")

    def transcribe(self, audio_path: str | Path) -> str:
        """
        오디오/비디오 파일을 받아 전체 텍스트를 반환합니다.
        faster-whisper는 ffmpeg가 설치되어 있으면 MP3, M4A 등을 직접 처리합니다.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {audio_path}")

        self._load_model()

        console.print(f"[cyan]음성 인식 시작: {audio_path.name}[/cyan]")

        segments_list = []
        with Progress(
            SpinnerColumn("line"),  # ASCII 스피너 (|/-\) - Windows CP949 호환
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("변환 중...", total=None)

            segments, info = self.model.transcribe(
                str(audio_path),
                language="ko",
                beam_size=5,
                vad_filter=True,          # 음성 구간만 처리 (속도 향상)
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            for segment in segments:
                segments_list.append(segment.text.strip())
                progress.update(task, description=f"[{segment.start:.0f}s] {segment.text[:40]}...")

        transcript = " ".join(segments_list)
        console.print(f"[green]음성 인식 완료 - 총 {len(transcript)}자[/green]")
        return transcript


def transcribe_file(audio_path: str | Path, model_size: str = DEFAULT_MODEL_SIZE) -> str:
    """편의 함수: 파일 하나를 바로 변환"""
    transcriber = Transcriber(model_size=model_size)
    return transcriber.transcribe(audio_path)
