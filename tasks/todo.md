# TODO — KINTEX·SETEC·DDP 크롤링 장애 수정 (2026-09-29)

- [x] DDP: 중간 인증서 번들(`crawlers/certs/`) + `session.verify` 적용
- [x] summarize: DDP 상세 페이지 fetch에 같은 번들 전달
- [x] KINTEX: www 도메인 직접 사용, 타임아웃 (20,30), 재시도 3회 백오프
- [x] main.py: 출처별로 신규 수집 + 이전 미종료 이벤트 병합 (부분 실패·0건 모두 대응)
- [x] KINTEX: 페이지 요청 실패 시 이미 수집한 페이지까지 반환
- [x] 로컬 검증: test_crawlers.py ddp/kintex, main.py, 폴백 시나리오
- [x] lessons.md 기록
- [x] 커밋·푸시 → Actions 수동 실행으로 확인

## 리뷰
- 로컬 검증 결과: DDP 79건(SSL 오류 없음), KINTEX 34건(www 도메인), SETEC 23건, COEX 58건 → 총 194건 저장
- 폴백 단위 검증: SETEC 0건 시 이전 23건 유지, 파일 없음/깨짐 시 안전하게 빈 리스트
- 남은 리스크: KINTEX가 Actions 러너 IP를 차단하는 경우 재시도로도 실패 가능 → 폴백으로 이전 데이터 유지
- 별건: Actions에 ANTHROPIC_API_KEY 시크릿 미설정으로 요약 매회 건너뜀
