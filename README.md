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

## 참고
- 조선일보는 본문이 스크립트로 로드돼 요약만, 한겨레·중앙일보는 Google 뉴스 링크라 본문 미수집(제목만)
