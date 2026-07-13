#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""「りりか 黒猫悪夢」のFBXをインポートし、単体で存在しないHipsボーンを
Armatureオブジェクトのローカル原点（実測でワールドZ=0.7251m、想定される腰の高さと一致）に
新規追加してSpine/Upperleg_L/Upperleg_Rを再ペアレントしたうえで、
作業用.blendとして保存する。元のFBX/Unityプロジェクトは一切変更しない。

Task 4のブラウザ実機検証で発覚したバグの修正:
すべてのメッシュがArmatureオブジェクト（このFBXでは"Hips"という名前）に
オブジェクトペアレント（parent_type='OBJECT'、Armatureモディファイアと併用）
されている。この状態でVRM Add-on（io_scene_gltf2ベース）がエクスポートすると、
メッシュノードがルートボーン"Hips"ノードの子としてグラフ上にネストされる一方、
スキニング用のbindMatrixは「メッシュはシーンルート相対でほぼ単位行列の位置にある」
という前提で計算される。実機検証（three-vrm）で確認した通り、結果として
bindMatrix=単位行列だがmatrixWorld=[0, 0.7251, 0.0244]（Hipsの実ワールド座標を
ノード階層経由で継承）という不一致が生じ、メッシュが崩壊して見える。

最初に「Armatureオブジェクト自身のワールド変換（Z=0.7251m等のオフセット）を
bpy.ops.object.transform_applyでボーンのレスト位置へ焼き込む」という対策を
単独で試したが、オフセットが物理的にHipsボーンのワールド座標として必ず
残る以上、ノード階層上でメッシュがHipsの子である限り同じ不一致が再現し、
効果がないことを実機検証で確認した（bindMatrix/matrixWorldとも変化なし）。

真因はメッシュがArmatureオブジェクトにオブジェクトペアレントされている
ことそのもの（エクスポータがこれを見てメッシュノードをルートボーンの子に
ネストする）。そのため、Hipsボーン追加後に対象メッシュのオブジェクトペアレントを
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')で解除する
（ワールド座標は維持したまま親子関係のみ外す）。Armatureモディファイアは
オブジェクト参照のみで機能し親子関係に依存しないため、非破壊スキニングは
維持される。これによりエクスポート後のメッシュノードはHipsの子ではなく
シーンルート直下の独立ノード（skinのみで変形）になり、二重変形が解消される
ことを実機検証で確認済み。

Armatureオブジェクト自身の変形も単位行列へ適用する（transform_apply）。
単独では上記バグを解決しないが、Blender公式が推奨するglTFエクスポート前の
一般的なベストプラクティスであり、メッシュのmatrix_parent_inverseを
Blenderが自動調整するため副作用もない。

ブランチ全体レビュー＋ユーザーのスクリーンショットによる実機確認で発覚した
不具合の修正: 元のVRChatアバターFBXには、Humanoidボディ本体とは無関係な
「小道具/UIギズモ」メッシュが多数（お絵描きタブレット風UI、モニター/ネオン
パネル、スマホ、食べ物・飲み物の小道具、ジェスチャー検出用Contact Receiverの
球体ギズモ等）含まれており、これらは元のVRChat/Unity側ではAnimatorレイヤーの
切り替えやエディタ専用表示で通常は非表示のはずだが、VRMエクスポート後は
常時表示のジオメトリとしてそのまま出力されてしまっていた。特に`Background`
という平面クアッドがキャラクターの顔正面を覆い、`Sphere_6`〜`Sphere_15`が
肩の高さで左右に浮くなど、見た目を著しく損なっていた。
全77メッシュオブジェクトを頂点数・ワールド座標・親オブジェクト・Armature
モディファイア有無で監査し、疑わしいものは単体ハイライトレンダリングで
視覚確認した上で、`hide_prop_meshes()`が対象メッシュの`hide_render`・
`hide_viewport`を両方Trueにする。VRM Add-onのエクスポート対象選定
（`export_invisibles`が未指定でFalseのまま）は`Object.visible_get()`
（hide_viewport依存）でオブジェクトを除外するため、実際に効いているのは
hide_viewport側だが、意図を一貫させるためhide_renderも合わせて設定する。

relink_broken_textures()でマゼンタのプレースホルダーを解消した後も、参考
画像（黒地に白トリムのゴシックドレス）と逆に衣装が白/クリーム色優勢に見える
問題が残っていた。実機検証（Base ColorをEmissionへ一時直結したunlitレンダー
でTex_Black.pngが黒地に白花柄レースという正しい配色を持つことを確認、UV
バウンディングボックスとピクセルサンプリングでUVマッピング自体は正常と確認、
material blend_method/alpha配線も概ね正常と確認）で切り分けた結果、真因は
UV・テクスチャのいずれでもなく、Mat_BlackVeil1〜4・Mat_WhiteVeil・Hair・
_3_Peach_Glow_Bob/Twin・Diamond・pearlの10マテリアルでPrincipled BSDFの
"Emission Color"が白(1,1,1,1)・"Emission Strength"が1.0のまま定数値で
残っていたことだった。これはUnity側マテリアルの"_EmissionColor"プロパティが
白のデフォルト値のまま残っている一方、Unity側では_EMISSIONキーワード自体が
無効化されていて実際には発光していなかった（Unityのシェーダはキーワード
無効時にプロパティ値を無視する）のが、FBXエクスポート/Blenderインポート時に
キーワードの有効・無効という文脈情報が失われ、プロパティの生値だけが
Principled BSDFのEmissionにそのままコピーされてしまった「幽霊発光」と判断
した（同じアバター内の他の"*_LLC_Clone_"マテリアル、例えばMat_Clothes/
Mat_Furball/Mat_Silk等はEmission Strength=0.0で正常なため、テクスチャや
命名規則が原因ではなくマテリアルごとに個別に持っていた値の違いであることを
確認済み）。定数の白色フル発光がBase Colorの上に単純加算されるため、本来
黒いはずのレース生地が白く洗い流されたように見えていた。`fix_phantom_emission()`
がこの10マテリアルのEmission Strengthを0.0にリセットする。実機検証（Blender
単体/合成レンダリング比較）で、この修正だけで参考画像どおりの黒地に白トリムの
配色に戻ることを確認済み。
"""
import math
import os
import sys

import bmesh
import bpy
import mathutils

ARMATURE_NAME = "Hips"
HUMANOID_CHAIN_ROOTS = ["Spine", "Upperleg_L", "Upperleg_R"]

# 実機検証（Blender 5.1でsource/ririka_kaihen.blendを開き、全マテリアルの
# TEX_IMAGEノードを監査）で判明: 「りりか 黒猫悪夢」の一部マテリアルは、
# Diffuse/Base ColorのTEX_IMAGEノードがUnity内部の".asset"でラップされた
# ランタイム専用テクスチャファイル（ZZZ_GeneratedAssets配下の*_llc_*.asset）を
# 参照しており、Blenderはこれをデコードできない
# （IMB_load_image_from_memory: unknown file-format、Image.size==(0,0)）。
# その結果、該当メッシュ（黒衣装の本体パーツ）がBlenderの標準マゼンタ/ピンク色の
# 「テクスチャ読み込み失敗」プレースホルダーで描画され、まるで別の
# ピンク系デフォルト衣装であるかのように見えていた。実際は別衣装ではなく
# 単なるテクスチャ参照切れであることを、同じ役割の他マテリアル
# （Mat_BlackVeil2_LLC_Clone_等）が正しく実ファイルTex_Black.pngを
# 参照して黒く描画されることと比較して確認済み。
#
# 壊れた参照は2パターンに分類される:
# 1. "Tex_Black_llc_*.asset" -> 実体は黒テクスチャ
#    D:\...\Assets\PuffyNightmare\Materials&Textures\Texture\A_Black&White\Tex_Black.png
#    と同一内容（同じ役割の他マテリアルが実際にこのファイルを正しく参照している
#    ことから確認）。
# 2. "UnityWhite_llc_*.asset" -> lilycalinventoryの内部規約と見られる
#    「テクスチャなし、フラット白のみ」を意味するプレースホルダー
#    （Unityプロジェクト内に対応する実ファイルが存在しない）。
#    画像を差し替える代わりに、TEX_IMAGEノードのColor出力の接続を切り、
#    接続先（実測では全ケースでPrincipled BSDFのBase Color）の
#    default_valueに直接白(1,1,1,1)を設定することで対応する。
REAL_TEX_BLACK_PATH = (
    r"D:\VRChatCreatorCompanion\VRChatProjects\りりか　黒猫悪夢\Assets"
    r"\PuffyNightmare\Materials&Textures\Texture\A_Black&White\Tex_Black.png"
)
TEX_BLACK_PREFIX = "Tex_Black_llc_"
UNITY_WHITE_PREFIX = "UnityWhite_llc_"
ZZZ_GENERATED_ASSETS_MARKER = "ZZZ_GeneratedAssets"

# 実機検証（Blender 5.1、Emissionを一時的にColor出力へ直結したunlitレンダー、
# 単体/合成レンダリング比較、three-vrmでの実機確認）で判明した第2の不具合の修正対象。
#
# relink_broken_textures()で壊れたテクスチャ参照を修復しマゼンタが解消した後も、
# 「黒猫悪夢」衣装（Dress/Dress2/Dress3/Sleevesメッシュ）が参考画像とは逆に
# 白/クリーム色優勢に見える問題が残っていた。原因はテクスチャ・UV・material
# blend_methodのいずれでもなかった（Base ColorをEmissionに直結してライティング
# を排除したunlitレンダーでは、Tex_Black.pngを正しくサンプリングした黒地に
# 白い花柄レース模様という、参考画像どおりの配色が正しく出ることを確認済み）。
#
# 真因: 以下10マテリアルのPrincipled BSDFの"Emission Color"が白(1,1,1,1)・
# "Emission Strength"が1.0のまま、いずれのソケットもテクスチャに接続されて
# いない（定数値）状態だった。これはUnity側マテリアルの"_EmissionColor"
# プロパティが白のデフォルト値のまま残っている一方、Unity側では_EMISSION
# キーワード自体が無効化されていて実際には発光していなかった（Unityの
# シェーダはキーワード無効時にプロパティ値を無視する）のが、FBXエクスポート/
# Blenderインポート時にキーワードの有効・無効という文脈情報が失われ、
# プロパティの生値だけがPrincipled BSDFのEmissionにそのままコピーされて
# しまったための「幽霊発光」であると判断した（同じ黒猫悪夢アバター内の
# 他の"*_LLC_Clone_"マテリアル、例えばMat_Clothes/Mat_Furball/Mat_Silk等は
# Emission Strength=0.0で正常なため、テクスチャや命名規則が原因ではなく
# マテリアルごとに個別に持っていた値の違いであることを確認済み）。
#
# 定数の白色フル発光（Strength=1.0）がBase Colorの上に単純加算されるため、
# 本来黒いはずのレース生地が白く洗い流されたように見えていた。実機検証
# （Blender単体レンダリング比較）で、この10マテリアルのEmission Strengthを
# 0.0にするだけで、参考画像どおりの黒地に白トリムの配色に戻ることを確認済み。
# "Dress/Dress2/Dress3/Sleeves"の範囲外（Hair・アクセサリー等）でも同一の
# 幽霊発光パターンを持つマテリアルは、同じ原因である以上まとめて修正する。
PHANTOM_EMISSION_MATERIAL_NAMES = [
    "Mat_BlackVeil1_LLC_Clone_",
    "Mat_BlackVeil2_LLC_Clone_",
    "Mat_BlackVeil3_LLC_Clone_",
    "Mat_BlackVeil4_LLC_Clone_",
    "Mat_WhiteVeil_LLC_Clone_",
    "Hair_LLC_Clone_",
    "_3_Peach_Glow_Bob_LLC_Clone_",
    "_3_Peach_Glow_Twin_LLC_Clone_",
    "Diamond_LLC_Clone_",
    "pearl_LLC_Clone_",
]

# 実機検証（Blender上で単体ハイライトレンダリング、材質ノード比較）で確認済み:
# 以下5メッシュは壊れたテクスチャ参照ではなく、正しく実ファイル
# （cloth1.png / Cloth.png、いずれもTex_Black.pngとは無関係な別の白/グレー系
# カジュアル私服テクスチャ）を参照して正常に読み込まれている「本物の」
# もう一つのデフォルト衣装（カーディガン+スニーカー、ブラウス+スカート風）。
# 参考画像の黒ゴシック「黒猫」衣装とは別物のため、VRM出力から除外する。
DEFAULT_OUTFIT_MESH_NAMES_TO_HIDE = [
    "Outer",
    "Boots",
    "Cloth",
    "cover_arm",
    "Over_knee_socks",
]

# ユーザーの実見確認（desktop-vrm-mascotでの使用時）で発覚した衣装混在の修正:
# リファレンス画像（黒猫悪夢衣装: 猫耳＋肉球グローブ＋黒レースドレス＋黒レース
# ソックス、羽なし）と照合し、メッシュ棚卸し＋単体レンダリング確認で
# 「リファレンスに存在しない混入パーツ」と判定したメッシュ。
# 腰の羽状パーツはユーザー確認済みで「本来存在しないパーツ」。
MIXED_IN_MESH_NAMES_TO_HIDE = [
    "Bag",  # 「腰の羽」の正体: コウモリ羽付きリュック（単体レンダリングで形状確認済み）。
            # 材質が隠蔽済みデフォルト私服と同族（cloth1/metal/Diamond/pearl）
    "cloth_Accessories",  # 隠蔽済み私服「Cloth」の付属アクセサリー一式
                          # （頭部のミニコウモリ羽クリップ・耳飾り・腰ストリップ）
    "pet",  # スケール0で全次元dims=0の死にジオメトリ（3146ポリゴンが1点に潰れた状態）。
            # 現状は見えないが、無駄ポリゴン排除と将来の出現防止のため非表示にする
]

# 実機検証（three-vrm）で発覚した「ピンクの開いた口」オーバーレイの修正:
# Bodyメッシュ内の歯（上下）・舌の3アイランドは、幾何学的には唇の奥約9mmに
# あるが、body_LLC_Clone_マテリアルがalphaMode=BLEND+doubleSidedでエクスポート
# されるため、three.js側でdepthWrite=falseの透過描画になり、プリミティブ内の
# 描画順（歯→舌が顔スキンより後）で手前に上書き合成されて見える。
# Unity/VRChat側ではFXレイヤーが収納シェイプキー（下記3キー）を常時1に保って
# 口内ポケットへ収納していたが、FBXにはキー値0で入ってくるため常時展開状態
# だった。収納キーvalue=1のまま保存する方式はエクスポータのウェイト出力と
# ビューア側のリセット挙動に依存して脆弱なため、該当頂点を物理削除する。
# 各キーのデルタは該当アイランドの頂点だけを排他的に動かす（他の頂点への
# 影響ゼロ、実機検証で確認済み）ため、デルタ非0の頂点集合＝削除対象になる。
MOUTH_STORAGE_SHAPE_KEYS = ["t_upper_off", "t_lower_off", "tang_off"]
MOUTH_PART_MESH_NAME = "Body"
EXPECTED_MOUTH_PART_VERTEX_COUNT = 1568  # 上歯569+下歯569+舌430（調査で実測）

# 実機検証（three-vrm）で発覚した「ピンクの開いた口」第2の原因の修正:
# Task 2bで歯・舌アイランドは削除したが、口腔壁（口内ポケットの壁）は顔スキンと
# 同一連結成分のため削除できない。body_LLC_Clone_材質はblend_method=HASHEDで
# VRMエクスポート時にalphaMode=BLEND+doubleSidedになり、three.jsはBLENDを
# transparent=true, depthWrite=falseで描画するため、同一プリミティブ内の描画順で
# 口腔壁（ピンクテクスチャ）が顔スキンの上に上書き合成されて見える。
# three.js上でdepthWrite=trueにするだけで完全に正常表示になることを確認済み
# （検証画像: vrm_r2_test_depthwrite.png）だが、glTF/VRM標準にBLEND+depthWriteの
# 組み合わせは存在しないため、alphaMode=MASK（カットアウト透過は維持・
# 深度書き込みあり）でエクスポートさせる。実現手段はblend_methodではなく
# ノードツリー書き換え（詳細はfix_face_material_blend_method()のdocstring参照）。
FACE_MATERIAL_NAME = "body_LLC_Clone_"

# 実機検証（three-vrm、ユーザーのスクリーンショットによる目視確認）で判明:
# 元のVRChatアバターにはHumanoidボディ本体とは無関係な「小道具/UIギズモ」の
# メッシュオブジェクトが多数含まれており、これらがVRMエクスポート後は
# 常時表示のジオメトリとしてそのまま出力されてしまう（元のVRChat/Unity側では
# Animatorのレイヤー切り替えやエディタ専用表示で通常は隠れているか、
# ユーザーが手動でオンにするギミックだった）。
# 全77メッシュオブジェクトをBlender上で頂点数・ワールド座標バウンディングボックス・
# 親オブジェクト・Armatureモディファイア有無で監査し、実際にオブジェクトを
# 単体でハイライトレンダリングして視覚確認した上で、以下を「本体と無関係な
# 小道具/UIメッシュ」と判定した（本体・衣装・髪・アクセサリー等の
# Humanoidメッシュは一切含まない。判定基準: 親がArmature直下の
# オブジェクトペアレントではなくボーン親のみ、かつArmatureモディファイアを
# 持たない＝スキニングされていない）。
PROP_MESH_NAMES_TO_HIDE = [
    # --- お絵描きタブレット風UIギミック（顔の正面付近に配置された平面パネル群） ---
    "Background",  # 顔の正面を覆う大きな平面クアッド（実機検証で顔を覆っていた元凶）
    "ColorBar",
    "Palette",
    "PaletteIcon",
    "Pen",
    "Pen_Eraser_L",
    "Pen_Eraser_R",
    "Eraser_1",
    "Close",
    # --- モニター/ネオンパネル風UI（顔正面に別途重なる大型パネル、単体レンダリングで確認済み） ---
    "Cl_Monitor",
    "Map_Monitor",
    "_1_1",
    "_2_1",
    "_3",
    "noise_panel_1",
    # --- アバター調整用デバッグ/技術的ギズモ（本体形状ではない平面メッシュ） ---
    "AvatarHight",  # 頭上z=1.51に浮く身長確認用マーカー（4頂点の平面）
    "AntiCulling",  # VRChat側のカリング対策トリックメッシュ、VRM上では無意味な残骸ジオメトリ
    # --- スマホ/カメラ小道具 ---
    "Photo_camera",
    "phone_1",
    "phone_3",
    "phone_001",
    "phone_001_1",
    "phone_002",
    "phone_002_1",
    "phone_003",
    "reset",  # phone_2配下のリセットボタンUI
    # --- 食べ物/飲み物の小道具 ---
    "doughnut1",
    "doughnut2",
    "doughnut3",
    "doughnut4",
    "can_drink",
    "can_drink1",
    "can_drink2",
    "can_drink3",
    "can_drink4",
    "candy_2",
    # --- ジェスチャー検出用Contact Receiverギズモの球体（肩の高さで左右に浮く） ---
    "Sphere_6",
    "Sphere_7",
    "Sphere_8",
    "Sphere_9",
    "Sphere_10",
    "Sphere_11",
    "Sphere_12",
    "Sphere_13",
    "Sphere_14",
    "Sphere_15",
]


def get_args():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit(
            "Usage: blender --background --python prepare_ririka_kaihen_blend.py "
            "-- <source_fbx> <output_blend>"
        )
    return argv[argv.index("--") + 1:]


def parse_args(args):
    if len(args) != 2:
        raise SystemExit("Expected 2 positional args: <source_fbx> <output_blend>")
    return args[0], args[1]


def add_hips_bone(armature_object):
    bpy.context.view_layer.objects.active = armature_object
    armature_object.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = armature_object.data.edit_bones

    if "Hips" in edit_bones:
        raise RuntimeError("すでに'Hips'という名前のボーンが存在します。想定外の状態です")

    hips_bone = edit_bones.new("Hips")
    hips_bone.head = (0.0, 0.0, 0.0)
    hips_bone.tail = (0.0, 3.0, 0.0)
    hips_bone.roll = 0.0

    missing = []
    for name in HUMANOID_CHAIN_ROOTS:
        b = edit_bones.get(name)
        if b is None:
            missing.append(name)
            continue
        b.parent = hips_bone
        b.use_connect = False

    bpy.ops.object.mode_set(mode='OBJECT')

    if missing:
        raise RuntimeError(f"以下のボーンが見つかりません: {missing}")


def apply_armature_transform(armature_object):
    """Armatureオブジェクト自身のワールド変換（location/rotation/scale）を
    単位行列へ適用し、オフセットをボーンのレスト位置に焼き込む。
    メッシュはArmatureオブジェクトにオブジェクトペアレントされているが、
    Blenderのtransform_applyは子のmatrix_parent_inverseを自動調整するため
    メッシュのワールド座標・Hipsボーンのワールド座標は変化しない。
    """
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = armature_object
    armature_object.select_set(True)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    loc, rot, scale = armature_object.matrix_world.decompose()
    if loc.length > 1e-4:
        raise RuntimeError(
            f"Armatureオブジェクトのワールド平行移動が単位行列化されていません: {loc}"
        )


def unparent_skinned_meshes(armature_object):
    """Armatureオブジェクトにオブジェクトペアレントされている（かつ
    Armatureモディファイアで実際にスキニングされている）メッシュの
    オブジェクトペアレントを、ワールド座標を保ったまま解除する。
    VRMエクスポート時にメッシュノードがルートボーン("Hips")ノードの子として
    誤ってネストされ、bindMatrix（スキニング側の想定）とmatrixWorld
    （ノード階層継承）が食い違う二重変形バグを防ぐための処理。
    Armatureモディファイアはオブジェクト参照のみで機能するため、
    親子関係を外してもスキニングそのものは維持される。
    """
    targets = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.parent is not armature_object:
            continue
        if any(m.type == 'ARMATURE' and m.object == armature_object for m in obj.modifiers):
            targets.append(obj)

    if not targets:
        raise RuntimeError(
            "Armatureにオブジェクトペアレントされたスキンメッシュが見つかりません。想定外の状態です"
        )

    bpy.ops.object.select_all(action='DESELECT')
    for obj in targets:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    still_parented = [obj.name for obj in targets if obj.parent is not None]
    if still_parented:
        raise RuntimeError(f"ペアレント解除に失敗したメッシュがあります: {still_parented}")

    # parent_clear(KEEP_TRANSFORM)は、外れた親（Armature）が持っていた
    # ワールド変換（このFBXでは回転90°+スケール0.01。親の0.01スケール[Empty]と
    # Armatureオブジェクト自身の回転を合成したもの）を、ワールド座標を
    # 保つためにメッシュ自身のオブジェクト変換（location/rotation/scale）に
    # そのまま転記する。
    #
    # ここで単純にこの変形を単位行列へtransform_applyするだけでは不十分だった
    # （実機検証で確認済み: 実際に試したがエクスポート結果は一切変化しなかった。
    # transform_applyはワールド座標を保存する操作である以上、当然の結果）。
    #
    # 真因はVRM Add-on（io_scene_gltf2ベース）のエクスポータが、Armatureに
    # オブジェクトペアレントされたボーン階層（Hipsボーン等）には固有の変換経路を
    # 使う一方、Armatureの子から外れた単体メッシュオブジェクトには標準の
    # 「Blender Z-up → glTF Y-up」座標軸変換（(x,y,z)→(x,z,-y)相当）を別途
    # 適用すること。このFBXはボーン側が既にY軸を上方向として一貫している
    # （実機検証: 正しいボーン階層はこの変換を受けずにそのまま出力される）ため、
    # ペアレントを外した単体メッシュに標準変換が適用されると軸が入れ替わり、
    # 頭部メッシュ等が本来の高さ(y≈1.03〜1.19)ではなくz≈-1.0〜-1.23という
    # 無関係な位置に描画されることを実機検証（three-vrm、Tailメッシュの座標を
    # 使い軸入れ替え式(x,y,z)→(x,z,-y)と厳密に一致することを確認）で特定した。
    #
    # 対策として、エクスポータが適用するこの変換を打ち消す補正回転
    # （X軸まわり+90°、上記変換の逆行列）を各メッシュのワールド変形に
    # あらかじめ合成してから単位行列へtransform_applyし、頂点データへ
    # 焼き込む。これによりBlender内の見た目上の整合性（メッシュの向き）は
    # 崩れるが、この.blendはインタラクティブ編集用ではなくVRMエクスポート
    # 専用の作業ファイルであるため許容する。エクスポート後の結果が正しい
    # ワールド座標（ボーン階層と一致する座標系）になることを実機検証で確認済み。
    axis_conversion_compensation = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
    for obj in targets:
        obj.matrix_world = axis_conversion_compensation @ obj.matrix_world

    bpy.ops.object.select_all(action='DESELECT')
    for obj in targets:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    not_identity = []
    for obj in targets:
        loc, rot, scale = obj.matrix_world.decompose()
        if loc.length > 1e-4 or abs(rot.angle) > 1e-4 or (scale - scale.__class__((1, 1, 1))).length > 1e-4:
            not_identity.append(obj.name)
    if not_identity:
        raise RuntimeError(f"メッシュの変形が単位行列化されていません: {not_identity}")

    return targets


def _hide_meshes(names, label):
    """指定名のメッシュのhide_render・hide_viewportを両方Trueにする。

    VRM Add-onのエクスポート対象オブジェクト選定ロジック
    （editor/search.py の export_objects()）は、export_invisiblesが
    Falseの場合（本パイプラインのデフォルト、export_vrm_ririka_kaihen.pyでも
    未指定のためFalseのまま）、Object.visible_get()がFalseのオブジェクトを
    除外する。visible_get()はhide_viewportの状態（および所属コレクションの
    hide_viewport）に依存するため、実際にエクスポートから除外するために
    必須なのはhide_viewport=Trueである。hide_renderはこのフィルタには
    使われないが、「レンダリング/エクスポートに含めない」という意図を
    Blender上のUIでも一貫して示すため、あわせてTrueにしておく。
    """
    missing = []
    hidden = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH':
            missing.append(name)
            continue
        obj.hide_render = True
        obj.hide_viewport = True
        hidden.append(name)

    if missing:
        raise RuntimeError(f"以下の{label}メッシュが見つかりません: {missing}")

    return hidden


def hide_prop_meshes():
    """PROP_MESH_NAMES_TO_HIDEに列挙した「本体と無関係な小道具/UIメッシュ」を非表示化する。"""
    return _hide_meshes(PROP_MESH_NAMES_TO_HIDE, "小道具/UI")


def hide_default_outfit_meshes():
    """DEFAULT_OUTFIT_MESH_NAMES_TO_HIDEに列挙した「本物の別デフォルト私服」を非表示化する。"""
    return _hide_meshes(DEFAULT_OUTFIT_MESH_NAMES_TO_HIDE, "デフォルト私服")


def hide_mixed_in_meshes():
    """MIXED_IN_MESH_NAMES_TO_HIDEに列挙した「リファレンスに存在しない混入パーツ」を非表示化する。"""
    return _hide_meshes(MIXED_IN_MESH_NAMES_TO_HIDE, "混入パーツ")


def delete_mouth_storage_parts():
    """MOUTH_STORAGE_SHAPE_KEYSのデルタが非0の頂点（歯・舌のアイランド）を
    Bodyメッシュから物理削除する。"""
    obj = bpy.data.objects.get(MOUTH_PART_MESH_NAME)
    if obj is None or obj.type != 'MESH':
        raise RuntimeError(f"メッシュオブジェクト'{MOUTH_PART_MESH_NAME}'が見つかりません")
    me = obj.data
    if me.shape_keys is None:
        raise RuntimeError(f"'{MOUTH_PART_MESH_NAME}'にシェイプキーがありません")

    key_blocks = me.shape_keys.key_blocks
    basis = key_blocks.get('Basis')
    if basis is None:
        raise RuntimeError("Basisシェイプキーが見つかりません")

    target_indices = set()
    for key_name in MOUTH_STORAGE_SHAPE_KEYS:
        kb = key_blocks.get(key_name)
        if kb is None:
            raise RuntimeError(f"収納シェイプキー'{key_name}'が見つかりません")
        for i in range(len(kb.data)):
            if (kb.data[i].co - basis.data[i].co).length > 1e-6:
                target_indices.add(i)

    if len(target_indices) != EXPECTED_MOUTH_PART_VERTEX_COUNT:
        raise RuntimeError(
            f"削除対象頂点数が想定と異なります: {len(target_indices)} != "
            f"{EXPECTED_MOUTH_PART_VERTEX_COUNT}（FBXの構造が変わった可能性。要再調査）"
        )

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    doomed = [bm.verts[i] for i in sorted(target_indices)]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(me)
    bm.free()

    print(f"MOUTH_STORAGE_PARTS_DELETED: {len(target_indices)} vertices")
    return len(target_indices)


def fix_face_material_blend_method():
    """FACE_MATERIAL_NAMEの材質をalphaMode=MASK（カットアウト透過）で
    エクスポートさせる（口腔壁の描画順問題の根治）。

    当初は`mat.blend_method = 'CLIP'`で実現する計画だったが、実機調査
    （Blender 4.5で代入→読み返しがHASHED -> HASHEDのまま変化せず）と
    エクスポータのソース調査で以下が判明したため、ノードツリー書き換えに変更した:

    - Blender 4.2以降、Material.blend_methodはEEVEE Next移行に伴うレガシー
      互換プロパティで、実体はsurface_render_method（'DITHERED'/'BLENDED'）。
      'CLIP'を代入してもDITHEREDへ丸められ、読み返すと'HASHED'になる。
    - Blender 5.1のio_scene_gltf2はalphaModeの判定にblend_methodを一切
      使わず、Principled BSDFのAlphaソケットに至るノード構成だけで判定する
      （io_scene_gltf2/blender/exp/material/search_node_tree.py の
      gather_alpha_info() / detect_alpha_clip()）:
        * Alphaが定数1.0 → OPAQUE
        * Alpha入力の直前が Math(Round) → MASK（cutoff=0.5固定）
        * Math(1 - (X < cutoff)) / legacy Math(X > cutoff) → MASK（cutoff可変）
        * それ以外（テクスチャ直結等） → BLEND
    - VRM Add-on（vrm1_exporter.save_vrm_materials）が材質dictを独自生成する
      のはMToon1/MMD/レガシーアドオン材質のみで、素のPrincipled BSDF材質は
      io_scene_gltf2の出力をそのまま使う（body_LLC_Clone_はこれに該当）。
      つまりblend_method経由の制御は不可能で、ノード書き換えが唯一の手段。

    そこで、AlphaソケットのリンクにMath(Round)ノードを割り込ませて
    alphaMode=MASK（alphaCutoff=0.5）としてエクスポートさせる。
    """
    mat = bpy.data.materials.get(FACE_MATERIAL_NAME)
    if mat is None or mat.node_tree is None:
        raise RuntimeError(f"材質'{FACE_MATERIAL_NAME}'が見つかりません")

    bsdf = None
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            bsdf = node
            break
    if bsdf is None:
        raise RuntimeError(f"材質'{FACE_MATERIAL_NAME}'にPrincipled BSDFが見つかりません")

    alpha_socket = bsdf.inputs.get('Alpha')
    if alpha_socket is None or not alpha_socket.is_linked:
        raise RuntimeError(
            f"材質'{FACE_MATERIAL_NAME}'のAlphaソケットがテクスチャに"
            "リンクされていません（想定と異なる構成。要再調査）"
        )

    link = alpha_socket.links[0]
    src_socket = link.from_socket
    round_node = mat.node_tree.nodes.new('ShaderNodeMath')
    round_node.operation = 'ROUND'
    round_node.label = "Alpha Clip (alphaMode=MASK)"
    round_node.location = (bsdf.location.x - 200.0, bsdf.location.y - 400.0)
    mat.node_tree.links.remove(link)
    mat.node_tree.links.new(src_socket, round_node.inputs[0])
    mat.node_tree.links.new(round_node.outputs[0], alpha_socket)

    # エクスポータは参照しないが、Blenderビューポート上の見た目・意図表示を
    # エクスポート結果（カットアウト透過）と揃えておく
    mat.surface_render_method = 'DITHERED'
    mat.alpha_threshold = 0.5

    print(
        "FACE_MATERIAL_BLEND_METHOD: "
        f"BLEND(alphaテクスチャ直結) -> MASK(cutoff=0.5, {src_socket.node.name}."
        f"{src_socket.name} -> Math(Round) -> Alpha)"
    )


def _is_export_visible(obj):
    """hide_prop_meshes()/hide_default_outfit_meshes()/hide_mixed_in_meshes()
    適用後の状態で、このオブジェクトがVRMエクスポート対象に含まれるか（=hide_viewportが
    Falseか）を返す。壊れたテクスチャ参照が非表示メッシュにしか
    影響していない場合は実害がないため、relink_broken_textures()の
    未知パターン検出時にこの情報で警告と致命的エラーを切り分ける。
    """
    return not obj.hide_viewport


def relink_broken_textures():
    """全マテリアルのTEX_IMAGEノードを走査し、image.size==(0, 0)
    （＝Blenderがデコードできず読み込みに失敗した）かつファイルパスが
    ZZZ_GeneratedAssets配下の"*_llc_*.asset"（Unity内部ランタイム専用
    テクスチャのラッパー）に一致するものを検出し、以下のルールで修復する。

    - ファイル名が"Tex_Black_llc_"で始まる場合:
      実体である黒テクスチャの実ファイル（REAL_TEX_BLACK_PATH）を読み込み、
      ノードのimageをそれに差し替える。
    - ファイル名が"UnityWhite_llc_"で始まる場合:
      画像を差し替える対応する実ファイルがUnityプロジェクト内に存在しない
      （lilycalinventoryの「テクスチャなし・フラット白」内部規約と判断）。
      そのため、TEX_IMAGEノードのColor/Alpha出力から接続を切り、接続先
      ソケット（実機調査では全ケースでPrincipled BSDFのBase Color）の
      default_valueに白(1.0, 1.0, 1.0, 1.0)を直接設定する。
    - 上記いずれにも一致しない未知のパターンの場合:
      そのマテリアルを使用するオブジェクトが1つでもエクスポート対象
      （hide_viewport=False）に含まれるならRuntimeErrorで停止し、手動調査を促す。
      非表示の小道具メッシュのみが使用している場合はVRM出力に影響しないため、
      警告を出力するだけで処理を続行する（実機調査で確認済みの実例:
      "resettex_llc_*.asset"は非表示化済みの"reset"小道具メッシュのみが使用）。

    呼び出し前提: hide_prop_meshes()・hide_default_outfit_meshes()・
    hide_mixed_in_meshes()を先に実行し、各メッシュのhide_viewportを
    確定させておくこと。
    """
    real_tex_black_image = None

    relinked_to_black = []
    whited_out = []
    ignored_hidden_only = []

    for mat in bpy.data.materials:
        if mat.node_tree is None:
            continue
        for node in list(mat.node_tree.nodes):
            if node.type != 'TEX_IMAGE' or node.image is None:
                continue
            image = node.image
            if tuple(image.size) != (0, 0) or image.source == 'VIEWER':
                continue  # 正常に読み込めている（またはRender Result等の特殊画像）

            filepath = image.filepath
            basename = os.path.basename(filepath) if filepath else ""

            if ZZZ_GENERATED_ASSETS_MARKER not in filepath or "_llc_" not in basename or not basename.endswith(".asset"):
                # 対象パターン（ZZZ_GeneratedAssets配下の*_llc_*.asset）に
                # 一致しない壊れた画像。実機調査で確認済み: これらは
                # phone tex.renderTexture・Map_Texture.renderTexture等、
                # いずれも小道具/UIギズモ専用の別種の壊れた参照であり、
                # 本タスクのスコープ外（hide_prop_meshes()で既に非表示化される
                # メッシュのみが使用）。
                continue

            # このノードを使っているオブジェクトを特定し、非表示専用かどうか判定
            using_objects = [
                obj for obj in bpy.data.objects
                if obj.type == 'MESH' and any(slot.material is mat for slot in obj.material_slots)
            ]

            if basename.startswith(TEX_BLACK_PREFIX):
                if real_tex_black_image is None:
                    real_tex_black_image = bpy.data.images.load(REAL_TEX_BLACK_PATH, check_existing=True)
                    if tuple(real_tex_black_image.size) == (0, 0):
                        raise RuntimeError(
                            f"黒テクスチャの実ファイルが読み込めませんでした: {REAL_TEX_BLACK_PATH}"
                        )
                node.image = real_tex_black_image
                relinked_to_black.append((mat.name, node.name, basename))

            elif basename.startswith(UNITY_WHITE_PREFIX):
                for out_name in ('Color', 'Alpha'):
                    out_socket = node.outputs.get(out_name)
                    if out_socket is None:
                        continue
                    fill_value = (1.0, 1.0, 1.0, 1.0) if out_name == 'Color' else 1.0
                    for link in list(out_socket.links):
                        to_socket = link.to_socket
                        mat.node_tree.links.remove(link)
                        try:
                            to_socket.default_value = fill_value
                        except TypeError:
                            # スカラーソケットにColorの4要素を代入しようとした場合等の
                            # 型不一致に備えたフォールバック（実機調査では未発生）。
                            to_socket.default_value = fill_value[0] if out_name == 'Color' else fill_value
                whited_out.append((mat.name, node.name, basename))

            else:
                still_visible = [obj.name for obj in using_objects if _is_export_visible(obj)]
                if still_visible:
                    raise RuntimeError(
                        f"未知パターンの壊れたテクスチャ参照がエクスポート対象メッシュに"
                        f"影響しています。手動調査が必要です: material={mat.name} "
                        f"node={node.name} file={basename} affected_objects={still_visible}"
                    )
                ignored_hidden_only.append((mat.name, node.name, basename,
                                             [obj.name for obj in using_objects]))

    print(f"RELINKED_TO_BLACK: {len(relinked_to_black)}")
    for mat_name, node_name, basename in relinked_to_black:
        print(f"  {mat_name} / {node_name} <- {basename}")

    print(f"WHITED_OUT: {len(whited_out)}")
    for mat_name, node_name, basename in whited_out:
        print(f"  {mat_name} / {node_name} <- {basename}")

    print(f"IGNORED_UNKNOWN_PATTERN_HIDDEN_ONLY: {len(ignored_hidden_only)}")
    for mat_name, node_name, basename, objs in ignored_hidden_only:
        print(f"  {mat_name} / {node_name} <- {basename} (objects: {objs}, all hidden)")

    return relinked_to_black, whited_out, ignored_hidden_only


def fix_phantom_emission():
    """PHANTOM_EMISSION_MATERIAL_NAMESに列挙したマテリアルについて、
    Principled BSDFの"Emission Strength"入力がテクスチャ等に接続されておらず
    （定数値）、かつ0より大きい場合にのみ0.0へリセットする。

    実機検証（Base ColorをEmissionへ一時的に直結したunlitレンダーとの比較、
    Emission Strengthを0にしただけの単体レンダリング比較）で、この処理だけで
    黒地に白トリムという参考画像どおりの配色に戻ることを確認済み。Emission
    Colorそのものは変更しない（Strength=0であれば寄与はゼロになるため十分で、
    元データを不必要に破壊しないため）。

    呼び出し前提: relink_broken_textures()実行後（本関数はEmission関連の
    ソケットのみを扱うため実際には呼び出し順に依存しないが、一貫性のため
    このタイミングで呼ぶ）。
    """
    missing = []
    fixed = []
    already_zero = []
    unexpected_linked = []

    for mat_name in PHANTOM_EMISSION_MATERIAL_NAMES:
        mat = bpy.data.materials.get(mat_name)
        if mat is None or mat.node_tree is None:
            missing.append(mat_name)
            continue

        bsdf = None
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        if bsdf is None:
            missing.append(mat_name)
            continue

        strength_socket = bsdf.inputs.get('Emission Strength')
        if strength_socket is None:
            missing.append(mat_name)
            continue

        if strength_socket.is_linked:
            # テクスチャ駆動のEmissionは想定外パターン（幽霊発光の定数値ケースとは
            # 別物の可能性が高い）。誤って正当なEmissionを壊さないよう手動調査を促す。
            unexpected_linked.append(mat_name)
            continue

        if strength_socket.default_value > 0.0:
            strength_socket.default_value = 0.0
            fixed.append(mat_name)
        else:
            already_zero.append(mat_name)

    if missing:
        raise RuntimeError(f"以下のマテリアル/Principled BSDF/Emission Strengthソケットが見つかりません: {missing}")
    if unexpected_linked:
        raise RuntimeError(
            f"以下のマテリアルはEmission Strengthがテクスチャに接続されており、"
            f"想定していた定数の幽霊発光パターンと異なります。手動調査が必要です: {unexpected_linked}"
        )

    print(f"PHANTOM_EMISSION_FIXED: {len(fixed)}")
    for name in fixed:
        print(f"  {name}")
    if already_zero:
        print(f"PHANTOM_EMISSION_ALREADY_ZERO: {len(already_zero)}")
        for name in already_zero:
            print(f"  {name}")

    return fixed


if __name__ == "__main__":
    source_fbx, output_blend = parse_args(get_args())

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=source_fbx)

    armature_object = bpy.data.objects.get(ARMATURE_NAME)
    if armature_object is None or armature_object.type != 'ARMATURE':
        raise RuntimeError(f"Armatureオブジェクト'{ARMATURE_NAME}'が見つかりません")

    add_hips_bone(armature_object)
    print("HIPS_BONE_ADDED")

    apply_armature_transform(armature_object)
    print("ARMATURE_TRANSFORM_APPLIED")

    unparented = unparent_skinned_meshes(armature_object)
    print(f"UNPARENTED_SKINNED_MESHES: {len(unparented)}")

    hidden_props = hide_prop_meshes()
    print(f"HIDDEN_PROP_MESHES: {len(hidden_props)}")

    hidden_default_outfit = hide_default_outfit_meshes()
    print(f"HIDDEN_DEFAULT_OUTFIT_MESHES: {len(hidden_default_outfit)}")

    hidden_mixed_in = hide_mixed_in_meshes()
    print(f"HIDDEN_MIXED_IN_MESHES: {len(hidden_mixed_in)}")

    delete_mouth_storage_parts()

    fix_face_material_blend_method()

    relink_broken_textures()

    fix_phantom_emission()

    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    print(f"SAVED: {output_blend}")
