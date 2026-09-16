#!/bin/zsh
cd "${0:A:h}"
if /usr/bin/curl -fsS http://127.0.0.1:4173/ 2>/dev/null | /usr/bin/grep -q 'Orbe — Finanças pessoais'; then
  /usr/bin/open http://127.0.0.1:4173/
else
  /usr/bin/open http://127.0.0.1:4173/
  python3 -m http.server 4173 --bind 127.0.0.1 --directory dist
fi
