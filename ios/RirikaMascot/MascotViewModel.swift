import Foundation

@MainActor
final class MascotViewModel: ObservableObject {
    @Published private(set) var isReady = false
    @Published private(set) var errorMessage: String?

    func receive(_ message: MascotMessage) {
        switch message {
        case .ready:
            NSLog("MASCOT_READY")
            isReady = true
            errorMessage = nil
        case let .error(message):
            NSLog("MASCOT_ERROR: %@", message)
            isReady = false
            errorMessage = message
        case let .diagnostic(message):
            NSLog("MASCOT_DIAGNOSTIC: %@", message)
        }
    }
}

enum MascotMessage: Equatable {
    case ready
    case error(String)
    case diagnostic(String)

    init?(body: Any) {
        guard
            let dictionary = body as? [String: Any],
            let type = dictionary["type"] as? String
        else { return nil }

        switch type {
        case "ready":
            self = .ready
        case "error":
            self = .error(dictionary["message"] as? String ?? "不明なエラー")
        case "diagnostic":
            guard let message = dictionary["message"] as? String else { return nil }
            self = .diagnostic(message)
        default:
            return nil
        }
    }
}
