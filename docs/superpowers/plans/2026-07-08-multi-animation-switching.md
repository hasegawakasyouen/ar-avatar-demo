# 複数アニメーション追加・タップ切り替え Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** アバターに合計3本のアニメーション（idle + 新規2本）を持たせ、`vrc-mascot-pwa`のタップ操作で順番に切り替えられるようにする。`ar-avatar-demo`の見た目は変更しない。

**Architecture:** Mixamoで同じリギング済みキャラクターに別アニメーションを適用してダウンロードし、`scripts/convert_to_web.py`を拡張して1回のBlenderセッション内で複数アニメーションを合成、`model.glb`/`model.usdz`に埋め込む。`vrc-mascot-pwa`のタップハンドラーに`animation-name`切り替えロジックを追加する。

**Tech Stack:** Blender 4.5（bpy headless script拡張）, Mixamo（追加アニメーション取得、手動）, model-viewer `availableAnimations`/`animationName` API

**確認済みの環境:**
- Blender: `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`
- `ar-avatar-demo`: `C:\Users\PC_User\Documents\ar-avatar-demo`（既存の`scripts/convert_to_web.py`・`source/avatar_idle_mixamo.fbx`・公開中の`model.glb`/`model.usdz`あり）
- `vrc-mascot-pwa`: `C:\Users\PC_User\Documents\vrc-mascot-pwa`（既存の`index.html`・`sw.js`あり。公開中）
- 両プロジェクトとも branch master に直接コミットでOK（既存プロジェクトと同じ前提）

---

### Task 1: Mixamoで追加アニメーションを2本取得する（手動）

**Files:**
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_wave_mixamo.fbx`
- Create: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_dance_mixamo.fbx`

- [ ] **Step 1: Mixamoで既存のリギング済みキャラクターを開く**

https://www.mixamo.com にアクセスし、以前アップロード・自動リギングした「リリカ」のキャラクターが `CHARACTERS` 一覧に残っていることを確認する（再アップロード・再リギングは不要）。

- [ ] **Step 2: 1本目の追加アニメーション「手を振る」を取得**

1. アニメーション一覧から「Waving」等、手を振るモーションを検索して選択
2. プレビューで不自然な動きがないか確認
3. 「DOWNLOAD」→ Format: `FBX Binary(.fbx)` / Skin: `With Skin` / FPS: `30` / Keyframe Reduction: `none`
4. `source\avatar_wave_mixamo.fbx` として保存

- [ ] **Step 3: 2本目の追加アニメーション「ダンス」を取得**

1. 同じキャラクターのまま、アニメーション一覧から「Dancing」等のダンスモーションを検索して選択
2. 同様にダウンロードし、`source\avatar_dance_mixamo.fbx` として保存

- [ ] **Step 4: コミット**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add source/avatar_wave_mixamo.fbx source/avatar_dance_mixamo.fbx
git commit -m "asset: add wave and dance Mixamo animations for the same rigged character"
```

---

### Task 2: `scripts/convert_to_web.py` を拡張し、スモークテストで後方互換性を確認する

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\scripts\convert_to_web.py`

- [ ] **Step 1: スクリプトを書き換える**

```python
# scripts/convert_to_web.py
import bpy
import sys


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python convert_to_web.py "
            "-- <input_fbx|--smoketest> <output_glb> <output_usdz> [extra_anim_fbx...]"
        )
    return argv[argv.index("--") + 1:]


def harvest_extra_animations(extra_anim_paths):
    for anim_path in extra_anim_paths:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=anim_path)
        imported = [o for o in bpy.data.objects if o not in before]
        armature = next((o for o in imported if o.type == 'ARMATURE'), None)
        if armature and armature.animation_data and armature.animation_data.action:
            armature.animation_data.action.use_fake_user = True
        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)


def export_glb_and_usdz(output_glb, output_usdz):
    bpy.ops.export_scene.gltf(
        filepath=output_glb,
        export_format='GLB',
        export_animations=True,
        export_animation_mode='ACTIONS',
    )
    bpy.ops.wm.usd_export(
        filepath=output_usdz,
        export_animation=True,
    )


def main():
    args = get_args()
    if len(args) < 3:
        raise SystemExit(
            "Expected at least 3 args: <input_fbx|--smoketest> <output_glb> <output_usdz> [extra_anim_fbx...]"
        )
    mode, output_glb, output_usdz = args[0], args[1], args[2]
    extra_anim_paths = args[3:]

    if mode == "--smoketest":
        # Blenderの初期シーン(Cube/Light/Camera)をそのまま使う
        bpy.ops.wm.read_factory_settings(use_empty=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=mode)

    if extra_anim_paths:
        harvest_extra_animations(extra_anim_paths)

    export_glb_and_usdz(output_glb, output_usdz)
    print("CONVERT_OK", output_glb, output_usdz)


main()
```

**重要 — 実装者への注意:** `export_animation_mode='ACTIONS'` というパラメータ名・値は、Blenderのバージョンによって異なる可能性がある（正式なenum値は `'ACTIONS'`, `'ACTIVE_ACTIONS'`, `'NLA_TRACKS'`, `'SCENE'` 等）。これは「合成した複数のActionをすべて別々のglTFアニメーションとして書き出す」ためのモードである必要がある。Blender 4.5で実際にこのスクリプトを実行してエラーが出た場合、または実行はできても最終的なGLBにアニメーションが1本しか入らなかった場合は、Blender内のPythonコンソールで `bpy.ops.export_scene.gltf.get_rna_type().properties['export_animation_mode'].enum_items.keys()` 等を確認し、正しい値に修正すること。この検証はTask 3で実データを使って行う。

- [ ] **Step 2: スモークテストを実行し、3引数の従来動作が壊れていないことを確認**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- --smoketest smoketest.glb smoketest.usdz
```

Expected: `CONVERT_OK smoketest.glb smoketest.usdz` が出力され、終了コード0。ファイルが生成される（`.gitignore`済みなので確認後削除してよい）。

- [ ] **Step 3: コミット**

```bash
git add scripts/convert_to_web.py
git commit -m "feat: extend convert_to_web.py to merge extra animation-only FBX files"
```

---

### Task 3: 実際に3本のアニメーションを合成したGLB/USDZを生成し、検証する

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\model.glb`
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\model.usdz`

- [ ] **Step 1: 拡張したスクリプトで実際の合成を実行**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- source\avatar_idle_mixamo.fbx model.glb model.usdz source\avatar_wave_mixamo.fbx source\avatar_dance_mixamo.fbx
```

Expected: `CONVERT_OK model.glb model.usdz` が出力される。

- [ ] **Step 2: GLBのアニメーション数を検証**

`model.glb`の先頭12バイト（バイナリヘッダ）をスキップしてJSONチャンクを取り出し、`animations`配列の要素数が3であることを確認する（Pythonで直接パースするか、Blenderで再インポートして`bpy.data.actions`の数を確認する）。

- [ ] **Step 3: スキン・テクスチャが引き続き正しいことを確認**

`model.glb`のJSONを解析し、`skins`配列に33ジョイントのスキンが1件、`images`配列に複数の実テクスチャ（プレースホルダでない、実サイズのある画像）が含まれていることを確認する（前回のTask 4での確認方法と同様）。

- [ ] **Step 4: 3本のアニメーションがそれぞれ別の動きになっているか、実際に読み込んで目視確認する**

ローカルサーバーで`model.glb`をブラウザ（`<model-viewer>`等）に読み込み、`mascot.availableAnimations`の各要素を`mascot.animationName`に順番にセットして、都度スクリーンショットを撮る。3枚のスクリーンショットが明確に異なるポーズ・動きになっていることを確認する（すべて同じ、または壊れたメッシュになっていないか）。

- [ ] **Step 5: ファイルサイズが妥当かを確認**

```bash
ls -la model.glb model.usdz
```

Expected: アニメーションデータが増える分多少大きくなるが、極端な増加（数十MB規模）がないことを確認する。もし大きく増加していたら、テクスチャが重複して埋め込まれていないか疑う（アニメーション追加時にテクスチャが二重に埋め込まれるのは既知の失敗パターンではないが、念のため確認する）。

- [ ] **Step 6: コミット**

```bash
git add model.glb model.usdz
git commit -m "asset: merge wave and dance animations into model.glb/usdz (3 animations total)"
```

---

### Task 4: `ar-avatar-demo`のローカル回帰確認

**Files:** なし

- [ ] **Step 1: ローカルプレビューで`ar-avatar-demo`の`index.html`を開く**

今まで通り、`animation-name`未指定のまま最初のクリップ（idle）が自動再生されることを確認する。見た目・アニメーションの変化がないことを確認する（回帰確認）。

- [ ] **Step 2: 問題があれば記録し、修正**

もしidle以外のクリップが再生されてしまう場合、Blenderのアクション合成順序（`avatar_idle_mixamo.fbx`が最初にインポートされ、そのActionが最初の＝デフォルトのAction）を疑う。

---

### Task 5: `ar-avatar-demo`をGitHub Pagesへpushする

**Files:** なし

- [ ] **Step 1: push**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git push
```

- [ ] **Step 2: 公開サイトが更新されたか確認**

```bash
curl -s -o "C:\Users\PC_User\AppData\Local\Temp\claude\live_model_check.glb" -w "%{http_code}\n" https://hasegawakasyouen.github.io/ar-avatar-demo/model.glb
```

ダウンロードした内容のファイルサイズが、ローカルの`model.glb`と一致することを確認する。確認後、一時ファイルは削除する。

---

### Task 6: `vrc-mascot-pwa`にモデルをコピーし、タップ切り替えロジックを追加する

**Files:**
- Modify: `C:\Users\PC_User\Documents\vrc-mascot-pwa\model.glb`（上書きコピー）
- Modify: `C:\Users\PC_User\Documents\vrc-mascot-pwa\model.usdz`（上書きコピー）
- Modify: `C:\Users\PC_User\Documents\vrc-mascot-pwa\index.html`

- [ ] **Step 1: モデルファイルをコピー**

```bash
cp "C:\Users\PC_User\Documents\ar-avatar-demo\model.glb" "C:\Users\PC_User\Documents\vrc-mascot-pwa\model.glb"
cp "C:\Users\PC_User\Documents\ar-avatar-demo\model.usdz" "C:\Users\PC_User\Documents\vrc-mascot-pwa\model.usdz"
```

- [ ] **Step 2: `index.html`のタップハンドラーにアニメーション切り替えロジックを追加**

現在の`index.html`のタップハンドラーは以下のようになっている（`try`ブロック内）:

```javascript
      try {
        mascot.classList.add('tapped');
        if (mascot.loaded) {
          baseFov = mascot.getFieldOfView();
          mascot.fieldOfView = `${baseFov * 0.92}deg`;
        }
      } finally {
```

この`try`ブロックの中、`if (mascot.loaded) { ... }`ブロックの直後（`} finally {`の直前）に、以下を追加する:

```javascript
        const anims = mascot.availableAnimations;
        if (anims && anims.length > 1) {
          const current = anims.indexOf(mascot.animationName);
          const next = (current + 1) % anims.length;
          mascot.animationName = anims[next];
          mascot.currentTime = 0;
          mascot.play();
        }
```

結果として、`try`ブロック全体は以下のようになる:

```javascript
      try {
        mascot.classList.add('tapped');
        if (mascot.loaded) {
          baseFov = mascot.getFieldOfView();
          mascot.fieldOfView = `${baseFov * 0.92}deg`;
        }
        const anims = mascot.availableAnimations;
        if (anims && anims.length > 1) {
          const current = anims.indexOf(mascot.animationName);
          const next = (current + 1) % anims.length;
          mascot.animationName = anims[next];
          mascot.currentTime = 0;
          mascot.play();
        }
      } finally {
```

既存のARボタン用ガード（`event.target.closest('#ar-button')`）・`reacting`フラグ・`finally`ブロックのロジックは一切変更しないこと。

- [ ] **Step 3: コミット**

```bash
cd "C:\Users\PC_User\Documents\vrc-mascot-pwa"
git add model.glb model.usdz index.html
git commit -m "feat: cycle through avatar animations on tap (3 animations available)"
```

---

### Task 7: `vrc-mascot-pwa`のローカル動作確認

**Files:** なし

- [ ] **Step 1: ローカルプレビューでタップごとにアニメーションが切り替わることを確認**

MutationObserverまたは`preview_eval`で`mascot.animationName`の値を記録しながら3回連続タップし、3回とも異なるアニメーション名に切り替わり、4回目で最初のアニメーションに戻る（サイクルする）ことを確認する。

- [ ] **Step 2: 既存の回帰確認を再実施**

- ARボタンをタップしてもアニメーション切り替え・バウンド演出が誤って発火しないこと（前回実装した`stopPropagation`のガードが引き続き機能していること）
- タップ時のバウンド＋ズーム演出が引き続き正しく動作すること
- Service Worker（`sw.js`）のキャッシュが新しい`model.glb`/`model.usdz`を正しく取得・キャッシュすること（Cache Storageの中身を確認）

- [ ] **Step 3: 問題があれば修正**

---

### Task 8: `vrc-mascot-pwa`のキャッシュバージョンを上げてGitHub Pagesへpushする

**Files:**
- Modify: `C:\Users\PC_User\Documents\vrc-mascot-pwa\sw.js`

- [ ] **Step 1: `CACHE_VERSION`を上げる**

`sw.js`冒頭の `const CACHE_VERSION = 'mascot-cache-v1';` を `'mascot-cache-v2';` に変更する（README記載のキャッシュ更新手順に従う）。

- [ ] **Step 2: コミット・push**

```bash
cd "C:\Users\PC_User\Documents\vrc-mascot-pwa"
git add sw.js
git commit -m "chore: bump cache version after adding wave/dance animations"
git push
```

- [ ] **Step 3: 公開サイトが更新されたか確認**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://hasegawakasyouen.github.io/vrc-mascot-pwa/model.glb
```

Expected: 200

---

### Task 9: 両プロジェクトをiPhone実機で確認する（手動）

**Files:** なし

- [ ] **Step 1: `ar-avatar-demo`の公開URLをiPhoneのSafariで開く**

`https://hasegawakasyouen.github.io/ar-avatar-demo/` を開き、今まで通りidleアニメーションのみが再生されることを確認する（回帰確認）。

- [ ] **Step 2: `vrc-mascot-pwa`の公開URLをiPhoneのSafariで開く**

`https://hasegawakasyouen.github.io/vrc-mascot-pwa/`（またはホーム画面のアイコン）から開き、以下を確認する:
- 画面をタップするたびにアニメーションが切り替わる（3種類を順番にサイクルする）
- バウンド＋ズームの演出も引き続き機能する
- 「ARで見る」ボタンが誤ってアニメーション切り替えを発火させない
- AR Quick Look自体も引き続き正常に起動する

- [ ] **Step 3: 問題があれば記録**

---

### Task 10: 両プロジェクトのREADMEを更新する

**Files:**
- Modify: `C:\Users\PC_User\Documents\ar-avatar-demo\README.md`
- Modify: `C:\Users\PC_User\Documents\vrc-mascot-pwa\README.md`

- [ ] **Step 1: `ar-avatar-demo`のREADMEに複数アニメーション対応を追記**

「自分のアバターに差し替える手順」内、Mixamoでのアニメーション取得手順の後に、以下を追記する:

```markdown
### 複数アニメーションを追加する場合

同じリギング済みキャラクターに対して、Mixamoでアニメーションを選び直せば再アップロード不要で追加のアニメーションFBXを取得できます。取得したFBXを `scripts/convert_to_web.py` の第4引数以降に渡すと、メッシュ・テクスチャは変更せずアニメーションだけを追加で合成できます:

```bash
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- source\avatar_idle_mixamo.fbx model.glb model.usdz source\avatar_wave_mixamo.fbx source\avatar_dance_mixamo.fbx
```

3引数のみ（追加アニメなし）で呼び出した場合の動作は従来通りです。
```

- [ ] **Step 2: `vrc-mascot-pwa`のREADMEにタップ切り替えの説明を追記**

「既知の制限・注意点」セクションの「アニメーション切り替え非対応」の行を、以下に置き換える:

```markdown
- **アニメーションはタップで順送り切り替え** — `model.glb`に複数のアニメーションクリップが入っている場合、タップのたびに次のクリップへ自動で切り替わります（`mascot.availableAnimations`のインデックス順）。選択メニュー等のUIはありません
```

- [ ] **Step 3: 両方をコミット・push**

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add README.md
git commit -m "docs: document multi-animation merging workflow"
git push

cd "C:\Users\PC_User\Documents\vrc-mascot-pwa"
git add README.md
git commit -m "docs: update animation-switching description in known limitations"
git push
```

---

## Self-Review メモ

- **Spec網羅性**: design spec の各セクション（パイプライン拡張/タップ切り替え/動作確認/スコープ外）に対応するTaskをすべて用意した
- **プレースホルダ**: 「TBD」「後で」は含まない。Blenderの `export_animation_mode` の正確な値のみ実行時検証が必要な旨を明記しているが、これは「未定」ではなく「実行時にAPIを確認して調整する」という具体的な指示
- **型/名称の一貫性**: `scripts/convert_to_web.py` のCLI契約（3引数+可変長の追加アニメ引数）はTask 2・Task 3・Task 10のREADME追記で一貫している。`index.html`の`try/finally`構造・`reacting`フラグ・ARボタンガードはTask 6で変更しないことを明記
