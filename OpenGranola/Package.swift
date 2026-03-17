// swift-tools-version: 6.2

import PackageDescription

let package = Package(
    name: "OpenGranola",
    platforms: [.macOS(.v26)],
    dependencies: [
        .package(url: "https://github.com/FluidInference/FluidAudio.git", from: "0.7.9"),
    ],
    targets: [
        .executableTarget(
            name: "OpenGranola",
            dependencies: [
                .product(name: "FluidAudio", package: "FluidAudio"),
            ],
            path: "Sources/OpenGranola",
            exclude: ["Info.plist", "OpenGranola.entitlements", "Assets"]
        ),
    ]
)
