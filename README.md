# commute-english-cards

인스타그램 **@commute.english.kr (출근길 영어)** 자동 게시용 저장소.

- 매일 20:00 KST: GitHub Actions(`daily.yml`)가 `daily.py`로 다음 날 카드뉴스(퀴즈형 7~8장, 계절 테마)와 캐릭터 '토리' 릴스를 만들어 `gh-pages`(GitHub Pages)에 올림. 최근 5일치만 남김.
- 06:00 KST: Cloudflare Worker `commute-english-bot`(`worker/`)이 인스타 Graph API로 카드뉴스와 릴스를 게시.
- 문장·장면 데이터: `data/plan_2027.json` (원본은 별도 작업 폴더 `english-ig/plan`). 2027년이 아니면 52주 단위로 옮겨 같은 요일 장면을 씀.
- 원어민 음성: AI 음성(Kokoro-82M, Apache-2.0). 배경음악: 자체 합성(`music/`). 글꼴: Noto Sans KR · Noto Color Emoji · Inter (OFL, `fonts/`).
