"""
Whisper로 변환된 텍스트를 Ollama LLM을 통해 구조화된 회의록으로 요약
"""
import json
import re
from datetime import datetime
from rich.console import Console

import ollama

console = Console()

DEFAULT_MODEL = "qwen3.5:0.8b"

SYSTEM_PROMPT = """당신은 회의록 작성 전문가입니다.
회의에 참석하지 않은 사람도 이 회의록만 보면 어떤 회의였는지 즉시 파악할 수 있도록 작성합니다.

작성 원칙:
- 녹취에 있는 내용만 사용하고 추측하거나 내용을 만들어내지 않습니다.
- 인사말, 잡담, 중복 발언, 말 더듬 등 회의와 무관한 내용은 모두 제외합니다.
- 각 항목은 핵심만 간결하게 씁니다. 장황하게 쓰지 않습니다.
- 반드시 아래 JSON 형식으로만 응답하십시오. 마크다운 코드블록 없이 순수 JSON만 출력합니다.
"""

# /no_think 를 user 메시지 앞에 붙여 qwen3 계열 thinking 모드 비활성화
SUMMARY_PROMPT_TEMPLATE = """/no_think
다음은 회의 녹취 텍스트입니다. 아래 규칙에 따라 회의록 JSON을 작성하십시오.

규칙:
1. 녹취에 명시된 내용만 사용합니다. 언급되지 않은 내용은 절대 만들어 쓰지 않습니다.
2. 담당자, 기한, 다음 회의 일정 등이 녹취에 없으면 반드시 빈 문자열 또는 빈 배열로 둡니다.
3. 불필요한 수식어, 반복, 인사말은 제거합니다.
4. 논의내용은 "무엇을 논의했고 어떤 결론이 났는지"를 한두 문장으로 요약합니다.
5. 결정사항은 실제로 결정된 것만 씁니다.

[녹취 텍스트]
{transcript}

[출력 형식 - 순수 JSON만 출력]
{{
  "회의명": "이 회의의 핵심 주제를 한 문장으로",
  "일시": "언급된 날짜/시간 (없으면 빈 문자열)",
  "장소": "언급된 장소 (없으면 빈 문자열)",
  "참석자": ["참석자1", "참석자2"],
  "안건": ["안건1", "안건2"],
  "주요_논의내용": [
    {{
      "안건": "안건 제목",
      "내용": "논의 내용과 결론을 2~3문장으로 간결하게"
    }}
  ],
  "결정사항": [
    "결정된 사항을 동사형으로 한 줄씩"
  ],
  "액션아이템": [
    {{
      "담당자": "담당자명 (불명확하면 미정)",
      "내용": "해야 할 일을 명확하게",
      "기한": "기한 (없으면 빈 문자열)"
    }}
  ],
  "다음회의": "다음 회의 일정 (없으면 빈 문자열)",
  "특이사항": "꼭 전달해야 할 기타 사항 (없으면 빈 문자열)"
}}"""


def _clean_llm_output(text: str) -> str:
    """LLM 출력에서 <think> 태그, 코드블록 등을 제거하고 순수 JSON만 추출"""
    # qwen3 계열의 <think>...</think> 제거
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # 마크다운 코드블록 제거
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.replace("```", "")
    return text.strip()


class Summarizer:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model

    def summarize(self, transcript: str) -> dict:
        """
        녹취 텍스트를 받아 구조화된 회의록 딕셔너리를 반환합니다.
        """
        console.print(f"[cyan]LLM 요약 시작 (모델: {self.model})[/cyan]")

        prompt = SUMMARY_PROMPT_TEMPLATE.format(transcript=transcript)

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                think=False,          # qwen3 계열 thinking 모드 비활성화
                options={"temperature": 0.3},
            )

            raw_output = response.message.content
            cleaned = _clean_llm_output(raw_output)

            # JSON 파싱
            meeting_data = json.loads(cleaned)
            console.print("[green]LLM 요약 완료[/green]")
            return meeting_data

        except json.JSONDecodeError as e:
            console.print(f"[yellow]JSON 파싱 실패, 텍스트 요약으로 대체합니다: {e}[/yellow]")
            return self._fallback_summary(transcript, raw_output)

        except Exception as e:
            console.print(f"[red]LLM 오류: {e}[/red]")
            raise

    def _fallback_summary(self, transcript: str, raw_output: str) -> dict:
        """JSON 파싱 실패 시 기본 구조로 반환"""
        return {
            "회의명": "회의록",
            "일시": "",
            "장소": "",
            "참석자": [],
            "안건": [],
            "주요_논의내용": [{"안건": "전체 내용", "내용": raw_output}],
            "결정사항": [],
            "액션아이템": [],
            "다음회의": "",
            "특이사항": f"원본 녹취: {transcript[:500]}...",
        }


def summarize_transcript(transcript: str, model: str = DEFAULT_MODEL) -> dict:
    """편의 함수"""
    summarizer = Summarizer(model=model)
    return summarizer.summarize(transcript)
