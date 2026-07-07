# 複数アニメーション追加・タップ切り替え 設計書

- 日付: 2026-07-08
- ステータス: 承認済み（brainstormingフェーズ完了）
- 対象プロジェクト: `ar-avatar-demo`（アニメーション合成パイプライン）＋ `vrc-mascot-pwa`（タップ切り替えUI）

## 背景・目的

現状、アバターには Mixamo 由来の idle アニメーション1本のみが入っている。合計3本（idle + 新規2本、例: 手を振る・ダンス）に増やし、`vrc-mascot-pwa` のタップ操作で順番に切り替えられるようにする。`ar-avatar-demo` 側の見た目・挙動は変更しない（今まで通り最初のクリップを自動再生するだけ）。

## 前提・制約

- `ar-avatar-demo` の `index.html` は変更しない（従来通りidleのみ自動再生）
- アニメーション名のリネームや選択メニューUIは作らない（インデックスでの順送りのみ）
- 前回（テクスチャ修正の再現性問題）の反省を踏まえ、FBXの保存・再読込を挟む方式は避け、1回のBlenderセッション内でメッシュ＋複数アニメーションを合成してそのままGLB/USDZに出力する

## パイプライン（ar-avatar-demo側）

### Step 1: Mixamoで追加アニメーションを取得（手動）

既にAuto-rigger済みの同じキャラクターに対して、Mixamoの画面で別のアニメーションを選び直してダウンロードする。骨格ストリップ・デシメート・再アップロードは不要（同じリギング済みキャラクターを使い回せる）。ダウンロード形式は前回と同じ（`FBX Binary` / `With Skin` / `30fps` / `Keyframe Reduction: none`）。

### Step 2: `scripts/convert_to_web.py` の拡張

現在のCLI契約（`<input_fbx|--smoketest> <output_glb> <output_usdz>`、厳密に3引数）を後方互換を保ったまま拡張する:

```
blender --background --python convert_to_web.py -- <input_fbx|--smoketest> <output_glb> <output_usdz> [追加アニメFBX...]
```

- 引数が3個のみ（従来通り）の場合の動作は変更しない
- 4個目以降の引数は「アニメーションデータだけを使う」追加FBXとして扱う:
  1. 各追加FBXをインポート
  2. インポートされたアーマチュアの Action を `use_fake_user = True` で保護
  3. インポートされたメッシュ・アーマチュアオブジェクト自体は削除（本体のメッシュ・テクスチャには一切触れない）
- 最終的に本体のアーマチュアに複数の Action が紐づいた状態で、GLBエクスポート時に `export_animation_mode='ACTIONS'`（または同等のBlender 4.5のオプション。実装時にAPIを確認・調整する）を指定し、すべてのActionを別々のglTFアニメーションとして書き出す
- テクスチャは常にマスターの `avatar_idle_mixamo.fbx`（既に正しく修正済み）のものだけを使う。FBXの保存・再読込を挟まないため、前回のテクスチャ透け不具合は再発しない設計

### Step 3: 出力確認

`model.glb` のJSONチャンクを解析し、`animations` 配列に3件（idle・新規2本）入っていることを確認する。

## タップ時の切り替え（vrc-mascot-pwa側）

既存のタップハンドラー（バウンド＋ズーム演出、`index.html`）に、以下のロジックを追加する:

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

- アニメーション名（Mixamo由来の自動生成名）はリネームせず、`availableAnimations` のインデックスで順送りするだけの実装にする（名前に依存しないため、将来アニメーションを増やしても壊れない）
- 既存の try/finally によるリアクション処理（`reacting` フラグのリセット保証）はそのまま維持し、この切り替えロジックもその中に組み込む

## 動作確認方法

1. `scripts/convert_to_web.py` のスモークテスト（デフォルトCubeシーン、追加アニメ引数なし）を再実行し、3引数の従来動作が壊れていないことを確認
2. 実際に3本のアニメーションを合成した `model.glb`/`model.usdz` を生成し、GLBのJSONを解析して `animations` 配列に3件入っていること・スキン(33ジョイント)とテクスチャが引き続き正しいことを確認
3. `ar-avatar-demo` のローカルプレビューで、今まで通りidleのみが自動再生されることを確認（回帰確認）
4. `vrc-mascot-pwa` のローカルプレビューで、タップするたびにアニメーションが切り替わることを確認（MutationObserver等でアニメーション名の変化を検証）
5. `vrc-mascot-pwa` の既存のタップ関連の回帰確認（ARボタンとの二重発火がないこと等）を再実施
6. 両プロジェクトともGitHub Pagesへデプロイし、iPhone実機で確認

## スコープ外（今回やらないこと）

- アニメーション名の一覧表示・選択メニューUI
- `ar-avatar-demo` 側へのタップ切り替え機能の追加
- 4本目以降のアニメーション追加（将来必要になれば同じ仕組みで拡張可能）
