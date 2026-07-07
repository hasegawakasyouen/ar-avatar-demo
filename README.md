# ARアバターデモ

VRChat改変アバターをiPhoneのAR Quick Lookで表示し、アニメーションをループ再生するWebARデモ。

**ステータス:** iPhone実機での動作確認済み（GitHub Pages上でライブ運用）

---

## 仕組み

このプロジェクトはサーバーレスのWebAR実装です。

```
VRChatアバター(FBX)
    ↓ [Mixamoで自動リギング + アニメーション取得]
    ↓ [Blenderで GLB/USDZ に変換]
    ↓ [Google model-viewerで表示]
    ↓
iPhone Safari → AR Quick Look → 3D空間にアバター配置 → アニメーションループ再生
```

### ファイル構成

```
ar-avatar-demo/
├── index.html                    # model-viewer Web コンポーネント
├── model.glb                     # 通常3D表示用（全ブラウザ対応）
├── model.usdz                    # iOS AR Quick Look用
├── scripts/
│   └── convert_to_web.py         # Blenderヘッドレス変換スクリプト
├── source/
│   └── avatar_idle_mixamo.fbx    # Mixamo経由のアニメーション付きFBX（このファイルを差し替える）
└── README.md                     # このファイル
```

---

## 自分のアバターに差し替える手順

### 前提条件

- Blender 4.5（Windows）: `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`
- Python 3.12（PATH通り）

### Step 1: VRChatアバターのFBXを用意する

VRChatアップロード用Unityプロジェクト内の `Assets/` フォルダから、あなたのアバターモデルのFBXを探します。

> **探し方**
> - Unityでアバター用Prefabを開き、FBXはどこから来ているかプロパティで確認
> - または `Assets/` 内を "avatar" で検索
> - VRChatアバターは通常、インポート元のFBXがプロジェクト内に残っている

もしFBXが見つからない場合は、Unity内でアバターモデルをエクスポートします。

**Unity 2022.3.22以降の場合:**
1. アバターの GameObject を Hierarchy で選択
2. メニュー: `GameObject > Export To FBX`
3. ファイルを保存（例: `C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_raw.fbx`）

> **注意**
> エクスポートされたFBXはVRChatのボーン構造をそのまま含んでいます。これは正常です。Step 2 でそのボーン構造を削除し、メッシュのみの状態にしてからMixamoにアップロードします。

---

### Step 2: Blenderで骨格（Armature）をストリップする

**重要:** VRChatアバターのFBXは既に VRChat用ボーン構造を含んでいます。このままMixamoにアップロードすると、Mixamoの自動リガーが既存骨格の再マッピングに失敗し、エラー `「申し訳ありませんが、既存の骨格をマッピングできませんでした。」` が出て処理を進められません。

**解決策**: 事前にBlenderで骨格を削除し、メッシュだけの状態にしてからMixamoにアップロードします。Mixamoはメッシュのみの状態を自動リギングの入力として想定しており、この方法ならうまくいきます。

**Blender での処理手順:**

1. Blenderを開く
2. `File > Import > FBX (.fbx)` でVRChatアバターFBXをインポート
3. Outlinerで Armature オブジェクトを選択 → 削除（`X` キー → 削除確認）
4. 各メッシュオブジェクトを選択し、Modifiers パネルで Armature Modifier があれば削除（`X` ボタン）
   - これでメッシュが bind pose（初期姿勢）で固定化される
   - 複数メッシュがある場合はすべて処理する
5. `File > Export > FBX (.fbx)` で新しいFBXとして保存（例: `avatar_meshonly.fbx`）
6. このメッシュオンリーFBXをMixamoに送る

> **なぜこれが必要なのか?**
> VRChat用ボーン = humanoid IK + VRChat固有ボーン（指・目・口・etc）を含む複雑な構造
> Mixamoの自動リガー = シンプルな humanoid ボーン構造（上半身・下半身の主要ジョイント）のみを想定
>
> 既存ボーンの構造が「複雑すぎる」か「非標準」なため、Mixamoはマッピング（解釈）できず、エラーで止まります。
> メッシュ単体なら、Mixamoは chin / wrist / elbow / knee マーカーの UI で一から正しくリギングできます。

---

### Step 3: Mixamoでアニメーション付与 & ダウンロード

1. **https://www.mixamo.com にアクセス** → Adobeアカウント（無料）でログイン

2. **「UPLOAD CHARACTER」** → Step 2で作った `avatar_meshonly.fbx` をアップロード

3. **自動リギング画面**
   - Mixamoが顎・手首・肘・膝の位置を自動検出します
   - マーカーが正しい位置にあるか目視チェック（ずれていれば手動調整）
   - 「NEXT」をクリック
   - リギング処理を待つ（通常1〜2分。高ポリゴンメッシュの場合は稀に10分以上かかることがあります。下記参照）

   > **高ポリゴンメッシュでリギングが進まない場合:**
   > Mixamoの自動リガーは ~166k ポリゴンレベルで10分以上ハング することが報告されています。
   > その場合は、事前にBlenderで **メッシュを統合して頂点数を削減** してください。
   >
   > **前提: Shape Keys（ブレンドシェイプ）について**
   > VRChatアバターに顔アニメーションの Shape Keys がある場合、以下の削減手順を実行する **前に** 削除してください。Blenderの Decimate Modifier は Shape Keys がある状態では Apply できないため、先に削除が必要です。このデモでは本体の idle/ダンスアニメーションのみを再生し、顔表情は不要なため、削除しても構いません。
   >
   > **削減手順:**
   > 1. Blenderで meshonly FBX をインポート
   > 2. すべてのメッシュオブジェクトを選択（`Shift` クリック）
   > 3. `Object > Join` → 1つのメッシュに統合
   > 4. 統合したメッシュを選択
   > 5. Add Modifier → Decimate
   > 6. Ratio スライダーで約 25,000 ポリゴン になるよう調整（元の 166k から ~85% 削減）
   > 7. Modifier をApply
   > 8. メッシュをエクスポート
   > 
   > この削減により、Mixamoのリギング時間は数分以内に短縮されます。トレードオフとして、微細な形状（顔の細部、髪の毛の房など）は失われますが、ARビューの距離感ではほぼ気になりません。

4. **アニメーション選択**
   - 左側のアニメーション一覧から「Idle」または好みのダンスアニメーション（Shuffle、Breakdance等）を選択
   - プレビューで正しく再生されるか確認（腕や脚がねじれていないか）

5. **ダウンロード**
   - 「DOWNLOAD」ボタン
   - **Format:** `FBX Binary (.fbx)`
   - **Skin:** `With Skin`
   - **Frames per Second:** `30`
   - **Keyframe Reduction:** `none`
   - ダウンロード完了後、ファイルを `source/avatar_idle_mixamo.fbx` として保存

---

### Step 4: テクスチャのリンク修正（最も時間がかかるステップ）

**重要:** Unityから出力されたFBXのマテリアル内部のテクスチャパスは、元の作成者の絶対パス（例: `Z:\Blender\...\body.psd`）になっています。他のマシンではこのパスは存在しないため、Blenderがテクスチャを見つけられず、結果として **テクスチャが反映されない（灰色のメッシュになる）** ことがあります。

**症状:** 変換後の GLB/USDZ を見ると、せっかくのアバターが真っ灰色で、本来のテクスチャ（肌、髪、服など）が失われている

**解決策:** VRChatアバターの元フォルダ（.blend や source asset が置いてある場所）から実際のテクスチャ PNG ファイルを探し、Blenderで手動で再リンクします。

**テクスチャの探し方:**

1. VRChatアバターの作成に使った Blender project や art asset フォルダを確認
   - 例: `avatar_art_assets/texture/PNG/` 配下に `body.png`, `hair.png` 等の PNG ファイルが置いてあるはず
   - Unityプロジェクト内にも `Assets/Avatar/Textures/` 等があれば確認

2. PNG ファイルが見つかったら、ファイル名でマテリアル名と対応させる
   - 例: マテリアル名「Body_MAT」→ テクスチャファイル「body.png」のように推測

3. 小さなアクセサリー（ネックレス、帽子のリボン等）や金属パーツは、テクスチャなしで単色マテリアルの場合もあります。この場合は該当PNG が存在しない＝正常です。

**Blenderでのリンク修正:**

1. Blenderで `source/avatar_idle_mixamo.fbx` をインポート
2. Shading workspace に切り替え
3. メッシュオブジェクトを選択
4. Shader Editor で、各マテリアルの **Base Color** ノードを確認
5. Base Color に Image Texture ノード がつながっていれば、その **X** ボタンで削除（切断）
6. 新しい Image Texture ノードを追加
   - Shader Editor の **左上にある `Add` メニュー** をクリック → `Texture` → `Image Texture`
7. Image Texture ノードをロード
   - ノード上部の **`Open` ボタン** をクリック → ファイルブラウザで見つけた PNG テクスチャを選択
8. 新しい Image Texture ノードの出力を Base Color の入力につなぐ
   - Image Texture ノードの右側にある **黄色の出力ソケット** をドラッグしながら、Principled BSDF ノードの **Base Color 入力（左側）** にドロップ
9. すべてのマテリアルについて繰り返す

> **Tips: 全マテリアルを一括にするには？**
> マテリアルが多い場合（10個以上）は、Pythonスクリプトで一括修正することも検討してください。ただし、テクスチャの正体が各々のマテリアルで異なるため、「どのテクスチャをどのマテリアルに張るか」の判定は手動での確認が必須です。

**テクスチャのリサイズ（ファイルサイズ最適化）**

VRChatアバターのテクスチャは 4096×4096 が多く、そのまま変換すると GLB/USDZ が 40MB を超えることがあります。これはモバイルARとしては重すぎます。

**解決策:** 各テクスチャを 1024×1024 にリサイズ

**Blenderでの手順:**

1. Shading workspace で Image Texture ノードを選択
2. Properties パネル の Image タブで、Image を選択
3. Image Editor workspace を開く
4. `Image > Scale Image` → 1024 × 1024 に設定 → OK
5. すべてのテクスチャについて繰り返す
6. `Image > Save As` でPNG上書き保存（または `Image > Pack` で Blend ファイル内に埋め込み）

> **リサイズの効果:**
> - 元: 4096×4096 × 6枚テクスチャ → 43MB GLB/45MB USDZ
> - 後: 1024×1024 × 6枚テクスチャ → 6MB GLB/8MB USDZ
> 
> 約85% ファイルサイズ削減で、AR閲覧時のモバイル表示品質にはほぼ影響がありません。

> **透明度が必要なテクスチャについて:**
> 髪の毛の細部が透けるカットアウト表現（Alpha Transparency）が必要なら、1024×1024でも PNG で保持してください。
> 完全に不透明なテクスチャ（肌、服etc）は JPEG に変換してさらに圧縮することも検討できます。

**Step 2〜4の作業結果を保存する（重要）**

ここまでの骨格ストリップ・テクスチャ再リンク・リサイズ作業は、すべてBlender上でのメモリ内編集です。次のStep 5で使うのは `source/avatar_idle_mixamo.fbx` というファイルなので、**Blenderでの作業結果を必ずこのファイルとして上書きエクスポートしてください**（`File > Export > FBX (.fbx)` → `source/avatar_idle_mixamo.fbx` を選んで上書き保存）。これを忘れると、Step 5を実行しても直したはずの状態（正しいテクスチャ・軽量化済み）が反映されず、修正前の壊れた変換結果に戻ってしまいます。

> **再エクスポート後は必ず見た目を目視確認してください:**
> テクスチャ再リンク後にFBXを再エクスポートすると、まれにマテリアルが半透明・ゴーストのような見た目になることがあります（PNGのアルファチャンネルがBase Colorの不透明設定に影響してしまうケース）。Step 6（ブラウザプレビュー）で必ずスクリーンショットを見て、肌や服が透けていないか確認してください。透けている場合は、該当マテリアルの Alpha 入力を `1.0`（完全不透明）に固定するか、Blenderのマテリアル設定で Blend Mode を `Opaque` にしてから再エクスポートしてください。

---

### Step 5: Blenderで GLB/USDZ に変換する

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python scripts\convert_to_web.py -- source\avatar_idle_mixamo.fbx model.glb model.usdz
```

**実行結果:**

```
CONVERT_OK model.glb model.usdz
```

が標準出力に表示されれば成功です。

**ファイルサイズの目安:**
- GLB: 数MB〜15MB（テクスチャ解像度と頂点数に依存）
- USDZ: 数MB〜20MB

---

### Step 6: ブラウザでプレビュー確認

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
python -m http.server 8080
```

ブラウザで `http://localhost:8080` を開き、以下を確認：

- [ ] 3Dモデルが表示されている
- [ ] 肌・服・髪が半透明やゴースト状になっていない（完全に不透明で表示されている。Step 4末尾の注意を参照）
- [ ] アニメーションが自動再生されている（ループしている）
- [ ] ブラウザコンソールにエラーがない

---

### Step 7: GitHub Pages にデプロイ

```bash
cd "C:\Users\PC_User\Documents\ar-avatar-demo"
git add model.glb model.usdz
git commit -m "update: replace avatar with new version"
git push
```

デプロイ後、`https://<your-github-username>.github.io/ar-avatar-demo/` で公開されます。

---

### Step 8: iPhone で確認（実機必須）

iPhoneのSafariで上記URLを開き、以下を確認：

1. 3Dモデルが表示される
2. アニメーションがループ再生される
3. 「ARで見る」ボタンをタップ
4. AR Quick Lookが起動 → 床や机に配置 → アニメーション再生を確認

---

## トラブルシューティング

### Mixamoエラー: 「既存の骨格をマッピングできませんでした」

**原因:** VRChatアバターのFBX（ボーン構造付き）をそのままアップロードした

**解決:** Step 2 を参照。Blenderでボーン構造をあらかじめ削除してください。

---

### Mixamoのリギング画面がハングし、10分以上進まない

**原因:** 高ポリゴンメッシュ（>150k ポリゴン）を送った

**解決:** Step 3 の「高ポリゴンメッシュでリギングが進まない場合」を参照。Blenderで Decimate して 25k 程度に削減してから再アップロード。

---

### 変換後のモデルが真っ灰色で、テクスチャが見えない

**原因:** FBX内のテクスチャパスが絶対パス（別マシン上の存在しないパス）で、Blenderが見つけられなかった

**解決:** Step 4 を参照。実際のPNGテクスチャを探してBlenderで手動リンク。Blenderのシェーダーエディターで Base Color ノードを正しいPNGに差し替えてから変換。

---

### GLB/USDZ のファイルサイズが大きい（>30MB）

**原因:** テクスチャ解像度が 4096×4096 のままになっている

**解決:** Step 4 の「テクスチャのリサイズ」を参照。1024×1024 にリサイズ → ファイルサイズは約 85% 削減される。

---

### 変換スクリプトでエラー: `import_scene.fbx failed`

**原因:** ファイルパスが間違っているか、FBXが破損している

**確認:**
```bash
ls -la "C:\Users\PC_User\Documents\ar-avatar-demo\source\avatar_idle_mixamo.fbx"
```

ファイルが存在すれば、FBX自体を別アプリ（Blender GUI版等）で直接開いて破損確認。

---

### iPhoneでAR Quick Look が起動しない

**原因:** 
- iOS 15 未満（AR Quick Lookが非対応）
- ネットワーク接続がない
- Safari が 古いバージョン

**確認:**
- iOS 15以上であることを確認
- 同じWiFi上で `model.glb` が http.server で serve されているか確認

---

## 既知の制限

- **iOS Safari のみ対応** — Android/デスクトップのブラウザは 3D表示のみ（ARなし）
- **1つのアニメーションのみ** — idle またはダンスの1クリップのループ再生。複数モーション切り替えUIなし
- **顔アニメーション非対応** — Shape Keys（viseme等）は削除済み（Step 3参照）。表情アニメーションは再生されません
- **AR Quick Look の標準機能に依存** — カスタムレイアウト、永続的な空間アンカー等、高度なAR機能は不可

---

## ライセンス・クレジット

- **Blender**: GPL-3.0（無料・オープンソース）
- **Mixamo**: Adobe Inc.（無料アニメーション提供）
- **model-viewer**: Google（Apache 2.0）
- **GitHub Pages**: GitHub Inc.（無料ホスティング）

---

**更新日:** 2026-07-07  
**作成者:** hasegawakasyouen
