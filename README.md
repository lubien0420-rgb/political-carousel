# political-carousel

인스타그램(@politicsinsight360) 정치 캐러셀 자동화.

## 구조
```
scripts/        파이썬 스크립트 (토큰은 환경변수 IG_ACCESS_TOKEN / IG_USER_ID 에서만 읽음)
  ig_common.py         Graph API 호출 공통부 (graph.facebook.com, 토큰 마스킹)
  check_token.py       토큰·계정·게시 한도 확인
  make_test_images.py  1080x1080 테스트 JPEG 생성
  publish_carousel.py  캐러셀 게시
  collect.py           [수집] 정치 RSS → 이슈 후보 순위
config/sources.json   수집 대상 RSS 목록
data/collected/       수집 결과 JSON (git 제외)
docs/           GitHub Pages 공개 루트 (인스타가 가져갈 이미지)
  test/           1단계 테스트 이미지
```

## 1단계: 업로드 테스트
```
python scripts/check_token.py
python scripts/make_test_images.py
git add docs && git commit -m "test images" && git push   # Pages 반영 대기
python scripts/publish_carousel.py --caption "테스트" <URL1> <URL2>
```

## 2단계: 수집
```
python scripts/collect.py                 # 최근 12시간, 상위 15개
python scripts/collect.py --hours 24 --top 20
```
여러 언론사가 함께 다룬 이슈일수록 순위가 높다 (점수 = 언론사 수×10 + 기사 수×2 − 경과 시간).

## 3단계: 팩트 리서처
```
python scripts/research_pack.py --rank 1          # 순위 지정 → 기사 본문 묶음 (data/research/<폴더>/pack.md)
# Claude Code가 prompts/fact_researcher.md 규칙대로 같은 폴더에 factsheet.json 작성
python scripts/check_factsheet.py data/research/<폴더>   # 출처·인용 원문·'확인' 기준 검증
```
- `scripts/article_text.py`: 언론사 기사 본문 추출 (JTBC는 페이지 내 JSON에서 추출)
## 4단계: 카피 (republican-short 규격)
```
# Claude Code가 prompts/copywriter.md 규칙대로 같은 폴더에 copy.json 작성
python scripts/check_copy.py data/research/<폴더>
```
검증: 본문 450~550자·제목 3·해시태그 20·표지 3안(실제 글자 폭)·카드 블록 3 / 큰따옴표 인용 원문 대조 / 숫자는 팩트시트에 있어야 함 / cautions 대응 / 이전 글과 전환·마무리 반복

## 5단계: 검수
```
python scripts/review.py data/research/<폴더>              # 기계 검증 + 위험 표현 점검 → review_input.md
# 검수자가 prompts/reviewer.md 체크리스트대로 review.json 작성 (문장별 근거 매핑 + 지적 + 판정)
python scripts/review.py data/research/<폴더> --validate   # 판정 확인: 통과일 때만 종료코드 0
```
판정: 치명 → 게시 불가 / 중요 → 수정 필요(카피로 되돌려 재검수, review_rN.json 보관) / 경미만 → 통과

## 6단계: 승인 (사람)
```
python scripts/approve.py data/research/<폴더>                                 # 승인 패키지 미리보기
python scripts/approve.py data/research/<폴더> --title 2 --cover 1 --ack-notes  # 승인 (사용자가 직접)
python scripts/approve.py data/research/<폴더> --reject "사유"                  # 반려
python scripts/approve.py data/research/<폴더> --check                         # 유효성 (다음 단계가 사용)
```
승인은 copy/factsheet/review 파일 해시에 묶임 → 승인 뒤 수정하면 자동 무효.

## 7단계: 디자이너
```
python scripts/design.py data/research/<폴더>                  # 승인본 → design/carousel_politics_1x1.html
python scripts/design.py data/research/<폴더> --draft --cover 2 # 승인 전 레이아웃 시안 (업로드 불가)
```
템플릿: templates/carousel_politics_1x1.html (republican-short, 1080×1080 2장)

## 8단계: 사진 삽입 (수동)
HTML을 브라우저로 열기 → 카드 1·2 배경 사진 업로드 → '전체 2장 다운로드' → slide1.png, slide2.png 를 `<폴더>/final/` 에 넣기

## 9단계: 업로드 + 로그
```
python scripts/upload.py data/research/<폴더> --dry-run   # 변환·점검만
python scripts/upload.py data/research/<폴더>             # JPEG 변환 → docs/posts/<id>/ push → Pages 대기 → 게시
```
승인 유효 + final 이미지 2장 + 미게시(published.json 없음)일 때만 진행. 결과는 `<폴더>/published.json`, 모든 시도는 `logs/posts.jsonl`.

## 참고
- 조선일보는 본문이 스크립트로 로드돼 요약만, 한겨레·중앙일보는 Google 뉴스 링크라 본문 미수집(제목만)
