# android-play-publish

Android アプリを**作ってから Google Play で公開が完了するまで**を導く Claude Code 用スキルです。
ソースの非公開リポジトリ管理、Claude Design でのロゴ・アイコン作成、Play Console での内部テスト → 製品版の審査提出 → 公開確認までを扱います。法人アカウントで複数のアプリを新規公開・アップデートした実作業から起こしています。

Play Console は「どこに何があるか分からない」「保存したはずの入力が消える」「送信ボタンが押せない理由が分からない」
といった詰まり方をします。このスキルは、その**詰まる場所と抜け方**を先に Claude に教えておくためのものです。

提供: 一般社団法人サーコミュニケーション（[surc.online](https://surc.online/apps/)）

---

## 導入

`~/.claude/skills/` の下に clone します。ここに置くと、どのフォルダで Claude Code を起動しても使えます。

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/zunovia/android-play-publish.git
```

Windows（PowerShell）の場合:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills"
Set-Location "$env:USERPROFILE\.claude\skills"
git clone https://github.com/zunovia/android-play-publish.git
```

Claude Code を再起動すると `android-play-publish` が使えるようになります。

## 最初にやること

`SKILL.md` の **§0-1「自分の情報を先に埋める」** の表を埋めてください。

| 項目 |
|---|
| 開発者名（ストアに表示される名前） |
| 連絡先メールアドレス |
| 法人／個人 |
| プライバシーポリシーの公開URL |
| GitHub のアカウント名（アプリの非公開リポジトリを作る先） |

**ここが空欄のまま作業を始めないでください。** ストア掲載・プライバシーポリシー・データセーフティの
連絡先に毎回使う値です。後から変えると審査の再確認が発生します。

埋めたら、その変更をコミットしておくと `git pull` 時に自分の値が残ります。

```bash
git add SKILL.md
git commit -m "自社の情報を記入"
```

## 使い方

Claude Code に、やりたいことをそのまま伝えてください。

```
Google Play にアプリを新規で公開したい
```
```
アップデートを審査に出したい
```
```
審査への送信ボタンがグレーになっていて押せない
```
```
このアプリのロゴとアイコンを作って、Play に出せるサイズで書き出して
```

スキルが自動で読み込まれ、手順・急所・つまずいたときの対処が Claude に渡ります。

> **ログインは必ずご自身で行ってください。** Claude にアカウントのパスワードや
> 2段階認証コードを渡さないでください。ブラウザにログインした状態を用意してから操作を任せます。

## 必要なもの（ロゴ作成・秘密情報検査を使う場合）

- Python 3 と [Pillow](https://pypi.org/project/pillow/)（`pip install pillow`）
- Chrome か Edge（`make_icons.py` が SVG の描画に使う。見つからなければ環境変数 `CHROME_PATH` で指定）
- ロゴを Design キャンバスで作るなら、Claude の Artifact（Design）機能が使えるアカウント。使えない環境でも、SVG を手元で書いて同じ書き出しと検品ができます
- 非公開リポジトリを作るなら [GitHub CLI](https://cli.github.com/)（`gh auth login` 済み）

## 更新

```bash
cd ~/.claude/skills/android-play-publish
git pull
```

Play Console の UI と要件は頻繁に変わります。こちらで新しい観測があれば反映していきます。

自分で編集した箇所と衝突した場合は、**実画面で正しいほうを残してください。**
手順書よりも実際の画面が正しい、が原則です。

## 画面がこの手順と違っていたら

**実画面を優先してください。** そのうえで `SKILL.md` の該当箇所を直し、
末尾の「変更履歴」に日付・観測内容・どの画面で見たかを1行足してください。
Claude に頼めばやってくれます。

直した内容を [info@surc.online](mailto:info@surc.online) に送っていただけると、
この手順書の更新に使い、`git pull` で全利用者に還元します。
UI変更は1人では年に数回しか踏めませんが、複数人で持ち寄れば早く正確になります。

**送るときのお願い**

- **変更した箇所だけ**を送ってください。ファイル全体は送らないでください。
- アプリID・デベロッパーID・社内固有の情報が混じっていないか、送る前にご確認ください。
- 送るかどうかは必ずご自身で判断してください。**このスキルが自動で送信することはありません。**

## 収録内容

| | 内容 |
|---|---|
| §1 | デベロッパーアカウントの作成（個人と法人の違い・12人テスト要件） |
| §0-5 | 全体の流れ（アプリ作成から公開完了まで） |
| §2 | 事前準備（署名・versionCode・targetSdk・R8検証・16KB整列・ストア素材） |
| §2-1 | ロゴ・アイコン・フィーチャーグラフィックを Claude Design で作り、全サイズを書き出して検品 |
| §2-2 | ソースを GitHub の非公開リポジトリで管理（commit 前の秘密情報検査・公開後のタグ） |
| §3 | 新規アプリの公開手順（申告10件・掲載情報・内部テスト・テスター選択・国／地域・審査送信） |
| §4 | アップデートの公開（2回目以降の最短手順・対象国の拡大） |
| §5 | よくあるブロッカーと対処（12件） |
| §6 | 変わりやすい項目ウォッチリスト（毎回疑う箇所と最終確認日） |
| §7 | AIエージェントに操作を代行させる場合の要点 |
| 付録 | `check16k.py` — AAB内の `.so` の16KB整列チェッカー |
| 付録 | `make_icons.py` — ロゴ SVG から Play 掲載画像とランチャーアイコン一式を書き出して検品 |
| 付録 | `scan_secrets.py` — commit 前に git の index から鍵・トークン・パスワード直書きを検出 |

## 免責

Google Play Console の仕様・UI・要件は Google が随時変更します。
本スキルは**実際に観測した事実の記録**であり、正確性・最新性を保証するものではありません。
最終的な判断は必ず実画面と Google の公式ドキュメントで行ってください。
本スキルの利用によって生じた損害について、提供者は責任を負いません。

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照してください。
