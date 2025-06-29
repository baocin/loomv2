# Service Tests

This directory contains unit tests for the service layer of the FOOM application.

## Database Service Tests

The `database_service_test.dart` file contains tests for the core functionality of the `DatabaseService` class, including:

- Configuration operations
- Device management
- Sensor operations

## Sensor Stats Tests

The `sensor_stats_test.dart` file contains tests specifically for the sensor statistics functionality, including:

- Creation of sensor stats when data is inserted
- Calculation of running averages for payload sizes
- Retrieval of stats for multiple sensors

## Running the Tests

To run all tests:

```bash
flutter test
```

To run a specific test file:

```bash
flutter test test/services/database_service_test.dart
flutter test test/services/sensor_stats_test.dart
flutter test test/widgets/hertz_modal_test.dart
```

## Test Setup

The tests use `sqflite_common_ffi` to create an in-memory database for testing. This allows the tests to run without affecting the actual database used by the application.

A mock path provider is used to create a temporary directory for the test database, which is cleaned up after each test.

## Adding New Tests

When adding new tests:

1. Create a new test file in the appropriate directory
2. Import the necessary dependencies
3. Set up the test environment with `setUp` and `tearDown` methods
4. Group related tests together using the `group` function
5. Write individual test cases using the `test` function

## Test Coverage

To generate a test coverage report:

```bash
flutter test --coverage
```

This will generate a coverage report in the `coverage` directory. You can use tools like `lcov` to convert this to a more readable format:

```bash
genhtml coverage/lcov.info -o coverage/html
```

Then open `coverage/html/index.html` in a browser to view the coverage report. 