import SwiftUI
import WebKit

struct MascotWebView: UIViewRepresentable {
    let model: MascotViewModel

    func makeCoordinator() -> Coordinator {
        Coordinator(model: model)
    }

    func makeUIView(context: Context) -> WKWebView {
        let controller = WKUserContentController()
        controller.add(context.coordinator, name: "mascot")

        let configuration = WKWebViewConfiguration()
        configuration.userContentController = controller
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.setURLSchemeHandler(BundleSchemeHandler(), forURLScheme: "mascot")

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.isOpaque = true
        webView.scrollView.isScrollEnabled = false
        context.coordinator.webView = webView
        context.coordinator.loadContent()
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}

    static func dismantleUIView(_ webView: WKWebView, coordinator: Coordinator) {
        webView.configuration.userContentController.removeScriptMessageHandler(forName: "mascot")
        coordinator.stopObservingLifecycle()
    }

    @MainActor
    final class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
        weak var webView: WKWebView?
        private let model: MascotViewModel
        private var observers: [NSObjectProtocol] = []

        init(model: MascotViewModel) {
            self.model = model
            super.init()
            observeLifecycle()
        }

        func loadContent() {
            guard let indexURL = URL(string: "mascot://bundle/index.html") else { return }
            NSLog("MASCOT_NAVIGATION: load-started")
            webView?.load(URLRequest(url: indexURL))
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            NSLog("MASCOT_NAVIGATION: finished")
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            NSLog("MASCOT_NAVIGATION_ERROR: %@", error.localizedDescription)
            model.receive(.error(error.localizedDescription))
        }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard let parsed = MascotMessage(body: message.body) else { return }
            model.receive(parsed)
        }

        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            model.receive(.error("描画プロセスが終了しました"))
        }

        private func observeLifecycle() {
            let center = NotificationCenter.default
            observers.append(center.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: .main) { [weak self] _ in
                self?.webView?.evaluateJavaScript("window.mascotApp?.suspend()")
            })
            observers.append(center.addObserver(forName: UIApplication.willEnterForegroundNotification, object: nil, queue: .main) { [weak self] _ in
                self?.webView?.evaluateJavaScript("window.mascotApp?.resume()")
            })
        }

        func stopObservingLifecycle() {
            let center = NotificationCenter.default
            observers.forEach(center.removeObserver)
            observers.removeAll()
        }
    }
}

private final class BundleSchemeHandler: NSObject, WKURLSchemeHandler {
    private let allowedResources = Set(["index.html", "mascot.js", "model.vrm", "idle.vrma"])

    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        guard
            let requestURL = urlSchemeTask.request.url,
            let resourceName = requestURL.pathComponents.last,
            allowedResources.contains(resourceName),
            let separator = resourceName.lastIndex(of: "."),
            let resourceURL = Bundle.main.url(
                forResource: String(resourceName[..<separator]),
                withExtension: String(resourceName[resourceName.index(after: separator)...])
            )
        else {
            urlSchemeTask.didFailWithError(URLError(.fileDoesNotExist))
            return
        }

        do {
            let attributes = try FileManager.default.attributesOfItem(atPath: resourceURL.path)
            let size = (attributes[.size] as? NSNumber)?.intValue ?? -1
            let response = URLResponse(
                url: requestURL,
                mimeType: mimeType(for: resourceName),
                expectedContentLength: size,
                textEncodingName: resourceName.hasSuffix(".html") || resourceName.hasSuffix(".js") ? "utf-8" : nil
            )
            urlSchemeTask.didReceive(response)

            let handle = try FileHandle(forReadingFrom: resourceURL)
            defer { try? handle.close() }
            while let data = try handle.read(upToCount: 1024 * 1024), !data.isEmpty {
                urlSchemeTask.didReceive(data)
            }
            urlSchemeTask.didFinish()
        } catch {
            urlSchemeTask.didFailWithError(error)
        }
    }

    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) {}

    private func mimeType(for resourceName: String) -> String {
        switch resourceName.split(separator: ".").last {
        case "html": "text/html"
        case "js": "text/javascript"
        case "vrm", "vrma": "model/gltf-binary"
        default: "application/octet-stream"
        }
    }
}
