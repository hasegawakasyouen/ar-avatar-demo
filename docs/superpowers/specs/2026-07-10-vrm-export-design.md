# リリカアバターのVRM化 設計書

- 日付: 2026-07-10
- 対象リポジトリ: `ar-avatar-demo`
- 元素材: `D:\VRアバター\アバター\リリカアバター\解凍\身体\ririka_v1.0.9\ririka\ririka.blend`（読み取り専用として扱う。このファイル自体は一切変更しない）

## 目的

将来のデスクトップ常駐マスコットアプリ（別spec、`three-vrm`でVRMを読み込み任意アバターを動かす方式）に向けて、リリカアバターをVRM 1.0形式でも出力できるようにする。既存のBlender→Mixamo→GLB/USDZパイプライン（`ar-avatar-demo/scripts/`）とは別の出力経路として追加する。

## 前提として確認済みの事実

Blenderをheadlessで実行し、`ririka.blend`を直接調査して確認済み（推測ではない）:

- `Body`メッシュ（顔・胴体本体）は337ボーンの`Armature`（メインの方。`Armature.001`という別の80ボーン簡易アバターも存在するが、それは`Boots_c2`/`Cloth2_Outer`/`Cloth2_Pants`/`Leg warmers`の一部服飾メッシュにしか使われておらず、`Body`本体とは無関係）にウェイトされている
- メインの`Armature`（337ボーン）には、VRM Humanoidが要求する骨がすべて実在する（詳細は下記マッピング表）。残り約250本は髪・スカート・しっぽ・バッグ等の物理揺れもの用ボーンで、Humanoidマッピングの対象外
- `Body`メッシュには表情用シェイプキーが既に用意されている: `happy`/`angry`/`sad`/`joy`/`smile`/`tear1`/`tear2`、VRChat標準ビゼム（`vrc.v_aa`等）、`blink`/`blink_L`/`blink_R`、MMD用の日本語名表情（`びっくり`＝驚き 等）
- 実行環境のBlenderは4.5.2 LTS。GUIなしのheadless実行のみ可能なため、VRM Add-onの操作はPython API経由で行う（手作業でのボーンマッピングUI操作はできない）

## スコープ外

- 物理演算（VRMのSpringBone設定）は今回は対象外。髪・スカート等の揺れものボーンは今回のHumanoidマッピングには含めない（将来必要になれば別specで対応）
- 表情アニメーション自体（どう動かすか）は対象外。今回はVRMファイル側に表情ブレンドシェイプを正しく登録するところまで
- デスクトップアプリ本体（`three-vrm`での読み込み・操作）は別spec。今回は「正しいVRMファイルが1つ手に入る」ことがゴール

## アーキテクチャ

- 新規スクリプト `ar-avatar-demo/scripts/export_vrm.py` を追加する。既存の`prepare_for_mixamo.py`/`convert_to_web.py`と同じく、Blender headless（`--background --python`）で実行する
- 実行フロー:
  1. `ririka.blend`を開く（保存はしない。VRM出力は別ファイルとして書き出す）
  2. VRM Add-on for Blenderをインストール済みであることを前提とする（未インストールの場合はインストール手順を別途実施。Blender 4.2以降のExtensions基盤経由か手動zipインストールかは実装時に確認する）
  3. `Armature`オブジェクトに対し、`vrm_addon_extension`のPython APIでHumanoidボーンマッピングを設定する（下記マッピング表の通り）
  4. `Body`メッシュのシェイプキーをVRM Expression（表情プリセット・カスタム表情）に登録する（下記マッピング表の通り）
  5. `bpy.ops.export_scene.vrm()`でVRM 1.0形式としてエクスポートする。出力先は`ar-avatar-demo/model.vrm`
- 元の`.blend`ファイルには一切書き込まない（読み込み後、必要な設定はメモリ上のシーンに対してのみ行い、`save_mainfile`は呼ばない）

## Humanoidボーンマッピング表

| VRM Humanoidボーン | リリカ側のボーン名 |
|---|---|
| hips | Hips |
| spine | Spine |
| chest | Chest |
| neck | Neck |
| head | Head |
| leftShoulder / rightShoulder | sholder_L / sholder_R |
| leftUpperArm / rightUpperArm | Upperarm_L / Upperarm_R |
| leftLowerArm / rightLowerArm | Lowerarm_L / Lowerarm_R |
| leftHand / rightHand | Left Hand / Right Hand |
| leftUpperLeg / rightUpperLeg | Upperleg_L / Upperleg_R |
| leftLowerLeg / rightLowerLeg | Lowerleg_L / Lowerleg_R |
| leftFoot / rightFoot | Foot_L / Foot_R |
| leftToes / rightToes | Toe_L / Toe_R |
| leftEye / rightEye | eye_L / eye_R |
| left/rightThumbMetacarpal, Proximal, Distal（VRM 1.0では"Intermediate"は無し） | Thumb Proximal/Intermediate/Distal_L・R（リリカ側は3段階ともProximal/Intermediate/Distal名のため1段階前へずらしてマッピング） |
| left/rightIndexProximal, Intermediate, Distal | Index Proximal/Intermediate/Distal_L・R |
| left/rightMiddleProximal, Intermediate, Distal | Middle Proximal/Intermediate/Distal_L・R |
| left/rightRingProximal, Intermediate, Distal | Ring Proximal/Intermediate/Distal_L・R |
| left/rightLittleProximal, Intermediate, Distal | Little Proximal/Intermediate/Distal_L・R |
| upperChest | 該当ボーンなし（未設定。VRM仕様上オプション） |
| jaw | 該当ボーンなし（未設定。VRM仕様上オプション） |

LookAt（視線制御）は`eye_L`/`eye_R`ボーンが存在するため、ブレンドシェイプ方式ではなく**ボーン回転方式**を採用する。

## 表情（Expression）マッピング表

| VRM Expression | 種別 | 対応するシェイプキー |
|---|---|---|
| happy | プリセット | happy |
| angry | プリセット | angry |
| sad | プリセット | sad |
| relaxed | プリセット | nagomi |
| surprised | プリセット | びっくり |
| aa | プリセット（リップシンク） | vrc.v_aa |
| ih | プリセット（リップシンク） | vrc.v_ih |
| ou | プリセット（リップシンク） | vrc.v_ou |
| ee | プリセット（リップシンク） | vrc.v_e |
| oh | プリセット（リップシンク） | vrc.v_oh |
| blink | プリセット | blink |
| blinkLeft | プリセット | blink_L |
| blinkRight | プリセット | blink_R |
| crying（カスタム表情） | カスタム | tear1 + tear2（複数バインド。sadと組み合わせて泣き顔を構成） |

`crying`をカスタム表情として登録するのは、今回のデスクトップマスコット企画の「泣く」演出に直接使うことを見越した対応。VRM標準プリセットには「泣く」に相当するものが無いため、VRM 1.0のカスタム表情機能で追加する。

## 検証方法

1. **エクスポート直後のファイル検証**: 出力された`model.vrm`のファイルサイズが0でないこと、glTF/VRM拡張として有効なJSON構造を持つこと（バイナリglTFのヘッダーとJSONチャンクをPythonで軽くパースして確認する）
2. **three-vrmでの実描画検証**: `ar-avatar-demo`内に一時的な検証用HTMLページ（`vrm-preview.html`等、正式な機能としては残さない使い捨てページ）を作り、`@pixiv/three-vrm`で`model.vrm`をロードして表示する。Previewツールでこのページを開き:
   - モデルが人型として正しくレンダリングされる（ボーンマッピング崩れでメッシュが変形していないか）
   - `happy`/`angry`/`sad`/`crying`の表情をJSから切り替えて、対応する表情が実際に変化することを確認する
   - リップシンク用の`aa`/`ih`/`ou`/`ee`/`oh`も同様に確認する
3. 実機（VRoid Hub等の外部VRMビューアーへのアップロード確認）は本specの範囲外（必要なら別途ユーザー側で実施）

## エラーハンドリング

- VRM Add-onが未インストール、またはPython APIの構造がバージョンによって想定と異なる場合、その時点で処理を止めて具体的なエラー内容を報告する（当て推量で別のプロパティ名を試行錯誤し続けない）
- ボーンマッピング表に無いボーン名（typo等）を指定してAPI呼び出しがエラーになった場合も同様に、実際のボーン名を再調査した上で報告する
