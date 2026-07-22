import XCTest
@testable import RirikaMascot

final class MascotMessageTests: XCTestCase {
    func testReadyMessage() {
        XCTAssertEqual(MascotMessage(body: ["type": "ready"]), .ready)
    }

    func testErrorMessage() {
        XCTAssertEqual(
            MascotMessage(body: ["type": "error", "message": "failed"]),
            .error("failed")
        )
    }

    func testDiagnosticMessage() {
        XCTAssertEqual(
            MascotMessage(body: ["type": "diagnostic", "message": "model-loaded"]),
            .diagnostic("model-loaded")
        )
    }

    func testUnknownMessageIsRejected() {
        XCTAssertNil(MascotMessage(body: ["type": "unknown"]))
    }
}
