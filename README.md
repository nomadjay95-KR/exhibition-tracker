# Exhibition Tracker

COEX · SETEC · KINTEX · DDP 4개 전시장의 전시·행사 일정을 크롤링해
**정적 웹 갤러리**로 보여주는 프로젝트입니다. (이전: Notion 적재 → 현재: 자체 웹페이지)

## 구조

```
crawlers/          # 전시장별 크롤러 (coex / setec / kintex / ddp)
filter.py          # 키워드 기반 관련도 판정
store.py           # 크롤링 결과 → docs/exhibitions.json 저장
main.py            # 크롤 → 저장 실행 진입점
docs/              # GitHub Pages로 서빙되는 정적 갤러리
  ├ index.html
  ├ style.css
  ├ app.js         # exhibitions.json을 읽어 카드 그리드 렌더 + 검색/필터
  └ exhibitions.json   # 크롤링 결과 (자동 생성/갱신)
.github/workflows/crawl.yml   # 주 1회 자동 크롤 → JSON 커밋 → Pages 재배포
```

## 로컬 실행

```bash
pip install -r requirements.txt

# 크롤링 → docs/exhibitions.json 생성
python main.py

# 개별 크롤러 점검 (이미지 수집 여부는 🖼 표시)
python test_crawlers.py all

# 프론트엔드 로컬 미리보기
cd docs && python -m http.server 8000   # http://localhost:8000
```

## 배포 (GitHub Pages, 무료)

1. 이 repo를 GitHub에 push
2. Settings → Pages → Source: `main` 브랜치 `/docs` 폴더 선택
3. `https://<user>.github.io/<repo>/` 에서 갤러리 공개
4. 데이터 갱신: `.github/workflows/crawl.yml`이 매주 월요일 자동 실행
   (Actions 탭에서 `Crawl Exhibitions` 수동 실행도 가능)

## 데이터 모델 (`docs/exhibitions.json`)

```json
{
  "generated_at": "2026-06-25T09:00:00+09:00",
  "count": 120,
  "events": [
    {
      "name": "...", "start_date": "2026-07-01", "end_date": "2026-07-03",
      "venue": "...", "url": "...", "source": "COEX",
      "image_url": "https://...",
      "relevant": true
    }
  ]
}
```
