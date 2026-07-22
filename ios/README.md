# リリカ iOSマスコット（実機スパイク）

SwiftUIの`WKWebView`内で`three.js` / `three-vrm`を動かし、リポジトリ直下の
`model.vrm`と`animations/idle.vrma`をローカル再生する最小構成です。

## Webアセットの更新

Node.jsとpnpmが利用できる環境で実行します。

```bash
cd ios
pnpm install --frozen-lockfile
pnpm test
pnpm build
```

生成済みの`Web/dist/index.html`と`Web/dist/mascot.js`はXcodeのBundle Resourceです。
アプリ実行時のネットワーク接続はありません。

## Xcode

`RirikaMascot.xcodeproj`を開き、開発チームと接続したiPhoneを選択して実行します。
初回スパイクでは、ロード完了、idle再生、SpringBone、衣装・顔、メモリ、FPS、
バックグラウンド復帰を確認します。
