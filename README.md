# political-carousel

인스타그램(@politicsinsight360) 정치 캐러셀 자동화.

## 구조
```
scripts/        파이썬 스크립트 (토큰은 환경변수 IG_ACCESS_TOKEN / IG_USER_ID 에서만 읽음)
  ig_common.py         Graph API 호출 공통부 (graph.facebook.com, 토큰 마스킹)
  check_token.py       토큰·계정·게시 한도 확인
  make_test_images.py  1080x1080 테스트 JPEG 생성
  publish_carousel.py  캐러셀 게시
docs/           GitHub Pages 공개 루트 (인스타가 가져갈 이미지)
  test/           1단계 테스트 이미지
```

## 1단계 실행
```
python scripts/check_token.py
python scripts/make_test_images.py
git add docs && git commit -m "test images" && git push   # Pages 반영 대기
python scripts/publish_carousel.py --caption "테스트" <URL1> <URL2>
```
