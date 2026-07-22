# Product Charter — リリカ iOSマスコット

## Status

- App ID: `ririka-ios-mascot`
- Product: リリカ iOSマスコット
- Phase: iPhone実機vertical slice／軽量VRM再検証
- Implementation owner: Mac（SwiftUI、WKWebView、実機検証）
- Asset-generation collaborator: Windows（Blender／VRM Add-onによる`model_ios.vrm`生成のみ）
- Source repository: `hasegawakasyouen/ar-avatar-demo`
- Base branch at charter creation: `master`
- Base commit: `583532c5198e2c6da06408c6ff9509ac8df5824f`

## Objective

VRChatアバター「リリカ」のVRM 1.0モデルとVRMAアニメーションを使い、
iPhone上で自律的に動き、タップとドラッグに反応するデスクトップマスコット風
アプリを、外部通信なしで動作させる。

## Primary user and outcome

所有者本人が、自分のiPhone上でリリカを常時眺め、直接触って反応を楽しめる。
既存のthree.js版PWAと同じ基本挙動を、iOSネイティブのアプリ境界で提供する。

## Approved product scope

1. SwiftUIをアプリ／ライフサイクル境界とする。
2. WKWebView内でthree.js、`@pixiv/three-vrm`、`@pixiv/three-vrm-animation`を動かす。
3. VRM／VRMA／Web bundleはアプリへ同梱し、実行時の外部通信を行わない。
4. 最初の合否ゲートは、軽量VRM＋`idle.vrma`の実機表示・再生とする。
5. 合格後、idle／wave／dance／walk／joy／cry／eat、自律徘徊、タップ反応、ドラッグを実装する。
6. バックグラウンドでは描画とアニメーションを停止し、復帰時は安全にidleへ戻す。

## Current architecture and fixed dependencies

- iOS 17以降
- SwiftUI＋WKWebView
- `three@0.180.0`
- `@pixiv/three-vrm@3.5.3`
- `@pixiv/three-vrm-animation@3.5.3`
- Web bundle生成: `esbuild@0.25.6`

依存バージョンは`ios/pnpm-lock.yaml`で固定する。新しいproduction dependencyや
外部サービスは、必要性と影響を説明して別承認を得るまで追加しない。

## Vertical-slice acceptance criteria

- 生成した`model_ios.vrm`がVRM 1.0として読み込める。
- iPhone実機で`model-loaded`、`idle-loaded`、`MASCOT_READY`まで到達する。
- WKWebViewのWebContentプロセスがモデル読込で終了しない。
- idleアニメーションとSpringBoneが継続して動く。
- 顔、黒猫悪夢衣装、髪、透過表現に明白な破綻がない。
- バックグラウンド移行と復帰でクラッシュせず、idleへ復旧する。
- FPS、メモリ、発熱、初回読込時間を実測して記録する。

具体的な性能閾値は軽量版の初回実測後に決める。実測前に推測値を合格条件へ
固定しない。

## Non-goals for the current phase

- App Store公開、TestFlight配布、第三者配布
- 外部サーバー、分析SDK、広告、課金、アカウント、クラウド同期
- VRM原本やVRChat／Unity原本プロジェクトの上書き
- 現行252MB `model.vrm`のiPhone向け直接採用
- 軽量VRM合格前の全挙動実装

## Asset ownership and handoff

- `model.vrm`、`source/ririka_kaihen.blend`、`animations/*.vrma`は入力原本として変更しない。
- Windowsは`docs/ios-vrm-optimization-handoff.md`と
  `scripts/export_vrm_ririka_kaihen_ios.py`を使い、`model_ios.vrm`を別ファイルとして生成する。
- `model_ios.vrm`は100MB未満、目標50〜80MBとするが、Gitへ追加しない。
- Windows側はiOS／Swift／Web実装を変更しない。
- Mac側はBlender原本やVRM生成パイプラインの既存動作を変更しない。

## Failure and recovery

- WebContent終了時はSwift側でエラーを表示し、成功扱いにしない。
- 軽量版で見た目が壊れた場合は原本へ戻さず、別出力として再生成する。
- generation tokenにより、古い非同期完了処理が現在状態を上書きしないようにする。
- commit、push、公開、削除、互換性破壊はそれぞれ承認境界として扱う。

## Allowed paths

```text
.gitignore
docs/product-charter-ririka-ios.md
docs/ios-vrm-optimization-handoff.md
ios/README.md
ios/RirikaMascot.xcodeproj/project.pbxproj
ios/RirikaMascot.xcodeproj/xcshareddata/xcschemes/**
ios/RirikaMascot/**
ios/RirikaMascotTests/**
ios/Web/src/**
ios/Web/tests/**
ios/Web/dist/index.html
ios/Web/dist/mascot.js
ios/package.json
ios/pnpm-lock.yaml
ios/pnpm-workspace.yaml
ios/scripts/**
scripts/export_vrm_ririka_kaihen_ios.py
```

Explicitly excluded:

```text
ios/**/xcuserdata/**
*.xcuserstate
model.vrm
model_ios.vrm
source/ririka_kaihen.blend
animations/**
```

## Verification and release boundary

- Node unit tests、XCTest build／execution、Xcode build、実機ログ、実画面確認を使う。
- 自動テストだけで衣装・顔・アニメーションの視覚的正しさを断定しない。
- 保護用ローカルcommitは復元点であり、公開・push承認を意味しない。
- push、PR、merge、TestFlight、App Store操作は個別の明示承認があるまで行わない。

## Open items

- Windows側に未pushの同時作業が存在するか。
- `model_ios.vrm`の実サイズと実機上のピークメモリ。
- 軽量版の実測に基づく性能合格値。
- 配布へ進む場合のアバター利用許諾と署名／Bundle ID方針。
