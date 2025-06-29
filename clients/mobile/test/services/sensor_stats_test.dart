import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Sensor Stats Calculations', () {
    test('Running average calculation should work correctly', () {
      // Simulate the running average calculation used in the sensor stats
      int calculateRunningAverage(
          int currentAvg, int currentCount, int newValue) {
        // Formula: new_avg = old_avg + (new_value - old_avg) / new_count
        final int newCount = currentCount + 1;
        return currentAvg + ((newValue - currentAvg) ~/ newCount);
      }

      // Test with some sample values
      int avg = 100; // Starting with average of 100
      int count = 1; // One data point so far

      // Add a value of 200
      avg = calculateRunningAverage(avg, count, 200);
      count++;
      expect(avg, equals(150)); // (100 + 200) / 2 = 150

      // Add a value of 300
      avg = calculateRunningAverage(avg, count, 300);
      count++;
      expect(avg, equals(200)); // Moving toward 200 as we add larger values

      // Add a value of 400
      avg = calculateRunningAverage(avg, count, 400);
      count++;
      expect(avg, equals(250)); // Moving toward 250 as we add larger values

      // Add a smaller value of 50
      avg = calculateRunningAverage(avg, count, 50);
      count++;
      expect(avg, equals(210)); // Moving down as we add smaller values
    });

    test('Payload size calculation should handle different data types', () {
      // Simulate the payload size calculation
      int calculatePayloadSize(dynamic data) {
        if (data == null) return 0;

        if (data is String) {
          return data.length;
        } else if (data is List) {
          int size = 0;
          for (var item in data) {
            size += calculatePayloadSize(item);
          }
          return size;
        } else if (data is Map) {
          int size = 0;
          data.forEach((key, value) {
            size += calculatePayloadSize(key);
            size += calculatePayloadSize(value);
          });
          return size;
        } else {
          return data.toString().length;
        }
      }

      // Test with different data types
      expect(calculatePayloadSize("test"), equals(4));
      expect(calculatePayloadSize(["test", "data"]), equals(8));
      expect(calculatePayloadSize({"key": "value"}), equals(8));
      expect(calculatePayloadSize(null), equals(0));
      expect(calculatePayloadSize(123), equals(3));
    });
  });
}
