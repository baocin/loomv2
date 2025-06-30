import 'package:flutter/material.dart';
import '../services/data_collection_service.dart';
import '../core/config/data_collection_config.dart';
import '../core/utils/power_estimation.dart';

class AdvancedSettingsScreen extends StatefulWidget {
  final DataCollectionService dataService;

  const AdvancedSettingsScreen({super.key, required this.dataService});

  @override
  State<AdvancedSettingsScreen> createState() => _AdvancedSettingsScreenState();
}

class _AdvancedSettingsScreenState extends State<AdvancedSettingsScreen> {
  final Map<String, bool> _expandedStates = {};

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Advanced Data Source Settings'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: ListView(
        children: [
          // Power consumption summary card
          _buildPowerConsumptionSummary(),
          const Divider(),
          
          // Data source parameter settings
          ...widget.dataService.availableDataSources.entries.map((entry) {
            final sourceId = entry.key;
            final dataSource = entry.value;
            final config = widget.dataService.getDataSourceConfig(sourceId);
            final powerLevel = PowerEstimation.sensorPowerConsumption[sourceId] ?? 0;
            
            return Card(
              margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              child: Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  key: PageStorageKey(sourceId),
                  title: Row(
                    children: [
                      Icon(_getDataSourceIcon(sourceId), size: 20),
                      const SizedBox(width: 8),
                      Expanded(child: Text(dataSource.displayName)),
                      _buildPowerIndicator(powerLevel),
                    ],
                  ),
                  subtitle: Text(
                    config != null && config.enabled 
                        ? 'Interval: ${(config.collectionIntervalMs / 1000).toStringAsFixed(1)}s, Batch: ${config.uploadBatchSize}'
                        : 'Disabled',
                    style: TextStyle(
                      color: config?.enabled == true ? null : Colors.grey,
                    ),
                  ),
                  initiallyExpanded: _expandedStates[sourceId] ?? false,
                  onExpansionChanged: (expanded) {
                    setState(() {
                      _expandedStates[sourceId] = expanded;
                    });
                  },
                  children: [
                    if (config != null) ...[
                      _buildPowerConsumptionInfo(sourceId),
                      const Divider(indent: 16, endIndent: 16),
                      _buildParameterControls(sourceId, config),
                    ],
                  ],
                ),
              ),
            );
          }).toList(),
        ],
      ),
    );
  }

  Widget _buildPowerConsumptionSummary() {
    final activeSources = widget.dataService.availableDataSources.entries
        .where((e) => widget.dataService.getDataSourceConfig(e.key)?.enabled == true)
        .map((e) => e.key)
        .toList();
    
    final totalPower = PowerEstimation.calculateCombinedPower(activeSources);
    final powerLevel = PowerEstimation.getPowerLevelDescription(totalPower);
    final batteryDrain = PowerEstimation.estimateBatteryDrain(totalPower);
    
    return Card(
      margin: const EdgeInsets.all(16),
      color: _getPowerColor(totalPower).withOpacity(0.1),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.battery_alert, color: _getPowerColor(totalPower)),
                const SizedBox(width: 8),
                const Text(
                  'Total Power Consumption',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '$powerLevel - $batteryDrain',
              style: TextStyle(
                fontSize: 16,
                color: _getPowerColor(totalPower),
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '${activeSources.length} active data sources',
              style: TextStyle(color: Colors.grey[600]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPowerIndicator(double powerLevel) {
    final color = _getPowerColor(powerLevel);
    final description = PowerEstimation.getPowerLevelDescription(powerLevel);
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.power, size: 14, color: color),
          const SizedBox(width: 4),
          Text(
            description,
            style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }

  Widget _buildPowerConsumptionInfo(String sourceId) {
    final powerFactors = PowerEstimation.getDetailedPowerFactors(sourceId);
    final basePower = powerFactors['base_power'] as double;
    final factors = Map<String, dynamic>.from(powerFactors['factors'] as Map);
    final tips = List<dynamic>.from(powerFactors['tips'] as List);
    
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.blue.withOpacity(0.05),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline, size: 16, color: Colors.blue[700]),
              const SizedBox(width: 8),
              Text(
                'Power Consumption Info',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.blue[700],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Base consumption: ${PowerEstimation.estimateBatteryDrain(basePower)}',
            style: const TextStyle(fontSize: 13),
          ),
          if (factors.isNotEmpty) ...[
            const SizedBox(height: 8),
            const Text('Factors affecting power:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
            ...factors.entries.map((e) => Padding(
              padding: const EdgeInsets.only(left: 8, top: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('• ', style: TextStyle(fontSize: 13)),
                  Expanded(
                    child: Text(
                      '${e.key}: ${e.value}',
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                ],
              ),
            )),
          ],
          if (tips.isNotEmpty) ...[
            const SizedBox(height: 8),
            const Text('Power saving tips:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
            ...tips.map((tip) => Padding(
              padding: const EdgeInsets.only(left: 8, top: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('✓ ', style: TextStyle(color: Colors.green[700], fontSize: 13)),
                  Expanded(
                    child: Text(tip.toString(), style: const TextStyle(fontSize: 13)),
                  ),
                ],
              ),
            )),
          ],
        ],
      ),
    );
  }

  Widget _buildParameterControls(String sourceId, DataSourceConfigParams config) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Collection Interval
          _buildSliderControl(
            title: 'Collection Interval',
            value: config.collectionIntervalMs / 1000,
            min: _getMinInterval(sourceId),
            max: _getMaxInterval(sourceId),
            divisions: 100,
            unit: 's',
            onChanged: (value) async {
              final newConfig = config.copyWith(collectionIntervalMs: (value * 1000).toInt());
              await widget.dataService.updateDataSourceConfig(sourceId, newConfig);
              setState(() {});
            },
          ),
          const SizedBox(height: 16),
          
          // Upload Batch Size
          _buildSliderControl(
            title: 'Upload Batch Size',
            value: config.uploadBatchSize.toDouble(),
            min: 1,
            max: _getMaxBatchSize(sourceId),
            divisions: _getMaxBatchSize(sourceId).toInt() - 1,
            unit: ' items',
            isInt: true,
            onChanged: (value) async {
              final newConfig = config.copyWith(uploadBatchSize: value.toInt());
              await widget.dataService.updateDataSourceConfig(sourceId, newConfig);
              setState(() {});
            },
          ),
          const SizedBox(height: 16),
          
          // Upload Interval
          _buildSliderControl(
            title: 'Upload Interval',
            value: config.uploadIntervalMs / 1000,
            min: 5,
            max: 300,
            divisions: 59,
            unit: 's',
            onChanged: (value) async {
              final newConfig = config.copyWith(uploadIntervalMs: (value * 1000).toInt());
              await widget.dataService.updateDataSourceConfig(sourceId, newConfig);
              setState(() {});
            },
          ),
          
          // Source-specific settings
          if (sourceId == 'screenshot') ...[
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('Skip when screen unchanged'),
              subtitle: const Text('Saves power by avoiding duplicate captures'),
              value: config.customParams['skip_unchanged'] ?? true,
              onChanged: (value) async {
                final customParams = Map<String, dynamic>.from(config.customParams);
                customParams['skip_unchanged'] = value;
                final newConfig = config.copyWith(customParams: customParams);
                await widget.dataService.updateDataSourceConfig(sourceId, newConfig);
                setState(() {});
              },
            ),
          ],
          
          if (sourceId == 'gps') ...[
            const SizedBox(height: 16),
            const Text('Location Accuracy', style: TextStyle(fontWeight: FontWeight.w500)),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'low', label: Text('Low')),
                ButtonSegment(value: 'medium', label: Text('Medium')),
                ButtonSegment(value: 'high', label: Text('High')),
              ],
              selected: {(config.customParams['accuracy'] ?? 'medium') as String},
              onSelectionChanged: (Set<String> selected) async {
                final customParams = Map<String, dynamic>.from(config.customParams);
                customParams['accuracy'] = selected.first;
                final newConfig = config.copyWith(customParams: customParams);
                await widget.dataService.updateDataSourceConfig(sourceId, newConfig);
                setState(() {});
              },
            ),
          ],
          
          if (sourceId == 'audio') ...[
            const SizedBox(height: 16),
            const Text('Sample Rate', style: TextStyle(fontWeight: FontWeight.w500)),
            const SizedBox(height: 8),
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 8000, label: Text('8 kHz')),
                ButtonSegment(value: 16000, label: Text('16 kHz')),
                ButtonSegment(value: 44100, label: Text('44.1 kHz')),
              ],
              selected: {(config.customParams['sample_rate'] ?? 16000) as int},
              onSelectionChanged: (Set<int> selected) async {
                final customParams = Map<String, dynamic>.from(config.customParams);
                customParams['sample_rate'] = selected.first;
                final newConfig = config.copyWith(customParams: customParams);
                await widget.dataService.updateDataSourceConfig(sourceId, newConfig);
                setState(() {});
              },
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSliderControl({
    required String title,
    required double value,
    required double min,
    required double max,
    required int divisions,
    required String unit,
    bool isInt = false,
    required ValueChanged<double> onChanged,
  }) {
    final displayValue = isInt ? value.toInt().toString() : value.toStringAsFixed(1);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w500)),
            Text('$displayValue$unit', style: TextStyle(color: Theme.of(context).primaryColor)),
          ],
        ),
        Slider(
          value: value.clamp(min, max),
          min: min,
          max: max,
          divisions: divisions,
          label: '$displayValue$unit',
          onChanged: onChanged,
        ),
      ],
    );
  }

  // Helper methods
  Color _getPowerColor(double level) {
    final hex = PowerEstimation.getPowerLevelColor(level);
    return Color(int.parse(hex.substring(1), radix: 16) + 0xFF000000);
  }

  double _getMinInterval(String sourceId) {
    switch (sourceId) {
      case 'gps':
        return 5.0; // 5 seconds minimum
      case 'accelerometer':
        return 0.1; // 100ms minimum
      case 'screenshot':
        return 30.0; // 30 seconds minimum
      case 'camera':
        return 60.0; // 1 minute minimum
      default:
        return 1.0;
    }
  }

  double _getMaxInterval(String sourceId) {
    switch (sourceId) {
      case 'accelerometer':
        return 60.0; // 1 minute max
      case 'screenshot':
      case 'camera':
        return 3600.0; // 1 hour max
      default:
        return 300.0; // 5 minutes max
    }
  }

  double _getMaxBatchSize(String sourceId) {
    switch (sourceId) {
      case 'audio':
        return 10.0; // Smaller batches for audio
      case 'accelerometer':
        return 100.0; // Larger batches for high-frequency data
      case 'screenshot':
      case 'camera':
        return 5.0; // Small batches for images
      default:
        return 50.0;
    }
  }

  IconData _getDataSourceIcon(String sourceId) {
    switch (sourceId) {
      case 'gps':
        return Icons.location_on;
      case 'accelerometer':
        return Icons.screen_rotation;
      case 'battery':
        return Icons.battery_full;
      case 'network':
        return Icons.wifi;
      case 'audio':
        return Icons.mic;
      case 'screenshot':
        return Icons.screenshot;
      case 'camera':
        return Icons.camera_alt;
      case 'screen_state':
        return Icons.phone_android;
      case 'app_lifecycle':
        return Icons.apps;
      case 'android_app_monitoring':
        return Icons.analytics;
      default:
        return Icons.sensors;
    }
  }
}