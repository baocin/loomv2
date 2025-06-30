import 'package:flutter/material.dart';
import 'dart:convert';
import '../services/data_collection_service.dart';
import '../core/config/data_collection_config.dart';
import '../core/utils/power_estimation.dart';
import '../widgets/data_preview_dialog.dart';

class AdvancedSettingsScreen extends StatefulWidget {
  final DataCollectionService dataService;

  const AdvancedSettingsScreen({super.key, required this.dataService});

  @override
  State<AdvancedSettingsScreen> createState() => _AdvancedSettingsScreenState();
}

class _AdvancedSettingsScreenState extends State<AdvancedSettingsScreen> {
  final Map<String, bool> _expandedStates = {};
  int _globalUploadIntervalMs = 300000; // Default 5 minutes

  @override
  void initState() {
    super.initState();
    _loadGlobalUploadInterval();
  }

  void _loadGlobalUploadInterval() {
    // Get the upload interval from the first enabled data source
    for (final entry in widget.dataService.availableDataSources.entries) {
      final config = widget.dataService.getDataSourceConfig(entry.key);
      if (config != null && config.enabled) {
        setState(() {
          _globalUploadIntervalMs = config.uploadIntervalMs;
        });
        break;
      }
    }
  }

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
          
          // Global upload interval setting
          _buildGlobalUploadInterval(),
          const Divider(),
          
          // Data source parameter settings
          ...widget.dataService.availableDataSources.entries.map((entry) {
            final sourceId = entry.key;
            final dataSource = entry.value;
            final config = widget.dataService.getDataSourceConfig(sourceId);
            final powerLevel = config != null && config.enabled 
                ? PowerEstimation.calculateAdjustedPower(sourceId, config)
                : PowerEstimation.sensorPowerConsumption[sourceId] ?? 0;
            
            return Card(
              margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              child: Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  key: PageStorageKey(sourceId),
                  title: Row(
                    children: [
                      InkWell(
                        onTap: () => _showDataPreview(sourceId),
                        borderRadius: BorderRadius.circular(20),
                        child: Padding(
                          padding: const EdgeInsets.all(8.0),
                          child: Icon(_getDataSourceIcon(sourceId), size: 20),
                        ),
                      ),
                      Expanded(child: Text(dataSource.displayName)),
                      _buildPowerIndicator(powerLevel),
                    ],
                  ),
                  subtitle: Text(
                    config != null && config.enabled 
                        ? _getSubtitleText(sourceId, config, powerLevel)
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
                      _buildParameterControls(sourceId, config),
                    ],
                  ],
                ),
              ),
            );
          }).toList(),
          const SizedBox(height: 16),
          _buildSettingsExplainer(),
          const SizedBox(height: 80), // Space for FAB
        ],
      ),
    );
  }

  Widget _buildGlobalUploadInterval() {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.cloud_upload, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                const Text(
                  'Global Upload Interval',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Force upload of all pending data after this time',
              style: TextStyle(color: Colors.grey[600], fontSize: 14),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Upload Interval', style: TextStyle(fontWeight: FontWeight.w500)),
                Text(
                  _formatDuration(_globalUploadIntervalMs),
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.primary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
            Slider(
              value: _globalUploadIntervalMs / 1000,
              min: 1,
              max: 3600,
              divisions: 360,
              label: _formatDuration(_globalUploadIntervalMs),
              onChanged: (value) async {
                setState(() {
                  _globalUploadIntervalMs = (value * 1000).toInt();
                });
                // Update all data source configs with new upload interval
                for (final sourceId in widget.dataService.availableDataSources.keys) {
                  final config = widget.dataService.getDataSourceConfig(sourceId);
                  if (config != null) {
                    final newConfig = config.copyWith(uploadIntervalMs: _globalUploadIntervalMs);
                    await widget.dataService.updateDataSourceConfig(sourceId, newConfig);
                  }
                }
              },
            ),
            Text(
              'Range: 1 second to 1 hour',
              style: TextStyle(color: Colors.grey[600], fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDuration(int milliseconds) {
    final seconds = milliseconds / 1000;
    if (seconds < 60) {
      return '${seconds.toStringAsFixed(0)} second${seconds == 1 ? '' : 's'}';
    } else if (seconds < 3600) {
      final minutes = seconds / 60;
      return '${minutes.toStringAsFixed(1)} minute${minutes == 1 ? '' : 's'}';
    } else {
      final hours = seconds / 3600;
      return '${hours.toStringAsFixed(1)} hour${hours == 1 ? '' : 's'}';
    }
  }

  Widget _buildPowerConsumptionSummary() {
    // Collect configs for all active sources
    final configs = <String, DataSourceConfigParams>{};
    for (final entry in widget.dataService.availableDataSources.entries) {
      final config = widget.dataService.getDataSourceConfig(entry.key);
      if (config != null && config.enabled) {
        configs[entry.key] = config;
      }
    }
    
    final totalPower = PowerEstimation.calculateCombinedPowerWithConfigs(configs);
    final powerLevel = PowerEstimation.getPowerLevelDescription(totalPower);
    final batteryDrain = PowerEstimation.estimateBatteryDrain(totalPower);
    
    return Card(
      margin: const EdgeInsets.all(16),
      elevation: 2,
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
              '${configs.length} active data sources',
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
            divisions: sourceId == 'accelerometer' ? 1000 : 100,
            unit: sourceId == 'accelerometer' && config.collectionIntervalMs < 1000 
                ? ' per second' 
                : 's',
            displayFormatter: sourceId == 'accelerometer' && config.collectionIntervalMs < 1000
                ? (v) => '${(1000 / (v * 1000)).toStringAsFixed(0)}'
                : null,
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
                ButtonSegment(value: 8000, label: Text('8000/s')),
                ButtonSegment(value: 16000, label: Text('16000/s')),
                ButtonSegment(value: 44100, label: Text('44100/s')),
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
    String Function(double)? displayFormatter,
    required ValueChanged<double> onChanged,
  }) {
    final displayValue = displayFormatter != null 
        ? displayFormatter(value)
        : (isInt ? value.toInt().toString() : value.toStringAsFixed(1));
    
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
        return 10.0; // 10 seconds minimum
      case 'accelerometer':
        return 0.01; // 10ms minimum (100 per second)
      case 'screenshot':
        return 60.0; // 1 minute minimum
      case 'camera':
        return 300.0; // 5 minutes minimum
      case 'audio':
        return 10.0; // 10 seconds minimum
      case 'android_app_monitoring':
        return 60.0; // 1 minute minimum
      case 'battery':
      case 'network':
        return 30.0; // 30 seconds minimum
      case 'screen_state':
      case 'app_lifecycle':
        return 1.0; // 1 second minimum (event-based)
      default:
        return 5.0;
    }
  }

  double _getMaxInterval(String sourceId) {
    switch (sourceId) {
      case 'accelerometer':
        return 300.0; // 5 minutes max
      case 'screenshot':
        return 7200.0; // 2 hours max
      case 'camera':
        return 86400.0; // 24 hours max
      case 'gps':
        return 3600.0; // 1 hour max
      case 'audio':
        return 600.0; // 10 minutes max
      case 'android_app_monitoring':
        return 3600.0; // 1 hour max
      case 'battery':
      case 'network':
        return 1800.0; // 30 minutes max
      case 'screen_state':
      case 'app_lifecycle':
        return 300.0; // 5 minutes max (event-based)
      default:
        return 600.0; // 10 minutes max
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

  Widget _buildSettingsExplainer() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Theme.of(context).dividerColor),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.help_outline, size: 20, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Settings Guide',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _buildExplainerItem(
              icon: Icons.timer,
              title: 'Collection Interval',
              description: 'How often the sensor collects data. For example, "30s" means data is collected every 30 seconds.',
              example: 'Lower values = more frequent collection = higher battery usage',
            ),
            const SizedBox(height: 12),
            _buildExplainerItem(
              icon: Icons.layers,
              title: 'Upload Batch Size',
              description: 'Number of data points collected before uploading to the server. Larger batches reduce network overhead.',
              example: 'Batch of 10 = upload after collecting 10 readings',
            ),
            const SizedBox(height: 12),
            _buildExplainerItem(
              icon: Icons.cloud_upload,
              title: 'Upload Interval',
              description: 'Maximum time before forcing an upload, even if the batch isn\'t full. Ensures data freshness.',
              example: '5 minutes = data uploaded at least every 5 minutes',
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.lightbulb_outline, size: 18, color: Theme.of(context).colorScheme.onPrimaryContainer),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Tip: Balance battery life vs data freshness by adjusting these settings. The power indicator updates in real-time!',
                      style: TextStyle(fontSize: 13, color: Theme.of(context).colorScheme.onPrimaryContainer),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExplainerItem({
    required IconData icon,
    required String title,
    required String description,
    required String example,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 18, color: Theme.of(context).colorScheme.secondary),
            const SizedBox(width: 6),
            Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 14,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Padding(
          padding: const EdgeInsets.only(left: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                description,
                style: TextStyle(
                  fontSize: 13,
                  color: Colors.grey[700],
                ),
              ),
              const SizedBox(height: 2),
              Text(
                example,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _showDataPreview(String sourceId) {
    showDialog(
      context: context,
      builder: (context) => DataPreviewDialog(
        sourceId: sourceId,
        dataService: widget.dataService,
      ),
    );
  }

  String _getSubtitleText(String sourceId, DataSourceConfigParams config, double powerLevel) {
    String intervalText;
    if (sourceId == 'accelerometer' && config.collectionIntervalMs < 1000) {
      final perSecond = 1000 / config.collectionIntervalMs;
      intervalText = '${perSecond.toStringAsFixed(0)}/second';
    } else {
      intervalText = '${(config.collectionIntervalMs / 1000).toStringAsFixed(1)}s';
    }
    
    return 'Interval: $intervalText, Batch: ${config.uploadBatchSize}, ${PowerEstimation.estimateBatteryDrain(powerLevel)}';
  }
}