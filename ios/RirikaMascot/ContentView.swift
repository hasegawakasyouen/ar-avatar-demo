import SwiftUI

struct ContentView: View {
    @StateObject private var model = MascotViewModel()

    var body: some View {
        ZStack {
            MascotWebView(model: model)
                .ignoresSafeArea()

            if let message = model.errorMessage {
                ContentUnavailableView(
                    "読み込みに失敗しました",
                    systemImage: "exclamationmark.triangle",
                    description: Text(message)
                )
                .padding()
                .background(.regularMaterial)
            }
        }
    }
}
