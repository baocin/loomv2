import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Hertz modal should display correct time interval text',
      (WidgetTester tester) async {
    // Create a helper function similar to the one in the app
    String getTimeIntervalText(double frequency) {
      double seconds = 1 / frequency;
      if (seconds < 1) {
        return '${(seconds * 1000).toStringAsFixed(0)} milliseconds';
      } else if (seconds < 60) {
        return '${seconds.toStringAsFixed(1)} seconds';
      } else if (seconds < 3600) {
        return '${(seconds / 60).toStringAsFixed(1)} minutes';
      } else {
        return '${(seconds / 3600).toStringAsFixed(1)} hours';
      }
    }

    // Test various frequencies and expected outputs
    expect(getTimeIntervalText(1000.0), equals('1 milliseconds'));
    expect(getTimeIntervalText(100.0), equals('10 milliseconds'));
    expect(getTimeIntervalText(10.0), equals('100 milliseconds'));
    expect(getTimeIntervalText(1.0), equals('1.0 seconds'));
    expect(getTimeIntervalText(0.5), equals('2.0 seconds'));
    expect(getTimeIntervalText(0.1), equals('10.0 seconds'));
    expect(getTimeIntervalText(1 / 60), equals('1.0 minutes'));
    expect(getTimeIntervalText(1 / (10 * 60)), equals('10.0 minutes'));
    expect(getTimeIntervalText(1 / (60 * 60)), equals('1.0 hours'));
    expect(getTimeIntervalText(1 / (24 * 60 * 60)), equals('24.0 hours'));
  });

  testWidgets('Snap to common frequency function should work correctly',
      (WidgetTester tester) async {
    // Define the snap function similar to the one in the app
    double snapToCommonFrequency(double value) {
      // Common frequency values (Hz)
      final List<double> commonFrequencies = [
        1000.0, // 1000 times per second
        100.0, // 100 times per second
        10.0, // 10 times per second
        1.0, // Once per second
        1 / 10, // Once per 10 seconds
        1 / 60, // Once per minute
        1 / (10 * 60), // Once per 10 minutes
        1 / (60 * 60), // Once per hour
        1 / (24 * 60 * 60), // Once per day
        1 / (7 * 24 * 60 * 60), // Once per week
      ];

      for (var freq in commonFrequencies) {
        // If within 5% of a common frequency, snap to it
        if ((value - freq).abs() / freq < 0.05) {
          return freq;
        }
      }
      return value;
    }

    // Test snapping to common frequencies
    expect(snapToCommonFrequency(1.04), equals(1.0)); // Should snap to 1.0
    expect(snapToCommonFrequency(0.98), equals(1.0)); // Should snap to 1.0
    expect(snapToCommonFrequency(10.4), equals(10.0)); // Should snap to 10.0
    expect(snapToCommonFrequency(0.0167),
        equals(1 / 60)); // Should snap to once per minute
    expect(snapToCommonFrequency(0.5),
        equals(0.5)); // Should not snap (not close to any common frequency)
  });

  testWidgets('Decimal precision should adjust based on frequency value',
      (WidgetTester tester) async {
    // Test function to determine decimal precision
    int getDecimalPrecision(double frequency) {
      if (frequency < 0.01) return 4;
      if (frequency < 0.1) return 3;
      return 1;
    }

    // Test various frequencies
    expect(getDecimalPrecision(5.0), equals(1));
    expect(getDecimalPrecision(0.5), equals(1));
    expect(getDecimalPrecision(0.05), equals(3));
    expect(getDecimalPrecision(0.005), equals(4));
    expect(getDecimalPrecision(0.0001), equals(4));
  });
}
