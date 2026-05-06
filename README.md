# 회의록 자동 작성 시스템

MP3/M4A 회의 녹음 파일을 입력받아 Whisper로 음성 인식 후, Ollama LLM으로 요약하여
HWP / DOCX / PDF 형식의 회의록을 자동 생성합니다.

## 기술 스택

| 역할 | 도구 |
|------|------|
| 음성 인식 | faster-whisper (로컬, CPU/GPU) |
| AI 요약 | Ollama (로컬 LLM, 기본: qwen3.5:4b) |
| DOCX 생성 | python-docx |
| PDF 변환 | docx2pdf |
| HWP 생성 | win32com (한컴 HWP 설치 필요) |
| CLI | typer + rich |

## 사전 요구사항

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) 설치 및 PATH 등록
- [Ollama](https://ollama.com/) 설치 및 모델 다운로드
- HWP 출력 시 한글과컴퓨터 한글 설치 필요

## 설치

```bash
# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 패키지 설치
pip install -r requirements.txt

# Ollama 모델 다운로드 (예시)
ollama pull qwen3.5:4b
```

## 사용법

```bash
# 가상환경 활성화
venv\Scripts\activate

# 기본 실행 (DOCX 생성)
python -m src.main input/회의녹음.mp3

# PDF로 생성
python -m src.main input/회의녹음.mp3 --format pdf

# HWP로 생성
python -m src.main input/회의녹음.mp3 --format hwp

# 출력 파일명 지정
python -m src.main input/회의녹음.mp3 --format docx --output 2025년9월회의록

# 음성 인식 결과만 확인
python -m src.main input/회의녹음.mp3 --transcript-only

# 기존 녹취 텍스트로 문서만 재생성
python -m src.main dummy.mp4 --from-transcript output/transcript.txt --format hwp

# 다른 Whisper 모델 사용 (더 빠르게)
python -m src.main input/회의녹음.mp3 --whisper-model small

# 다른 LLM 모델 사용
python -m src.main input/회의녹음.mp3 --llm-model qwen3.5:0.8b
```

## 폴더 구조

```
회의록자동작성/
├── venv/                  # 가상환경 (git 제외)
├── templates/             # HWP 템플릿 보관
│   └── 회의록_template.hwp
├── input/                 # 입력 MP4 파일 넣는 곳
├── output/                # 생성된 회의록 저장
├── src/
│   ├── __init__.py
│   ├── transcriber.py     # faster-whisper 음성 인식
│   ├── summarizer.py      # Ollama LLM 요약
│   ├── doc_generator.py   # 문서 생성 (DOCX/PDF/HWP)
│   └── main.py            # CLI 진입점
├── .env                   # 환경 설정
├── requirements.txt
└── README.md
```

## HWP 템플릿 설정

`templates/회의록_template.hwp` 파일 내에 아래 플레이스홀더를 삽입하면
자동으로 내용이 채워집니다.

| 플레이스홀더 | 치환 내용 |
|-------------|---------|
| `{{회의명}}` | 회의 제목 |
| `{{일시}}` | 회의 날짜/시간 |
| `{{장소}}` | 회의 장소 |
| `{{참석자}}` | 참석자 목록 |
| `{{안건}}` | 안건 목록 |
| `{{논의내용}}` | 주요 논의 내용 |
| `{{결정사항}}` | 결정 사항 |
| `{{액션아이템}}` | 액션 아이템 |
| `{{다음회의}}` | 다음 회의 일정 |
| `{{특이사항}}` | 기타 메모 |

## 환경 변수 (.env)

```env
OLLAMA_HOST=http://localhost:11434
WHISPER_MODEL=medium
LLM_MODEL=qwen3.5:4b
OUTPUT_FORMAT=docx
```
