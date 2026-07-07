# AR改変アバター表示デモ 設計書

- 日付: 2026-07-07
- ステータス: 承認済み（brainstormingフェーズ完了）

## 背景・目的

VRChat用に改変した自分のアバターを、スマホ(iPhone)のARで表示し、決まったモーション（idle/ダンス等）をループ再生するデモを作る。将来的にはBOOTHでの販売（他のVRChatユーザーが自分のアバターを使って同じ仕組みを利用できるテンプレート/キットとしての販売）を視野に入れるが、現段階ではコストをかけずに自分用のデモを完成させることを最優先とする。

## 前提・制約

- 開発環境はWindows。Mac/Xcodeは一切使用しない
- 対象は iPhone（Safari）のみ
- 動かすモーションは決まったクリップの再生のみ。リアルタイムのボディトラッキングは行わない
- アバターの実体データ（FBX/prefab）はVRChatアップロード用Unityプロジェクト内に存在する
- アニメーションクリップは未用意。Mixamoの無料モーションをHumanoidボーンにリターゲットして使用する
- 将来のBOOTH販売を見据え、サーバー費用・保守コストが発生しない構成にする

## 採用アーキテクチャ（WebAR方式）

Unity + AR Foundationのネイティブアプリ化は、Macなし環境ではXcodeビルドがブロッカーになるため採用しない。代わりに、静的ファイルのみで完結するWebAR方式を採用する。

```
[Blender(Windows)] --GLB/USDZ変換--> [静的ファイル一式] --GitHub Pages(無料)--> [iPhone Safari / AR Quick Look]
  ↑ FBX(VRChatアバター) + Mixamoモーション(リターゲット)
```

- **モデル変換**: Blender（Windows・無料）でFBXを読み込み、Mixamoの無料モーションをリターゲットして合成。そこから `model.glb`（通常3Dビュー用）と `model.usdz`（iOS AR Quick Look用）を書き出す
- **表示ページ**: Googleの `<model-viewer>` Webコンポーネントを使った1枚の `index.html`。GLBを通常表示に、`ios-src` にUSDZを指定してiOS Safariの「ARで見る」ボタンからApple標準のAR Quick Lookを起動する
- **ホスティング**: GitHub Pages（無料）

## ファイル構成

```
ar-avatar-demo/
├── index.html          # model-viewerを埋め込む1枚ページ（改変不要）
├── model.glb            # 通常3Dプレビュー用
├── model.usdz           # iOS AR Quick Look用
└── README.md            # 自分のFBXを差し替える手順書
```

BOOTH販売時は、`model.glb`/`model.usdz` を抜いた「テンプレート＋README＋Blender変換ガイド」をパッケージ化し、購入者が自分のアバターで同じ手順を踏めばそのまま使える形にする。これにより販売側にサーバー費用や保守コストは発生しない。

## パイプライン（変換手順）

1. VRChatアップロード用UnityプロジェクトからFBXをエクスポート（または既存FBXを使用）
2. Blenderへインポート
3. Mixamoから無料モーション（idle/ダンス等）をダウンロードし、Humanoidボーンにリターゲット
4. Blender標準機能で glTF(.glb) と USD(.usdz) の両方をエクスポート
5. `index.html` 内のファイル名を実際のファイル名に合わせる

## 動作確認方法

WindowsからはAR Quick Lookを直接プレビューできないため、実機確認が必須。

1. GitHub Pagesに一式をpush → 公開URL発行
2. iPhoneのSafariでURLを開く
3. モデルをタップ →「ARで見る」をタップ
4. AR Quick Look起動、平面検出→配置→アニメーションループ再生を確認
5. 問題があればBlenderのエクスポート設定を見直す

## 既知の制限（今回のスコープでは許容）

- AR Quick Lookはアプリではないため、複数アニメーション切り替えUIなどの作り込みはできない（1クリップのループ再生が中心）
- オクルージョンや永続的な空間アンカーはネイティブアプリほど高精度ではない
- これらは「デモとしては十分」「将来ネイティブアプリ化する際に強化する部分」として割り切る

## スコープ外（今回やらないこと）

- ネイティブiOSアプリ化（Unity + AR Foundation + Xcodeビルド）
- リアルタイムボディトラッキング・VRChat OSC連携
- BOOTH販売パッケージそのものの作成・課金導線
- サーバーサイド機能（アップロード、変換の自動化など）
