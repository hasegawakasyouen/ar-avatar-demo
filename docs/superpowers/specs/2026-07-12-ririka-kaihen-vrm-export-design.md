# 「りりか 黒猫悪夢」VRM化 設計書

- 日付: 2026-07-12
- 対象リポジトリ: `ar-avatar-demo`（既存のVRMエクスポートパイプラインを拡張）

## 目的

VRChat用に改変済みの別アバター「りりか 黒猫悪夢」（`D:\VRChatCreatorCompanion\VRChatProjects\りりか　黒猫悪夢\`、Modular Avatar/NDMFで非破壊構築）をVRM 1.0化し、[[project-desktop-vrm-mascot]]で選べる新しい見た目として使えるようにする。デスクトップアプリ自体は「任意のVRMファイルを読み込める」既存設計のため、VRM化さえ終われば**アプリ側のコード変更は不要**（タスクトレイの「VRMを選択」から選ぶだけ）。

## 前提として確認済みの事実

- Unity側でNDMFの「Manual Bake Avatar」により非破壊変更を確定させた複製オブジェクトから、Unity公式FBX ExporterでBinary形式のFBXを書き出し済み: `D:\VRChatCreatorCompanion\VRChatProjects\りりか　黒猫悪夢\Assets\ririka 黒猫悪夢(Clone).fbx`（約47MB）
  - **重要な罠**: Unity FBX Exporterのデフォルト書き出し形式はASCIIで、BlenderのFBXインポーターはASCII形式に非対応（`RuntimeError: ASCIIファイルは...未対応です`）。書き出し時に必ず「Binary」形式を明示選択する必要がある（2026-07-12に実際に踏んで特定済み）
- Blenderでインポートして中身を確認済み: メッシュ77個・全て非表示なし（着せ替えバリエーションの非表示メッシュが残っていない＝正しくベイクされている証拠）、頂点数計21万、シェイプキー705個（`Body`メッシュ）
- **ボーン構造がririka_v1.0.9元素体とほぼ同じ命名規則**: `Spine`/`Chest`/`Neck`/`Head`/`sholder_L`/`Upperarm_L`/`Lowerarm_L`/`Upperleg_L`/`Lowerleg_L`/`Foot_L`（左右とも）が完全一致。ただし手のボーン名は`Left_Hand`/`Right_Hand`（アンダースコア区切り）で、元の`export_vrm.py`の`Left Hand`/`Right Hand`（スペース区切り）とは表記が異なる
- **Hipsボーンが単体で存在しない**: Armatureオブジェクト自体の名前が`Hips`になっており、`Spine`/`stomach`/`tail`/`Upperleg_L`/`Upperleg_R`/`Butt_L`/`Butt_R`等が単一の明示的な親ボーンを持たずルートレベルに並んでいる。VRM Humanoidの`hips`ボーン割り当てには実ボーンが必要なため、実装時に対応方法を検証する必要がある（詳細は「未解決の技術的検証事項」参照）
- **表情シェイプキーはririka_v1.0.9と同名のものが存在**: `happy`/`angry`/`sad`/`tear1`/`tear2`が完全一致。加えて`smile`/`joy`/`joy2`/`blink`/`brow_smile`/`brow_joy`/`brow_angry`/`mouth_smile`/`mouth_sad`等、左右分割版（`_L`/`_R`）を含めより豊富な選択肢が存在する
- 2つ目のArmatureオブジェクト`Bone`（7ボーン）が存在する。名前から翼(`wing_L`/`wing_R`)や腕アクセサリ用の小さな独立骨格と推測されるが、詳細未調査（本体のVRM化には無関係の可能性が高い）

## スコープ

**含む:**
- `ririka 黒猫悪夢(Clone).fbx`用の新規Blenderスクリプト（既存の`export_vrm.py`は改変しない。リリカ本体・アニメーションパイプラインに影響を与えないよう、このアバター専用の新規スクリプトとして作る）
- Hipsボーン欠如問題の解決（実装時に検証・決定）
- ボーンマッピング（既存`BONE_MAPPING`を土台に、`Left_Hand`/`Right_Hand`表記へ調整）
- 表情マッピング（`happy`/`angry`/`sad`をVRMプリセットへ、`crying`を`tear1`+`tear2`+`sad`のカスタム表情へ、`joy`を`joy`+`joy2`+`brow_joy`を組み合わせた新規カスタム表情へ。正確な組み合わせはBlenderレンダリングで見た目を確認してから確定する）
- VRM出力・three-vrmでの表示検証（`vrm-preview.html`を流用）

**含まない（別途相談）:**
- デスクトップアプリ側のコード変更（不要な設計のため）
- このアバター専用の新規モーション（歩行/食事/喜ぶ/泣きの4モーションは[[project-desktop-vrm-mascot]]のVRMA形式で既にアバター非依存に作られているため、リターゲティングは自動で行われる想定。ただしHumanoidボーンマッピングが不完全だと正しく動かない可能性があるため、VRM化後に実際にデスクトップアプリで動作確認する）
- 2つ目のArmature(`Bone`)の扱い（本体のVRM Humanoidマッピングに含めない。必要なら別途検討）
- BOOTH等での配布・販売（既存のライセンス未確認方針を踏襲。VRMメタ情報は最も制限の強い`onlyAuthor`/`personalNonProfit`/`prohibited`をデフォルトにする）

## アーキテクチャ

### 新規スクリプト `scripts/export_vrm_ririka_kaihen.py`

既存`export_vrm.py`と同じ構造（`ARMATURE_NAME`・`BONE_MAPPING`・`PRESET_EXPRESSION_MAPPING`・`CUSTOM_EXPRESSION_MAPPING`・`apply_bone_mapping()`・`apply_expression_mapping()`・`apply_meta()`・`bpy.ops.export_scene.vrm()`呼び出し）を踏襲しつつ、以下を新アバター向けに書き換える。

- `ARMATURE_NAME`: 実際にBlenderへインポートした後のArmatureオブジェクト名に合わせる（インポート時の名前衝突有無を実装時に確認）
- `BONE_MAPPING`: 既存の値を土台に、`left_hand`/`right_hand`を`Left_Hand`/`Right_Hand`に修正。`hips`の割り当ては「未解決の技術的検証事項」の結論に従う
- 入力元は`.blend`ファイルではなくFBXファイル（`ririka 黒猫悪夢(Clone).fbx`）なので、`open_source_file()`相当の処理を`bpy.ops.import_scene.fbx(filepath=...)`に置き換える（既存の`open_source_file()`は`.blend`専用のため流用不可）

### 表情マッピング（案、実装時にレンダリング確認して確定）

```python
PRESET_EXPRESSION_MAPPING = {
    "happy": (BODY_MESH_NAME, "happy"),      # + brow_smile, mouth_smile を追加バインドする可能性あり
    "angry": (BODY_MESH_NAME, "angry"),      # + brow_angry
    "sad": (BODY_MESH_NAME, "sad"),          # + mouth_sad
    # relaxed/surprised/視素(aa/ih/ou/ee/oh)は元の "nagomi"/"びっくり"/"vrc.v_*" が
    # このアバターにも存在するか実装時に確認する（未確認）
}

CUSTOM_EXPRESSION_MAPPING = {
    "crying": [
        (BODY_MESH_NAME, "sad"),
        (BODY_MESH_NAME, "tear1"),
        (BODY_MESH_NAME, "tear2"),
    ],
    "joy": [
        (BODY_MESH_NAME, "joy"),
        (BODY_MESH_NAME, "joy2"),
        (BODY_MESH_NAME, "brow_joy"),
    ],
}
```

複数シェイプキーを1つの表情にバインドする際の各`weight`値（今は全て1.0を想定）は、レンダリング結果を見て強すぎる/弱すぎる場合に調整する。

## 未解決の技術的検証事項（実装の最初のタスクとして着手する）

1. **Hipsボーンの扱い**: Armatureオブジェクトの名前が`Hips`で、実ボーンとしての`Hips`が存在しない。以下のいずれかで解決する（実装時にBlenderで実際にボーン階層を目視確認してから判断する）:
   - Armatureのルートに、既存のルートレベルボーン群（`Spine`等）の共通の親となる新しい`Hips`ボーンを1本追加する
   - あるいはFBXインポート設定次第でボーン階層の解釈が変わる可能性があるため、インポートオプションを変えて再確認する
2. **`Bone`アーマチュア（7ボーン）の扱い**: 本体のHumanoidマッピングには使わない想定だが、非表示か削除かは実装時に見た目を確認して判断する
3. **視素(リップシンク)・relaxed/surprised用シェイプキーの有無**: 705個のシェイプキー全件は未確認。実装の最初のステップで`vrc.v_*`・`nagomi`・`びっくり`相当のキーが存在するか確認する

## 検証方法

既存プロジェクトで確立した手法を踏襲する。

1. Blenderでのレンダリング画像による表情の見た目確認（複数のシェイプキー組み合わせ候補を比較してから最終決定）
2. `ar-avatar-demo/vrm-preview.html`（Browser pane + `preview_start`）でVRMの読み込み・表示を確認
3. VRM化が完了したら、[[project-desktop-vrm-mascot]]で実際にこのVRMを選択し、既存の4モーション（歩行/食事/喜ぶ/泣き）が正しくリターゲティングされて動くか、表情（happy/crying/joy）が正しく発火するかを最終確認する
