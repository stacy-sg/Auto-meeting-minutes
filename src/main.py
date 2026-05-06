"""
회의록 자동 작성 CLI
사용법: python -m src.main run <입력파일> [옵션]
지원 형식: MP3, M4A, WAV 등 ffmpeg가 지원하는 오디오 파일
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import sys

# Windows CP949 콘솔 인코딩 문제 방지
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="회의록자동작성",
    help="MP4/오디오 파일로부터 회의록을 자동 생성합니다.",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    input_file: Path = typer.Argument(..., help="입력 파일 경로 (MP3, M4A, WAV 등)"),
    output_format: str = typer.Option(
        "docx",
        "--format", "-f",
        help="출력 형식: docx | pdf | hwp",
    ),
    output_name: Optional[str] = typer.Option(
        None,
        "--output", "-o",
        help="출력 파일명 (확장자 제외). 미입력시 자동 생성",
    ),
    model_size: str = typer.Option(
        "large-v3",
        "--whisper-model", "-w",
        help="Whisper 모델 크기: tiny | base | small | medium | large-v3",
    ),
    llm_model: str = typer.Option(
        "qwen3.5:0.8b",
        "--llm-model", "-l",
        help="Ollama 모델명 (ollama list 로 확인)",
    ),
    transcript_only: bool = typer.Option(
        False,
        "--transcript-only", "-t",
        help="음성 인식 결과만 출력 (문서 생성 안 함)",
    ),
    transcript_file: Optional[Path] = typer.Option(
        None,
        "--from-transcript",
        help="녹취 텍스트 파일에서 직접 요약 (음성 인식 건너뜀)",
    ),
    attendees: Optional[str] = typer.Option(
        None,
        "--attendees", "-a",
        help="참석자 직접 입력 (쉼표 구분, 예: '홍길동, 김철수, 이영희'). 미입력시 AI가 추출",
    ),
):
    """
    회의 녹음 파일(MP4 등)을 받아 자동으로 회의록을 생성합니다.
    """
    console.print(
        Panel.fit(
            "[bold cyan]회의록 자동 작성 시스템[/bold cyan]",
            border_style="cyan",
        )
    )

    # ── 1단계: 음성 인식 ──────────────────────────
    if transcript_file:
        console.print(f"[yellow]녹취 파일 사용: {transcript_file}[/yellow]")
        transcript = transcript_file.read_text(encoding="utf-8")
    else:
        if not input_file.exists():
            console.print(f"[red]입력 파일이 존재하지 않습니다: {input_file}[/red]")
            raise typer.Exit(1)

        from src.transcriber import Transcriber
        transcriber = Transcriber(model_size=model_size)
        transcript = transcriber.transcribe(input_file)

        # 녹취 텍스트 저장 (나중에 재사용 가능)
        transcript_out = Path("output") / f"{input_file.stem}_transcript.txt"
        transcript_out.parent.mkdir(exist_ok=True)
        transcript_out.write_text(transcript, encoding="utf-8")
        console.print(f"[dim]녹취 텍스트 저장: {transcript_out}[/dim]")

    if transcript_only:
        console.print("\n[bold]── 녹취 결과 ──[/bold]")
        console.print(transcript)
        raise typer.Exit(0)

    # ── 2단계: AI 요약 ────────────────────────────
    from src.summarizer import Summarizer
    summarizer = Summarizer(model=llm_model)
    meeting_data = summarizer.summarize(transcript)

    # 참석자 직접 입력값이 있으면 AI 추출값 덮어쓰기
    if attendees:
        meeting_data["참석자"] = [a.strip() for a in attendees.split(",") if a.strip()]
        console.print(f"[yellow]참석자 적용: {', '.join(meeting_data['참석자'])}[/yellow]")

    # 요약 결과 미리보기
    _print_summary(meeting_data)

    # ── 3단계: 문서 생성 ──────────────────────────
    from src.doc_generator import generate_document
    output_path = generate_document(
        meeting_data,
        output_format=output_format,
        output_filename=output_name,
    )

    console.print(
        Panel.fit(
            f"[bold green]완료![/bold green] 저장 위치: [underline]{output_path}[/underline]",
            border_style="green",
        )
    )


def _print_summary(data: dict):
    """회의록 요약을 터미널에 간략히 출력"""
    table = Table(title="회의록 요약", show_header=False, box=None)
    table.add_column("항목", style="bold cyan", width=12)
    table.add_column("내용")

    table.add_row("회의명", data.get("회의명", "-"))
    table.add_row("일시", data.get("일시", "-"))
    table.add_row("장소", data.get("장소", "-"))
    table.add_row("참석자", ", ".join(data.get("참석자", [])) or "-")

    decisions = data.get("결정사항", [])
    table.add_row("결정사항", f"{len(decisions)}건")

    actions = data.get("액션아이템", [])
    table.add_row("액션아이템", f"{len(actions)}건")

    console.print(table)


@app.command("list-models")
def list_models():
    """설치된 Ollama 모델 목록 출력"""
    import subprocess
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    console.print(result.stdout)


if __name__ == "__main__":
    app()
