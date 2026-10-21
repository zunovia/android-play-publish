"""git の index（git add 済みの中身）に、鍵・トークン・パスワード直書きが入っていないか調べる（SKILL.md の非公開リポジトリの節を参照）。

使い方: git add -A の後、commit の前に、リポジトリの中で
  python <このスキルのフォルダ>/scan_secrets.py
終了コード 0 = 見つからない、1 = 見つかった（commit しない）、2 = git リポジトリでない等。
シェルの引用符に左右されないよう、検査はすべてこのスクリプトの中で行う。
"""

import re
import subprocess
import sys

# 追跡してはいけないファイル（名前で判定）
BAD_FILES = re.compile(
    r"(^|/)(keystore\.properties|local\.properties|\.env(\..+)?|[^/]*service-account[^/]*\.json)$"
    r"|\.(jks|keystore|p12|pfx|pem|key|aab|apk)$",
    re.I,
)
# 中身で判定（どのファイルでも）
TOKENS = re.compile(
    r"BEGIN ([A-Z]+ )?PRIVATE KEY"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|sk-(ant|proj)-[0-9A-Za-z_-]{10,}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
)
PW = re.compile(r"(store|key)_?Password\s*([=:])?\s*(.*)", re.I)
# 値を「読み込んでいるだけ」の書き方（直書きではない）
INDIRECT = re.compile(r"keystoreProperties|getenv|System\.env|findProperty|project\.property|properties\[|\$\{|providers\.", re.I)
QUOTED = re.compile(r"""^["'][^"']+["']""")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def password_literal(path, line):
    m = PW.search(line)
    if not m:
        return False
    sep, value = m.group(2), m.group(3).strip()
    if not value or INDIRECT.search(value):
        return False
    if path.endswith(".properties"):  # storePassword=hunter2（引用符なしが標準形）
        return bool(sep)
    if path.endswith((".gradle", ".gradle.kts")):  # storePassword = "hunter2" / storePassword 'hunter2'
        return bool(QUOTED.match(value))
    return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        paths = [p for p in git("ls-files", "-z", "--cached").decode("utf-8").split("\0") if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("git リポジトリの中で実行する（git が無いか、リポジトリでない）")
        return 2
    if not paths:
        print("index が空。先に git add -A してから実行する")
        return 2

    hits = []
    for p in paths:
        if BAD_FILES.search(p):
            hits.append(f"{p}: 追跡してはいけないファイル（git rm --cached して .gitignore に足す）")
            continue
        try:
            data = git("show", f":{p}")
        except subprocess.CalledProcessError:
            continue
        if b"\0" in data[:8000]:
            continue  # バイナリ
        for n, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            if TOKENS.search(line):
                hits.append(f"{p}:{n}: 鍵またはトークンらしき文字列")
            elif password_literal(p, line):
                hits.append(f"{p}:{n}: パスワードの直書き")

    if hits:
        print("== 見つかった（commit しない）==")
        for h in hits:
            print("  " + h)  # 値そのものは表示しない
        return 1
    print(f"OK: index の {len(paths)} ファイルに鍵・トークン・パスワード直書きなし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
