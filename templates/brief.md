# LPブリーフ（ヒアリングシート）
#
# この書式は scripts/check_brief.py が機械で読む。書き方のルール:
#   - 「key: 値」の形を崩さない。値が複数あるときは、key: の次の行から「  - 値」で並べる
#   - 分からない項目は TODO のまま残す（推測で埋めない）
#   - 「#」で始まる行はコメント（読み飛ばされる）
#   - 書けるのは「事実」だけ。効果や評判ではなく、時間・場所・料金・資格・設備など確認できること
#
# ★印は必須。check_brief.py が通るまでLP作成は始まらない。

# ---------- 院の基本情報 ----------
# 複数院の共通LPにするときは、下の clinics に1院1行で書き、
# address / access / hours / holidays / parking / phone は「clinics参照」と書く。
# clinic_name には屋号（例: ○○整骨院）を書く。
# 書式: 名称 / 住所 / 行き方 / 受付時間 / 休業日 / 駐車場 / 電話（行き方・駐車場は分からなければ「なし」）
clinics:
  - なし
clinic_name: TODO                 # ★ 院名（正式名称）。複数院なら屋号
area: TODO                        # ★ 地域名・最寄駅（例: 藤沢市 辻堂駅）
address: TODO                     # ★ 所在地
access: TODO                      # ★ 行き方（例: 辻堂駅北口から徒歩4分）
hours: TODO                       # ★ 受付時間（例: 平日 9:00-12:00 / 15:00-20:00、土 9:00-14:00）
holidays: TODO                    # ★ 休業日
parking: TODO                     # 駐車場（例: 3台 / なし・近隣にコインパーキング）
phone: TODO                       # ★ 電話番号
line_url: TODO                    # 公式LINEの友だち追加URL（無ければ「なし」）
reservation_url: TODO             # Web予約URL（無ければ「なし」）
cta_primary: TODO                 # ★ 一番押してほしい行動: line / tel / web のどれか

# ---------- 施術者 ----------
# ★ 1人以上。「名前 / 資格 / 経歴の事実」の順で。資格は国家資格を正式名称で（柔道整復師 など）
staff:
  - TODO

# ---------- 誰に向けるか ----------
persona: TODO                     # ★ 想定する読者（年代・生活・どんな場面で困っているか）
main_complaint: TODO              # ★ 主に来てほしい人の悩み（例: 急に腰を痛めた、部活でひねった）
reader_worries:                   # ★ 来院前に読者が抱えている不安（例: 保険が使えるか分からない、痛くされそう）
  - TODO

# ---------- 来院の流れ・料金 ----------
first_visit_flow:                 # ★ 初回の流れ（受付→問診→検査→施術→説明 など）と所要時間
  - TODO
price_insurance: TODO             # 保険施術の窓口負担の目安（例: 初回 1,500円前後〈3割負担〉）。扱わないなら「なし」
# 自費メニュー。扱うなら1行ずつ「メニュー名 / 内容 / 料金 / 所要時間」
# 1つでも書いたら、下の self_pay_risks も必須（あはき・柔整広告ガイドラインⅥ.3）
self_pay_menu:
  - なし
self_pay_risks:                   # 自費施術の主なリスク・副作用（例: 施術後に一時的なだるさが出ることがあります）
  - なし

# ---------- 選ばれる理由（事実のみ） ----------
# ★ 3つ以上。効果ではなく「通いやすさ・分かりやすさ・安心・人」で。
#   良い例: 夜20時まで受付 / 予約優先で待ち時間が少ない / 個室あり / 女性の施術者が在籍 / 説明の時間をとる
#   ダメな例: よく治る / 根本改善 / 地域No.1 / 満足度98%
strengths:
  - TODO

# ---------- 流入経路と法令モード ----------
# ★ このLPに人がどこから来るか: organic（検索・GBP・紹介） / ads（リスティング・SNS広告） / flyer（チラシ・ポスティングのQR） / mixed
traffic_source: TODO
# ★ website / advertising のどちらか。決め方は skills/lp-compliance/SKILL.md の「モード判定」
#   迷ったら advertising（厳しい側）にする
compliance_mode: TODO
# traffic_source が organic 以外で website を選ぶときは必須。誰に・いつ照会し・何と回答を得たか
compliance_basis: なし

# ---------- 設置先と計測 ----------
# ★ html（index.html を自前で置く） / utage（UTAGE の「空白のファネル（HTML）」に貼る）
deploy_target: TODO
# utage のとき必須。このLP専用に UTAGE で発行した LINE 登録経路URL（院の共通URLは使わない）
#   発行: メール・LINE配信 > 配信アカウント > シナリオ > シナリオ設定 > 登録経路 > 追加（種類: LINE）
#   LPごとに経路を分けると、UTAGE の「登録経路分析」でアクセス数と登録数がLP単位で取れる
line_route_url: なし
line_route_name: なし            # UTAGE 上の登録経路の管理名称（例: LP_A院_急なケガ_2026-11）

# ---------- 素材 ----------
photos:                           # 使える写真（院内・外観・施術者）。掲載同意を取ったものだけ。無ければ「なし」
  - なし
brand_color: なし                 # 院のブランドカラー（例: #2E7D6B）。無ければデザインシステムの既定色
tone: 落ち着いて誠実              # 文体の雰囲気

# ---------- 参考 ----------
competitors:                      # 近隣の競合院のURL（調査で使う）。無ければ「なし」
  - なし
extra_ng_words:                   # 院の方針で使いたくない言葉
  - なし
notes: なし                       # その他伝えておきたいこと
