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
