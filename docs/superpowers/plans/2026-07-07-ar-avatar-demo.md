# AR改変アバター表示デモ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** VRChat改変アバターのFBXをMixamoで自動アニメーション付与し、GLB/USDZに変換して、iPhone Safariの標準AR Quick LookでARループ再生できるデモページをGitHub Pagesに無料でホストする。

**Architecture:** Blender 4.5をヘッドレス実行してFBX→GLB/USDZ変換をスクリプト化し、`<model-viewer>` Webコンポーネント1枚のindex.htmlで表示、GitHub Pages（無料）でホストする。バックエンドサーバーは持たない。

**Tech Stack:** Blender 4.5 (bpy headless script), Mixamo（無料アニメーション取得、手動）, `<model-viewer>` (Google, CDN読み込み), Python 3.12 (`http.server`でローカル確認), GitHub Pages, gh CLI

**確認済みの環境:**
- Blender: `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`
- Python: `C:\Users\PC_User\AppData\Local\Programs\Python\Python312\python.exe`（PATH通り `python` で起動可）
- gh CLI: 認証済み（アカウント `hasegawakasyouen`, scopes: repo, workflow）
- プロジェクトルート: `C:\Users\PC_User\Documents\ar-avatar-demo`（git初期化済み、design specをコミット済み）

---

### Task 1: プロジェクトの骨組み作成

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\.gitignore`
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\source\.gitkeep`
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\scripts\.gitkeep`

- [ ] **Step 1: フォルダ構成を作る**

```bash
mkdir -p "C:\Users\PC_User\Documents\ar-avatar-demo\source"
mkdir -p "C:\Users\PC_User\Documents\ar-avatar-demo\scripts"
touch "C:\Users\PC_User\Documents\ar-avatar-demo\source\.gitkeep"
touch "C:\Users\PC_User\Documents\ar-avatar-demo\scripts\.gitkeep"
```

- [ ] **Step 2: `.gitignore` を作成**

```
smoketest.glb
smoketest.usdz
*.blend1
*.blend2
```

- [ ] **Step 3: コミット**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add .gitignore source/.gitkeep scripts/.gitkeep
git commit -m "chore: scaffold project folders"
```

---

### Task 2: Blender変換スクリプトを書き、スモークテストで検証する

実際のアバターFBXがまだ手元にない段階でも、Blenderのデフォルトシーン（Cube）を使って変換ロジック自体が動くことを先に確認する。

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\scripts\convert_to_web.py`

- [ ] **Step 1: スクリプトを書く**

```python
# scripts/convert_to_web.py
import bpy
import sys


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python convert_to_web.py "
            "-- <input_fbx|--smoketest> <output_glb> <output_usdz>"
        )
    return argv[argv.index("--") + 1:]


def export_glb_and_usdz(output_glb, output_usdz):
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_animations=True,
    )
    bpy.ops.wm.usd_export(
        filepath=output_usdz,
        export_animation=True,
    )


def main():
    args = get_args()
    if len(args) != 3:
        raise SystemExit(
            "Expected 3 args: <input_fbx|--smoketest> <output_glb> <output_usdz>"
        )
    mode, output_glb, output_usdz = args

    if mode == "--smoketest":
        # Blenderの初期シーン(Cube/Light/Camera)をそのまま使う
        bpy.ops.wm.read_factory_settings(use_empty=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=mode)

    export_glb_and_usdz(output_glb, output_usdz)
    print("CONVERT_OK", output_glb, output_usdz)


main()
```

- [ ] **Step 2: スモークテストを実行**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- --smoketest smoketest.glb smoketest.usdz
```

Expected: 標準出力の最後に `CONVERT_OK smoketest.glb smoketest.usdz` が出る。終了コード0。

- [ ] **Step 3: 出力ファイルを検証**

```bash
ls -la "C:\Users\PC_User\Documents\ar-avatar-demo\smoketest.glb" "C:\Users\PC_User\Documents\ar-avatar-demo\smoketest.usdz"
```

Expected: 両ファイルが存在し、サイズが0バイトでないこと。確認後、`smoketest.glb`/`smoketest.usdz` は削除してよい（`.gitignore`済みなのでコミットはされない）。

- [ ] **Step 4: コミット**

```bash
git add scripts/convert_to_web.py
git commit -m "feat: add headless Blender FBX->GLB/USDZ conversion script"
```

---

### Task 3: Mixamoでアニメーション付きFBXを取得する（手動）

この工程はAdobeのMixamo（ブラウザ上のサービス）を使う手動作業。VRChatアバターのボーン構造をそのまま使わず、Mixamo側の自動リギングでシンプルに解決する。

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_idle_mixamo.fbx`（あなたが手元でダウンロードして配置）

- [ ] **Step 1: 元アバターのFBXを用意する**

VRChatアップロード用Unityプロジェクトの `Assets` フォルダ内に、アバターの元FBXがあるはず（VRChatアバターは通常インポート元のFBXがプロジェクト内に残っている）。そのFBXファイルを `source\avatar_for_mixamo.fbx` としてこのプロジェクトにコピーする。

見つからない場合は、Unityでアバターモデルを選択し、`Assets > Export Package` ではなく、モデルのメッシュ・スケルトンだけをFBXとして書き出す（Unity 2022.3.22f1に `Unity FBX Exporter` パッケージが入っていれば、GameObjectを選択して `GameObject > Export To FBX` が使える）。

- [ ] **Step 2: mixamo.com にアクセスし、アップロード**

1. https://www.mixamo.com を開き、Adobeアカウントでログイン（無料）
2. 「UPLOAD CHARACTER」から `source\avatar_for_mixamo.fbx` をアップロード
3. 自動リギング画面で、顎・両手首・両肘・両膝の位置にマーカーを合わせて「NEXT」
4. リギング完了を待つ

- [ ] **Step 3: アニメーションを選ぶ**

1. 左側のアニメーション一覧から「Idle」または好みのダンスアニメーションを検索して選択
2. プレビューでアバターに正しく適用されているか確認（腕や脚が不自然にねじれていないか目視チェック）

- [ ] **Step 4: ダウンロード**

1. 「DOWNLOAD」ボタン
2. Format: `FBX Binary(.fbx)`
3. Skin: `With Skin`
4. Frames per Second: `30`
5. Keyframe Reduction: `none`
6. ダウンロードしたファイルを `source\avatar_idle_mixamo.fbx` としてこのプロジェクトに保存

- [ ] **Step 5: コミット**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add source/avatar_idle_mixamo.fbx
git commit -m "asset: add Mixamo-rigged animated avatar FBX"
```

（バイナリアセットのgit管理について: デモ段階はこのままでよい。将来ファイルが増える場合はGit LFS導入を検討する）

---

### Task 4: 実際のアバターをGLB/USDZに変換する

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\model.glb`
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\model.usdz`

- [ ] **Step 1: 変換スクリプトを実行**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- source\avatar_idle_mixamo.fbx model.glb model.usdz
```

Expected: `CONVERT_OK model.glb model.usdz` が出力される。

- [ ] **Step 2: 出力を検証**

```bash
ls -la "C:\Users\PC_User\Documents\ar-avatar-demo\model.glb" "C:\Users\PC_User\Documents\ar-avatar-demo\model.usdz"
```

Expected: 両ファイルが存在し、サイズが0バイトでない（数百KB〜数MB程度が目安）。

もしエラーが出る場合:
- `import_scene.fbx` でエラー → FBXファイルが破損しているか、パスが間違っている
- `export_scene.gltf` / `wm.usd_export` でパラメータエラー → Blenderのバージョンでオペレーターの引数名が変わっている可能性があるため、Blender内のPythonコンソールで `bpy.ops.export_scene.gltf.get_rna_type().properties` 等を見て実際の引数名を確認する

- [ ] **Step 3: コミット**

```bash
git add model.glb model.usdz
git commit -m "asset: convert avatar to GLB/USDZ for WebAR"
```

---

### Task 5: model-viewerを使ったindex.htmlを作成する

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\index.html`

- [ ] **Step 1: index.htmlを書く**

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ARアバターデモ</title>
  <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js"></script>
  <style>
    html, body { margin: 0; height: 100%; }
    model-viewer { width: 100vw; height: 100vh; background-color: #eee; }
    #ar-button {
      background-color: #fff;
      border-radius: 8px;
      border: none;
      padding: 12px 20px;
      position: absolute;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%);
      font-size: 16px;
    }
  </style>
</head>
<body>
  <model-viewer
    src="model.glb"
    ios-src="model.usdz"
    alt="改変アバター"
    ar
    ar-modes="quick-look"
    camera-controls
    autoplay
    shadow-intensity="1">
    <button id="ar-button" slot="ar-button">ARで見る</button>
  </model-viewer>
</body>
</html>
```

Note: `animation-name` 属性は指定していない。model-viewerは `autoplay` 指定時、アニメーション名を省略すると最初の（＝唯一の）クリップを自動再生するため、Mixamoのクリップ名を気にする必要がない。複数アニメーションが埋め込まれていて意図しないものが再生される場合のみ、`animation-name="<クリップ名>"` を追加する。

- [ ] **Step 2: コミット**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add index.html
git commit -m "feat: add model-viewer based AR demo page"
```

---

### Task 6: ローカルで表示確認する

iPhone実機がなくても、3Dモデルが正しく読み込まれてアニメーションが再生されるかはPC上のブラウザで確認できる（AR Quick Look自体はiOS実機でしか動かないので、その部分は次のTaskで確認する）。

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\.claude\launch.json`

- [ ] **Step 1: launch.jsonを作成**

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "ar-avatar-demo",
      "runtimeExecutable": "python",
      "runtimeArgs": ["-m", "http.server", "8080"],
      "port": 8080
    }
  ]
}
```

- [ ] **Step 2: preview_startでサーバーを起動し、preview_screenshotとpreview_console_logsで確認**

実行者（エージェント）は `mcp__Claude_Preview__preview_start` で `ar-avatar-demo` を起動し、`http://localhost:8080/index.html` を開いて以下を確認する:
- `preview_console_logs` でエラーが出ていないこと
- `preview_screenshot` でアバターの3Dモデルが表示され、勝手に動いている（アニメーション再生中）こと
- `preview_snapshot` で「ARで見る」ボタン要素が存在すること（クリックしてもAR自体は起動しない。iOS実機専用のため）

- [ ] **Step 3: 問題があれば修正**

モデルが表示されない・真っ黒・エラーが出る場合は、Task 4のGLB出力を疑い、`model.glb` を https://gltf-viewer.donmccurdy.com/ 等の一般的なオンラインGLBビューアで開いて中身を確認する。

---

### Task 7: GitHub Pagesへデプロイする

**Files:**
- なし（GitHubリポジトリ作成とPages設定のみ）

- [ ] **Step 1: デフォルトブランチ名を確認**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git branch --show-current
```

- [ ] **Step 2: GitHubリポジトリを作成してpush**

```bash
gh repo create ar-avatar-demo --public --source=. --remote=origin --push
```

- [ ] **Step 3: GitHub Pagesを有効化**

Step 1で確認したブランチ名を使う（例では `master`。`main` の場合はそこを置き換える）:

```bash
gh api -X POST /repos/hasegawakasyouen/ar-avatar-demo/pages -f "source[branch]=master" -f "source[path]=/"
```

- [ ] **Step 4: 公開URLを確認**

```bash
gh api /repos/hasegawakasyouen/ar-avatar-demo/pages --jq .html_url
```

Expected: `https://hasegawakasyouen.github.io/ar-avatar-demo/` が返る。反映まで数分かかることがある。

---

### Task 8: iPhone実機でAR動作確認する（手動）

この工程はWindows環境からは実行できないため、実機での確認手順のみ示す。

**Files:** なし

- [ ] **Step 1: iPhoneのSafariで公開URLを開く**

`https://hasegawakasyouen.github.io/ar-avatar-demo/` をSafariで開く

- [ ] **Step 2: 3Dモデルが表示され、アニメーションがループ再生されることを確認**

- [ ] **Step 3: 「ARで見る」ボタンをタップ**

Apple標準のAR Quick Lookが起動することを確認

- [ ] **Step 4: 平面検出→配置→アニメーション再生を確認**

床や机の上をカメラでなぞって平面検出させ、タップして配置。アバターがその場でループアニメーションを再生し続けることを確認

- [ ] **Step 5: 問題があれば記録**

うまくいかない場合、症状（モデルが出ない/アニメーションが止まる/配置できない）をメモし、Task 4のBlenderエクスポート設定を見直す

---

### Task 9: README.md を書く（将来のBOOTHテンプレート化を見据えて）

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\README.md`

- [ ] **Step 1: README.mdを書く**

```markdown
# ARアバターデモ

VRChat改変アバターをiPhoneのAR Quick Lookで表示するWebARデモ。

## 仕組み

- `model.glb` / `model.usdz`: アバターの3Dモデル+アニメーション
- `index.html`: `<model-viewer>` を使った表示ページ（このファイルは変更不要）

## 自分のアバターに差し替える手順

1. VRChatアップロード用UnityプロジェクトからアバターのFBXを取得し、`source/` に置く
2. https://www.mixamo.com でFBXをアップロードし、自動リギング後に好きなアニメーション（Idle等）を選んで
   `FBX Binary / With Skin / 30fps` でダウンロードし、`source/avatar_idle_mixamo.fbx` として保存する
3. 以下を実行して `model.glb` / `model.usdz` を再生成する

   ```bash
   "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- source\avatar_idle_mixamo.fbx model.glb model.usdz
   ```

4. GitHub Pages等の静的ホスティングにアップロードすれば、iPhoneのSafariから「ARで見る」でAR表示できる

## 既知の制限

- iOS Safari（AR Quick Look）専用。Android/デスクトップは3Dプレビューのみ
- 再生できるのは1本のループアニメーションのみ（複数モーション切り替えは非対応）
```

- [ ] **Step 2: コミット**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add README.md
git commit -m "docs: add README with avatar replacement instructions"
git push
```

---

## Self-Review メモ

- **Spec網羅性**: design spec の各セクション（アーキテクチャ/ファイル構成/パイプライン/動作確認/制限/スコープ外）に対応するTaskをすべて用意した
- **プレースホルダ**: 「TBD」「後で」は含まない。Mixamoの手動操作・iPhone実機確認はスコープ上どうしても自動化できない部分であり、正確な手順を明記した
- **型/名称の一貫性**: `convert_to_web.py` の引数仕様（`<input_fbx|--smoketest> <output_glb> <output_usdz>`）はTask 2のスモークテストとTask 4の本番実行で同一
