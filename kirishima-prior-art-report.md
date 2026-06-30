# キリシマ — 前例調査レポート（prior art / 新規性）

調査日: 2026-06-27
対象: 3人用・完全情報・運なし・隠匿情報なしの格子線引き陣取りゲーム「キリシマ」、およびその背後の設計原理
方法: 5系統の並列ウェブ調査（ゲームカタログ／設計コミュニティ／組合せゲーム理論文献）＋敵対的相互検証
目的: 「あるのか／ないのか」と、最も近い既存例、新規性の較正済み判定

---

## 結論（4問への較正済み判定）

1. クラスの空白（深い＋席公平＋3人＋完全情報＋運なし）: **本質的に空。しかも偶然ではなく、構造的に除外されています。** 真剣な深さの基準で全条件を満たす既存ゲームはゼロです。

2. メカニクスの新規性（自網延伸＋色無差別・最後に閉じた者が領域総取り）: **組み合わせは新規です。** 各制約は単体では既出ですが、3つの結合に該当する命名ゲームは見つかりません。

3. 設計原理の新規性（リーチ制約で最下位の役を脱出可能にし、誰も無利得の決定手を持たない）: **狙う問題は3人組合せゲーム理論の中心的・形式的に定義された問題そのものです。一般的な対処（最下位に残余利得を与える）は既知ですが、それを「得点ルール」ではなく「手の幾何学」で達成する手法は文献上見当たりません。** ここに新規性があります。

4. 多人数組合せゲーム理論の位置づけ: 形式理論は豊富です（Propp の「Queer」クラス、Spindler の undetermined、Cincotti の NP完全性、Li/Straffin のコアリション）。キリシマは、その難点を設計で回避した経験的存在証明として位置づきます。

主張の射程: このレポートの価値は「前例が無いことの証明」ではありません。それは原理的に不可能で、最も価値の低い部分です。価値は二つの積極的事実にあります。(1) キリシマが狙う問題が形式的に命名され、難所として認知されていること、(2) その幾何学的解法が文献に未公表であること。前例の有無は副次的です。具体的に残るリスクは未デジタル化のペン&ペーパー旧蔵（特に Joris の全100作——Imparium が中立壁・最後閉鎖獲得を既に含むため）であって、特定国のオンライン個人制作ではありません。

---

## Q1. 「深い＋席公平＋3人＋完全情報＋運なし」は空か

### 構造的に除外されている
このクラスは、コミュニティ自身の正典的分類で定義上はじかれています。アブストラクトゲームの理論ページ（abstractgames.org, Cesco Reale）は次のように明言します——「キングメーカー効果が起こりうるため、最善のプレイヤーを真に確定できるのは2人ゲームだけ。だから組合せゲームの数学的定義はプレイヤーが2人であることを含む」。同ページの Venn 図（Maurizio De Leo）は、例となるゲームが見つからないセルに疑問符を置いています。空白は認知済みです。

形式的な核は3人 Nim の {1,2} 局面です。先手に勝ち手は無く、その着手は「2番手と3番手のどちらが勝つか」だけを決めます。最も単純な完全情報・運なしゲームに、純粋なキングメーカーが現れます（Propp 2000）。十分に深い3人ゲームは原理的にこの種の局面に到達しうるため、設計者はこの空間を避けてきました。

### 最も近い候補（5条件で採点: a 3人ネイティブ / b 完全情報 / c 運なし / d 深い / e 席公平）
- 中国チェッカー(3人): a,b,c ○、d 浅め（序盤決定的、AIの試験台だが囲碁級の深さではない）、e ×（abstractgames.org がキングメーカー/同盟の教科書例として名指し）。
- Yavalath(3人): a,b,c ○、d 中程度（短く強制手が多い）、e ×を強制ブロック＋3目脱落でパッチ。設計者本人「3人版は邪悪」。最強の near-miss ですが、公平性は追加ルールで個別に抑えたもので、深さも限定的です。
- Tak(3人): b,c ○、d ○（深い）だが a ×（本質2人設計）、2人でも先手勝率55〜65%＝e も×。
- Hex / Y / Star / *Star, GIPFシリーズ全作: 連結系・領地系の最深部だが**全て本質2人**。3人版の深い例は存在しません。
- Charybdis / Snark（個人設計、solvingkingmaker ブログ）: このクラスを狙った試作。Charybdis は強制キングメーカーを「ほぼ皆無」にしたが残存を自認、深さ未証明。Snark は「単純すぎて容易に解ける」＝深さで脱落。「キングメーカーを消すと深さも消える」という反復パターンの実例です。

### 判定
深さを真剣な基準（囲碁/GIPF/Hex 級）で取り、席公平を構造的なキングメーカー不在＋手番有利の不在まで要求すると、**全条件を満たす既存メンバーはゼロです。** 仮説「ほぼ空」は敵対的探索を経ても覆りませんでした。残る不確実性は、JavaScriptで読めなかった BGG の専門 geeklist（191517 ほか）に珍しい一作が潜む可能性のみです。

注意（矛盾しない点）: Propp の定理は「3人ゲームに Queer 局面が存在しうる」と言うのであって「全ての3人ゲームがキングメーカーに支配される」とは言いません。キリシマの主張は、リーチ制約の幾何によって Queer/キングメーカー局面を稀かつ戦略的に無害化したという**設計による回避**であり、定理への反証ではありません。だからこそ、空白セルの構成的存在証明の候補になりえます。

---

## Q2. メカニクスの新規性

### 制約ごとの較正
- 制約A（自網延伸＝自分の線からしか伸ばせない）: 単体では新規ではありません。鉄道/ルート構築（TransAmerica など「自分の起点ネットワークから接続」）の定番ルールであり、Walter Joris の Snake Fight にも自分の蛇を延ばす形で現れます。格子の単位辺に適用した点が新しいだけです。
- 制約B（色無差別の壁＋最後に閉じた者が領域を総取り）: 稀で、ほぼ新規です。「誰の線でも壁になる」＋「閉じた者が領域全体を取る」は、Joris の Imparium（マス/ドミノ＋奇数サイズ限定のパリティ）と、Dots and Boxes の1×1スケールでの「最後の辺を引いた者が箱を取る」が部分的に重なるのみです。任意サイズの領域を中立壁で「最後に閉じた者が総取り」は最も前例の薄い成分です。
- 組み合わせ（A＋Bを格子上で）: 新規。自網延伸を最後閉鎖総取りの陣取りに結合したゲームは見つかりません。

### 最も近い既存ゲームと差分
- Dots and Boxes / Strings-and-Coins: 同じ格子＋直交辺だが、辺は共有コモンズ（自網制約なし）、得点は1×1の箱単位、本質2人。属の祖先だが定義ルールで別物です。
- WallGo（『The Devil's Plan』2024–25）: 「壁で囲んで領域得点」で最も近い現代作。ただし領域は「中にいるコマの色」で得点＝最後に閉じた者総取りではなく、壁に色移転もなく、自網成長制約もありません。
- Walter Joris「Imparium」: 囲い規則そのものに最も近い前例。壁は中立、「自分の手で囲いを閉じた時に領域を獲得」。差分はマス/ドミノ基盤、自網成長制約なし、奇数サイズ≤9のみ得点というパリティの特徴です。
- Bridg-It / Gale: 直交線で自分の連結網を作る点は近いが、目的は対辺connection、2人です。
- Qix / Splix.io / Paper.io: 「自分の軌跡で囲って取る」は近いが、リアルタイム動画ゲームで、ターン制完全情報アブストラクトでも3人でもありません。

### 判定
「自網延伸」＋「色無差別・最後に閉じた者が領域総取り」の結合は**高い確度で新規**です。現実的な残存リスクは「Ludii か Joris の無名ルールが部分的に先取り」程度で、「著名ゲームが既にやっている」ではありません。Joris の100作と Browne の Connection Games 約200作は全文索引できなかったため、確度は高いものの確実ではありません。

---

## Q3. 設計原理の新規性（キングメーカーの幾何学的解消）

### 狙う問題は形式的に命名済み
キリシマが消そうとしている「最下位が、自分の利得に無関係なまま勝者を決める手」は、組合せゲーム理論で **Propp の Queer クラス**（どのプレイヤーにも必勝戦略がない局面）、**Spindler の undetermined クラス**として厳密に定義されています。Cincotti は3人 Hackenbush-on-strings の勝敗判定が **NP完全**であることを示し、難しさが「競争」ではなく「協調」に由来すると指摘します。キングメーカーは設計者が残した欠陥ではなく、3人完全情報・運なしゲームの解概念そのものの構造的特徴です。

設計コミュニティ側では、Alex Jaffe（GDC 2019「Cursed Problems in Game Design」）がキングメーカーを **cursed problem**——核となるプレイヤー約束どうしの矛盾に根ざし、解けず、ゲームの目的そのものを変えてしか回避できない問題——に分類します。

### 既知の対処は全て「制約を1つ緩める」
- 隠匿勝利情報（Knizia の Tigris & Euphrates の最小色得点など）→ 完全情報を破る。
- 運の導入 → 運なしを破る。
- 脱落（poker, Risk）→ キングメーカーは消えるが2対1の集中砲火を生む。
- 2位以下に得点価値を与える → 詰んだプレイヤーに残余利得を与え、無利得の手を無くす（Wikipedia のグラディエーター例: 2位に価値があれば先手は無関心でなくなる）。**「無利得の手を消す」を直接狙う唯一の主流対処です。**
- 「全ての手が全員を少し動かす」均衡＆慣性（The King Is Dead など）→ 決定的単手を消す。
- 約束の再交渉（Cole Wehrle, Root/Oath）→ 政治と物語を目的に組み込み、純粋技量勝負であることをやめる。Jaffe の「ゲームの目的を変える」逃げ道です。

学術側の構造的対処も同じ発想を**得点／順位ルール**で実現しています。Li の podium rule（最下位を避けられぬ者は2位を狙え）、Cincotti/Spindler の ranked/elimination convention。いずれも残余利得を**ペイオフ規則**で作ります。

### 幾何学で作る手法は未発見
キリシマの主張は、残余利得を得点ルールでなく**手の幾何学（自網リーチ制約）**で作る——最下位＝緩衝国が常に「国境を荒らして役を脱出する」自己利益の手を持つため、無利得の決定手に陥らない——というものです。これは Q4 の文献調査担当が明言した通り、**「リーチ／延伸の幾何によって敗者の役を脱出可能にする」手法は、定理としても命名原理としても文献に見当たりません。** 問題は厳密に既知、一般的な治療方針（敗者に残余利得を）も既知ですが、それを移動の幾何で実装する具体策は未公表です。ここが書き残す価値のある新規性です。

最も近い既存実装は個人ブログ solvingkingmaker の Snark（Petersen グラフ上、引き分けリセットで敗者の利害を反転）と Charybdis（六角盤、共有ボートを自分の辺から押す）です。どちらも幾何で攻めた本格的な試みですが、強制キングメーカーを「稀／soft」に下げるに留まり、Snark は幾何が効いた瞬間に自明化します。キリシマが「パッチ無しの内在的幾何＋証明された深さ」で両立しているなら、これらより前進しています。

---

## Q4. 多人数組合せゲーム理論の地形と位置づけ

- 二人理論の限界: Conway『On Numbers and Games』(1976) と Berlekamp–Conway–Guy『Winning Ways』(1982) の代数（surreal 値、選言和の群構造、Sprague–Grundy）は本質的に2人用。コアリションが現れると加法的ゲーム値が壊れます。
- 中心的難点の形式化: Propp「Three-player impartial games」(TCS 2000, arXiv math/9903153) が Queer クラスを定義し、3人 Nim {1,2} を例示。位置22（2,2の二山）は「吸収状態」＝何を足しても undetermined のまま、と証明。Spindler (arXiv 1903.01375, 2019) は undetermined が吸収的であることを示します。
- コアリション結果: Li (1978) podium rule、Straffin (1985) McCarthy revenge rule、Nowakowski–Santos–Silva (2021) podium rule の現代的完全分類、Krawec (2012/2014, ランダムプレイヤー)。いずれも敗者の振る舞いに仮定を置いて初めて tractable になります。
- 計算側: maxⁿ (Luckhardt–Irani, AAAI 1986)、Korf (1991, 浅い枝刈りしか効かない)、Paranoid 還元、soft-maxⁿ / prob-maxⁿ (Sturtevant–Bowling, 2006)、多人数 MCTS (Nijssen 学位論文; Baier–Kaisers「自分に集中せよ」)。
- 席公平: 3人完全情報ゲームの席公平は2人の strategy-stealing のようには形式化されていません。むしろ Spindler は対称三重和で N ∉ o(G+G+G)、すなわち**先手が構造的に不利**になりうると示します（先手有利の逆）。Sturtevant–Bowling は同一配置を6つの席順列で回して席効果を平均化します——キリシマの実験（予算↔席を6順列でローテして席効果を打ち消した手続き）と同じ作法です。

位置づけ: キリシマは、この形式理論が「困難な領域」と名指しした範囲で、設計によって成立させた経験的存在証明の候補です。とりわけ、3人席公平が理論的にほぼ未開拓（既存の数少ない結果はむしろ先手不利を示唆）である中で、強い手で席がフラットという経験データ自体が新しい観測です。

---

## 残存リスクの所在（確率順）
全文を索引できなかった領域のうち、前例が潜むなら確率の高い順に並べます。
1. 未デジタル化のペン&ペーパー旧蔵。最有力です。Walter Joris『100 Strategic Games for Pen and Paper』全100作（オンラインは約6作のみ）——同書の Imparium が既に中立壁＋最後閉鎖獲得を実装しているため、別の一作が自網延伸を足している可能性は無視できません。次いで Sid Sackson の収集、Martin Gardner ら娯楽数学コラム、露 Kvant 系。これは印刷物という媒体の穴であって、国籍の穴ではありません。
2. BGG の専門 geeklist（191517「Print-and-play 3人 luck-free abstracts」ほか）と「Fighting the kingmaker」スレ——JavaScript 描画で本文未読。索引可能、未読なだけです。
3. Cameron Browne『Connection Games』約200作——全文索引不可だが connection 勝利系であり、enclosure 得点は定義上含みにくい（低リスク）。
4. DiVA 修士論文「Mitigating kingmaking in multiplayer board games」(diva2:1876522)——存在のみ確認、本文未取得。

特定の国（日本・中国・欧州）の個人制作を残存リスクの主座に置く根拠はありません。完全情報アブストラクトの歴史的厚みはむしろ独・蘭（Knizia, Freeling）と露の娯楽数学にあり、潜在前例の在処を国籍で絞るのは誤りです。残るのは媒体（未デジタル化の旧印刷）の問題です。

---

## 書き残す際の推奨フレーミング
1. キリシマを「形式的にほぼ不可能とされた空白セルの、構成的存在証明の候補」として提示する（MCTS 1k〜100k の経験的裏づけ付き、深さ・席公平は経験的であって証明ではないと明記）。
2. メカニクスは「自網延伸＋色無差別・最後閉鎖総取り」の新規結合として、WallGo・Imparium・Dots and Boxes との差分で位置づける。
3. 設計原理は「敗者に残余利得を与える」既知方針の**幾何学的実装**として打ち出す。ペイオフ規則による既存治療（Li の podium、Cincotti/Spindler の順位/脱落 convention）および行動仮定による治療（Straffin、maxⁿ の前提）と明示的に対比し、形式的標的として Propp の Queer クラスを引く。
4. 席公平の経験的フラットさを、Spindler の理論的先手不利示唆および Sturtevant–Bowling の席順列法と並べて、観測として提示する。

---

## 出典

クラスの空白・キングメーカー（設計）
- [Theory of abstract games — abstractgames.org](https://www.abstractgames.org/abstractdefinition.html)
- [Abstract strategy game — Wikipedia](https://en.wikipedia.org/wiki/Abstract_strategy_game)
- [Kingmaker scenario — Wikipedia](https://en.wikipedia.org/wiki/Kingmaker_scenario)
- [Solving the three-player problem — Skeleton Code Machine (Pulsipher)](https://www.skeletoncodemachine.com/p/three-player-problem)
- [Is kingmaking a problem to be solved? — Skeleton Code Machine (Wehrle)](https://www.skeletoncodemachine.com/p/kingmaking)
- [Is kingmaking cursed? — Skeleton Code Machine (Jaffe)](https://www.skeletoncodemachine.com/p/is-kingmaking-cursed)
- [Cursed Problems in Game Design (Alex Jaffe) — GDC Vault](https://www.gdcvault.com/play/1025756/Cursed-Problems-in-Game)
- ["King Me": A Defense of King-Making (Cole Wehrle) — GDC/YouTube](https://www.youtube.com/watch?v=UraJElx1ebg)
- [3 Player Strategy Design — solvingkingmaker (What is Kingmaking?)](https://solvingkingmaker.wordpress.com/2014/03/17/what-is-kingmaking/)
- [No-Lose Scenarios — solvingkingmaker](https://solvingkingmaker.wordpress.com/2014/03/31/kingmaking-and-no-lose-scenarios/)
- [Case Study: Snark — solvingkingmaker](https://solvingkingmaker.wordpress.com/2014/11/17/case-study-snark/)
- [Case Study: Charybdis — solvingkingmaker](https://solvingkingmaker.wordpress.com/2016/02/08/case-study-charybdis/)

候補ゲーム・メカニクス
- [Dots and Boxes — Wikipedia](https://en.wikipedia.org/wiki/Dots_and_boxes)
- [Wall Go — rules (playwallgo.com)](https://www.playwallgo.com/rules)
- [WallZero: Mastering the Game of WallGo — arXiv](https://arxiv.org/html/2606.17847v1)
- [Six Strategic Pen-and-Paper Games (Walter Joris: Imparium, Snake Fight) — Math with Bad Drawings](https://mathwithbaddrawings.com/2020/04/22/six-strategic-games-from-a-strange-and-bottomless-mind/)
- [Connection game — Wikipedia](https://en.wikipedia.org/wiki/Connection_game)
- [Bridg-It — HexWiki](https://www.hexwiki.net/index.php/Bridg-It)
- [Black Path Game — Wikipedia](https://en.wikipedia.org/wiki/Black_Path_Game)
- [Qix — Wikipedia](https://en.wikipedia.org/wiki/Qix)
- [TransAmerica — BoardGameGeek](https://boardgamegeek.com/boardgame/2842/transamerica)
- [Rules of Go — Wikipedia](https://en.wikipedia.org/wiki/Rules_of_Go)
- [GIPF Project — Wikipedia](https://en.wikipedia.org/wiki/GIPF_Project)
- [Cameron Browne, Connection Games (Routledge)](https://www.routledge.com/Connection-Games-Variations-on-a-Theme/Browne/p/book/9781568812243)

3人で成立する近代ミニマル抽象・自動設計
- [Yavalath — BoardGameGeek](https://boardgamegeek.com/boardgame/33767/yavalath) / [rulebook 3人版 PDF](https://nestorgames.com/rulebooks/YAVALATH_EN.pdf) / [Cameron Browne](https://cambolbro.com/games/yavalath/)
- [A rule for kingmaking from Yavalath — VideoGameGeek](https://videogamegeek.com/blog/10957/blogpost/116806/a-rule-for-kingmaking-from-yavalath)
- [Tak Review (先手有利55–65%) — The Thoughtful Gamer](https://thethoughtfulgamer.com/2019/02/04/tak-review/)
- [On Strongly Solving Chinese Checkers — Sturtevant (PDF)](https://webdocs.cs.ualberta.ca/~nathanst/papers/sturtevant2019chinesecheckers.pdf)
- [An Overview of the Ludii General Game System — arXiv](https://arxiv.org/pdf/1907.00240)
- [Browne PhD「Automatic Generation and Evaluation of Recombination Games」— QUT](https://eprints.qut.edu.au/17025/)
- [GAVEL: Generating Games via Evolution and LLMs — arXiv](https://arxiv.org/abs/2407.09388)

組合せゲーム理論（学術）
- [Propp「Three-player impartial games」— arXiv math/9903153 (TCS 2000)](https://arxiv.org/abs/math/9903153)
- [Spindler「N-player normal play convention」— arXiv 1903.01375](https://arxiv.org/abs/1903.01375)
- [Cincotti「Three-player Hackenbush on strings is NP-complete」— IMECS 2008 PDF](https://www.iaeng.org/publication/IMECS2008/IMECS2008_pp226-230.pdf)
- [Cincotti「Three-player partizan games」— TCS 332 (2005)](https://www.semanticscholar.org/paper/Three-player-partizan-games-Cincotti/2545d55e4e1e4e4ac72aa616c3d7b0a101b241a5)
- [Nowakowski–Santos–Silva「Three-player nim with podium rule」— IJGT 2021](https://link.springer.com/article/10.1007/s00182-019-00702-3)
- [Li「N-person Nim and N-person Moore's games」— IJGT 1978](https://link.springer.com/article/10.1007/BF01763118)
- [Straffin「Three-person winner-take-all with McCarthy's revenge rule」— College Math. J. 1985](https://www.tandfonline.com/doi/abs/10.1080/07468342.1985.11972910)
- [Krawec「Analyzing n-player impartial games」— IJGT 2012](https://link.springer.com/article/10.1007/s00182-011-0289-3)
- [Brown「Three-player combinatorial games」— Leiden BSc thesis 2025 PDF](https://theses.liacs.nl/pdf/2024-2025-BrownMCMark.pdf)
- [Luckhardt–Irani / Korf「Multi-player alpha-beta pruning」— PDF](https://faculty.cc.gatech.edu/~thad/6601-gradAI-fall2015/Korf_Multi-player-Alpha-beta-Pruning.pdf)
- [Sturtevant–Bowling「Robust game play / soft-maxⁿ」— AAMAS 2006 PDF](https://webdocs.cs.ualberta.ca/~nathanst/papers/softmaxn.pdf)
- [Sturtevant「Multi-Player Games: Algorithms and Approaches」— PhD thesis PDF](https://webdocs.cs.ualberta.ca/~nathanst/papers/multiplayergamesthesis.pdf)
- [Nijssen「Monte-Carlo Tree Search for Multi-Player Games」— PhD thesis PDF](https://project.dke.maastrichtuniversity.nl/games/files/phd/Nijssen_thesis.pdf)
- [Baier–Kaisers「Guiding Multiplayer MCTS by Focusing on Yourself」— PDF](https://ir.cwi.nl/pub/30608/30608.pdf)

未検証（存在のみ確認）
- DiVA 修士論文「Mitigating kingmaking in multiplayer board games」(diva2:1876522)
