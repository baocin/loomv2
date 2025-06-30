package red.steele.loom

import android.content.Intent
import android.content.IntentFilter
import android.os.Bundle
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private lateinit var screenStateReceiver: ScreenStateReceiver
    private lateinit var appLifecycleMonitor: AppLifecycleMonitor
    private var screenStateEventSink: EventChannel.EventSink? = null
    private var appLifecycleEventSink: EventChannel.EventSink? = null
    
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        appLifecycleMonitor = AppLifecycleMonitor(this)
        
        // Screen State Method Channel
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "red.steele.loom/screen_state").setMethodCallHandler { call, result ->
            when (call.method) {
                "getScreenState" -> {
                    result.success(ScreenStateReceiver.getScreenState(this))
                }
                else -> result.notImplemented()
            }
        }
        
        // Screen State Event Channel
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, "red.steele.loom/screen_state_events").setStreamHandler(
            object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    screenStateEventSink = events
                    registerScreenStateReceiver()
                }
                
                override fun onCancel(arguments: Any?) {
                    screenStateEventSink = null
                    unregisterScreenStateReceiver()
                }
            }
        )
        
        // App Lifecycle Method Channel
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "red.steele.loom/app_lifecycle").setMethodCallHandler { call, result ->
            when (call.method) {
                "startAppMonitoring" -> {
                    appLifecycleMonitor.startMonitoring()
                    result.success(true)
                }
                "stopAppMonitoring" -> {
                    appLifecycleMonitor.stopMonitoring()
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
        
        // App Lifecycle Event Channel
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, "red.steele.loom/app_lifecycle_events").setStreamHandler(
            object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    appLifecycleEventSink = events
                    appLifecycleMonitor.setEventSink(events)
                }
                
                override fun onCancel(arguments: Any?) {
                    appLifecycleEventSink = null
                    appLifecycleMonitor.setEventSink(null)
                }
            }
        )
        
        // App Monitoring Method Channel
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "red.steele.loom/app_monitoring").setMethodCallHandler { call, result ->
            when (call.method) {
                "hasUsageStatsPermission" -> {
                    result.success(appLifecycleMonitor.hasUsageStatsPermission())
                }
                "getRunningApps" -> {
                    result.success(appLifecycleMonitor.getRunningApps())
                }
                "getUsageStats" -> {
                    val intervalMinutes = call.argument<Int>("intervalMinutes") ?: 60
                    result.success(appLifecycleMonitor.getUsageStats(intervalMinutes))
                }
                "requestUsageStatsPermission" -> {
                    // Open usage stats settings
                    val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
                    startActivity(intent)
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
    }
    
    private fun registerScreenStateReceiver() {
        screenStateReceiver = ScreenStateReceiver(screenStateEventSink)
        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_ON)
            addAction(Intent.ACTION_SCREEN_OFF)
            addAction(Intent.ACTION_USER_PRESENT)
            addAction(Intent.ACTION_POWER_CONNECTED)
            addAction(Intent.ACTION_POWER_DISCONNECTED)
        }
        registerReceiver(screenStateReceiver, filter)
    }
    
    private fun unregisterScreenStateReceiver() {
        try {
            unregisterReceiver(screenStateReceiver)
        } catch (e: IllegalArgumentException) {
            // Receiver not registered
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        unregisterScreenStateReceiver()
    }
}