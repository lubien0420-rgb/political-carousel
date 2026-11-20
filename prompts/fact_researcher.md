# 팩트 리서처 규칙

입력: `data/research/<폴더>/pack.md` (자료 묶음)
출력: 같은 폴더의 `factsheet.json` → `python scripts/check_factsheet.py <폴더>` 통과 필수

## 역할
카피 단계(보수 성향 republican-short 규격)가 **사실 위에서만** 주장하도록, 중립적인 사실 기반을 만든다.
팩트시트 자체에는 평가·형용사·의견을 넣지 않는다. 의견은 반드시 "누가 그렇게 주장했다"로만 기록한다.

## 원칙
1. **자료 묶음 밖의 사실은 쓰지 않는다.** 배경지식이 필요하면 `background`에 넣고 `sources`를 비우지 말 것. 출처를 댈 수 없으면 쓰지 않는다.
2. **모든 항목에 출처 ID**(`S1`, `S2` …)를 단다.
3. `status` 기준
   - `확인`: 서로 다른 언론사 2곳 이상이 같은 내용을 보도
   - `단독`: 1곳만 보도 (카피에서 단정 표현 금지)
   - `불일치`: 언론사 간 내용(수치·시점·발언)이 다름 → `disputes`에도 기록
4. **인용(`quotes`)은 원문 그대로** 옮긴다. 출처 본문에 글자 그대로 있어야 한다(검증 스크립트가 확인). 줄이려면 앞뒤를 자르되 중간을 바꾸지 않는다.
5. 발언자는 이름 + 소속/직함. 익명 관계자는 `"익명 관계자(언론사 표기)"`.
6. 수치(`numbers`)는 단위·기준 시점을 함께 적는다.
7. 양측 입장(`positions`)은 여당·야당·정부·기타 당사자를 **모두** 기록한다. 한쪽만 있으면 `cautions`에 적는다.
8. 아직 일어나지 않은 일(예정·전망)은 `next`에만 넣고 사실처럼 쓰지 않는다.
9. `cautions`: 카피가 넘으면 안 되는 선 (예: "유죄 확정 아님", "당론 채택이지 발의 전").

## factsheet.json 형식
```json
{
  "issue": "자료 묶음의 issue 그대로",
  "pack": "pack.json",
  "researched_at": "ISO 시각",
  "one_line": "중립 한 줄 요약 (60자 이내)",
  "facts":     [{"text": "...", "status": "확인|단독|불일치", "sources": ["S1","S3"]}],
  "timeline":  [{"when": "2026-11-20", "what": "...", "sources": ["S2"]}],
  "numbers":   [{"value": "3분의 1", "meaning": "...", "sources": ["S4"]}],
  "quotes":    [{"speaker": "이름", "role": "소속·직함", "quote": "원문 그대로", "sources": ["S5"]}],
  "positions": [{"side": "민주당|국민의힘|정부|기타:…", "summary": "...", "sources": ["S1"]}],
  "disputes":  [{"point": "...", "versions": [{"claim": "...", "sources": ["S2"]}]}],
  "background":[{"text": "...", "sources": ["S6"]}],
  "next":      [{"text": "...", "sources": ["S1"]}],
  "cautions":  ["..."]
}
```
