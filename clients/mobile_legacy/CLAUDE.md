# FOOM Project Guidelines

## Build Commands
- Build app: `flutter build <platform>` (ios, android, macos, web)
- Run app: `flutter run` or `flutter run -t lib/examples/run_permission_example.dart`
- Run tests: `flutter test`
- Run single test: `flutter test test/path/to/test_file.dart`
- Run with permissions: `./run_with_permissions.sh`
- Check code: `flutter analyze`
- Format code: `flutter format lib test`

## Code Style
- Follow official Flutter lint rules in analysis_options.yaml
- Organize imports in this order: dart, flutter, third-party, project
- Use camelCase for variables/methods, PascalCase for classes
- Prefer final variables when possible
- Use async/await for asynchronous operations
- Add comprehensive error handling with try/catch
- Implement DataSource interface for all data collection classes
- Use named parameters for better readability
- Document all public APIs with dartdoc comments
- Write unit tests for all business logic
- Use StreamControllers for reactive data sharing