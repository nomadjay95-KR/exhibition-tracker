# Lessons

## 2026-09-29 — 크롤러 장애 조사
- **크롤러 0건은 "성공"이 아니다.** Actions는 예외를 잡고 계속 진행하므로 워크플로우가 success여도 데이터가 빠질 수 있다. 조사 시 `gh run view --log`에서 `건 수집`·`ERROR`·`WARNING`을 먼저 확인할 것.
- **조사 전 `git fetch`.** 봇 커밋(`chore: update exhibitions data`)으로 로컬이 origin보다 뒤처져 있으면 사이트와 다른 데이터를 보고 잘못 판단한다.
- **"안 보인다" ≠ "안 수집된다".** 프론트 기본 필터(관련 주제만)가 출처 전체를 숨길 수 있다. 수집 건수와 relevant 건수를 분리해 확인할 것.
- **외부 사이트 SSL 오류는 `verify=False`로 덮지 말 것.** 서버가 중간 인증서를 빠뜨린 경우 해당 인증서를 저장소에 넣고 certifi와 합친 번들로 검증하면 경고 없이 안전하게 해결된다 (`crawlers/ddp.py:ca_bundle`).
- **한 출처의 일시 장애가 사이트 전체 품질을 깎지 않게 폴백을 둘 것.** 0건이면 이전 결과의 미종료 행사를 유지 (`main.py:_with_fallback`).
