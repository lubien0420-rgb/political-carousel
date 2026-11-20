# political-carousel

?몄뒪?洹몃옩(@politicsinsight360) ?뺤튂 罹먮윭? ?먮룞??

## 援ъ“
```
scripts/        ?뚯씠???ㅽ겕由쏀듃 (?좏겙? ?섍꼍蹂??IG_ACCESS_TOKEN / IG_USER_ID ?먯꽌留??쎌쓬)
  ig_common.py         Graph API ?몄텧 怨듯넻遺 (graph.facebook.com, ?좏겙 留덉뒪??
  check_token.py       ?좏겙쨌怨꾩젙쨌寃뚯떆 ?쒕룄 ?뺤씤
  make_test_images.py  1080x1080 ?뚯뒪??JPEG ?앹꽦
  publish_carousel.py  罹먮윭? 寃뚯떆
docs/           GitHub Pages 怨듦컻 猷⑦듃 (?몄뒪?媛 媛?멸컝 ?대?吏)
  test/           1?④퀎 ?뚯뒪???대?吏
```

## 1?④퀎 ?ㅽ뻾
```
python scripts/check_token.py
python scripts/make_test_images.py
git add docs && git commit -m "test images" && git push   # Pages 諛섏쁺 ?湲?python scripts/publish_carousel.py --caption "?뚯뒪?? <URL1> <URL2>
```

