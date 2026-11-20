# 카피 규칙 (republican-short 규격 + 파이프라인 제약)

입력: `data/research/<폴더>/factsheet.json` (check_factsheet 통과본) + `pack.md`
출력: 같은 폴더의 `copy.json` → `python scripts/check_copy.py <폴더>` 통과 필수
기준 스펙: republican-short 스킬 (숏폼 본문·제목 3·해시태그 20·캐러셀 문구). HTML은 이 단계에서 만들지 않는다(디자이너 단계).

## 파이프라인 추가 제약 (스킬보다 우선)
1. **사실은 factsheet에 있는 것만.** 웹 검색으로 새 사실을 들이지 않는다. 필요하면 팩트 리서처 단계로 되돌린다.
2. `status: 단독` 사실은 단정하지 않는다("~라고 보도됐다"). `불일치`·`disputes` 항목은 쓰지 않거나 양쪽을 다 밝힌다.
3. **큰따옴표 인용은 기사 원문 그대로**(축약은 앞뒤 자르기만). 검증기가 원문 대조한다. 강조·조어는 작은따옴표로.
4. 본문·카드의 **모든 숫자는 factsheet에 있어야** 한다.
5. factsheet의 `cautions`를 하나씩 어떻게 지켰는지 `caution_check`에 적는다.
6. 의견은 후반부에서만, 1인칭으로. 한쪽 진영 주장(예: '청구서', '국면전환')은 발언자를 밝혀 인용.
7. 비하 별명·욕설·집단 비하·지어낸 인용 금지(스킬 원칙 그대로).
8. 전환 문구·마지막 문장은 이전 copy.json들과 겹치지 않게(검증기가 비교).

## 어투 (운영자 지정, 2026-11-21)
- 의견부·카드 하단 주장은 **상대를 직접 찌르는 조롱·도발조**로 쓴다. 점잖은 논설체("~는 사법부 길들이기다") 대신
  "막상 탄핵하려니 니들도 쫄리지?", "할 거면 날짜부터 박아라." 같은 반말 직격.
- 카드 하단 주장(claim)은 이 조롱조 한 줄을 기본으로 한다. 본문 의견부에 같은 펀치라인이 있어야 한다(압축 관계).
- 조롱의 근거는 반드시 앞 팩트에 건다 (예: '쫄리지?' ← 발의 날짜 미확정 + 당내 공개 반대).
- 대상은 정당·정치인과 그 공적 행위까지. 지지자·국민·지역 등 집단으로 넓히지 않는다. 욕설·비하 별명은 여전히 금지.

## copy.json 형식
```json
{
  "issue": "factsheet의 issue",
  "factsheet": "factsheet.json",
  "written_at": "ISO 시각",
  "titles": [
    {"type": "숫자 충격형", "text": "..."},
    {"type": "도발 단언형", "text": "..."},
    {"type": "호기심 갭형", "text": "..."}
  ],
  "body": {
    "paragraphs": ["현황 문단", "...", "전환 한 줄", "의견 문단", "..."],
    "transition": "전환 한 줄 (paragraphs 안에도 그대로 포함)",
    "closing": "마지막 문장",
    "source_note": "*이 글은 ~보도를 바탕으로 한 개인적인 정치 논평입니다.*"
  },
  "hashtags": ["#조희대", "... 정확히 20개"],
  "cover": {
    "label": "사건 · 날짜",
    "options": [
      {"type": "독자 직격", "line1": "...", "line2": "...", "em": "line2 안의 강조 단어"}
    ]
  },
  "summary_card": {
    "title": "단정형 제목",
    "blocks": [{"icon": "⚖️", "label": "ENGLISH LABEL", "num": "큰 숫자/키워드", "text": "한 줄 설명"}],
    "counter": {"label": "여권 입장", "text": "..."},
    "claim": "본문 후반부 핵심 단언 압축"
  },
  "caution_check": [{"caution": "factsheet cautions 원문", "handled": "어떻게 지켰나"}],
  "fact_refs": ["본문에 쓴 사실의 factsheet 위치, 예: facts[1]", "numbers[2]"]
}
```
