package red.steele.loom

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.projection.MediaProjectionManager
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
    private var screenshotEventSink: EventChannel.EventSink? = null
    private var screenshotReceiver: BroadcastReceiver? = null

    companion object {
        private const val REQUEST_MEDIA_PROJECTION = 1001
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        appLifecycleMonitor = AppLifecycleMonitor(this)

        // Setup notification monitoring channels
        NotificationMonitor.setupChannels(flutterEngine, this)

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

        // Screenshot Method Channel
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "red.steele.loom/screenshot").setMethodCallHandler { call, result ->
            when (call.method) {
                "requestScreenshotPermission" -> {
                    requestMediaProjectionPermission()
                    result.success(true)
                }
                "hasScreenshotPermission" -> {
                    // For now, we can't easily check if we have permission
                    // Would need to track if user granted permission
                    result.success(false)
                }
                "startAutomaticCapture" -> {
                    val intervalMillis = call.argument<Int>("intervalMillis")?.toLong() ?: 300000L
                    // This would need the media projection result from requestScreenshotPermission
                    result.success(false) // For now
                }
                "stopAutomaticCapture" -> {
                    val stopIntent = Intent(this, ScreenshotService::class.java)
                    stopIntent.action = ScreenshotService.ACTION_STOP_CAPTURE
                    startService(stopIntent)
                    result.success(true)
                }
                "takeScreenshot" -> {
                    // We need to request permission first if not granted
                    requestMediaProjectionPermission()
                    // The actual screenshot will be taken after permission is granted
                    // For now, we return null as we need to wait for the permission result
                    result.success(null)
                }
                "isServiceRunning" -> {
                    // Check if screenshot service is running
                    result.success(false)
                }
                else -> result.notImplemented()
            }
        }

        // Screenshot Event Channel
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, "red.steele.loom/screenshot_events").setStreamHandler(
            object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    screenshotEventSink = events
                    registerScreenshotReceiver()
                }

                override fun onCancel(arguments: Any?) {
                    screenshotEventSink = null
                    unregisterScreenshotReceiver()
                }
            }
        )
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
        unregisterScreenshotReceiver()
    }

    private fun requestMediaProjectionPermission() {
        val mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        val permissionIntent = mediaProjectionManager.createScreenCaptureIntent()
        startActivityForResult(permissionIntent, REQUEST_MEDIA_PROJECTION)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == REQUEST_MEDIA_PROJECTION) {
            if (resultCode == Activity.RESULT_OK && data != null) {
                // Start the screenshot service with the permission result
                val serviceIntent = Intent(this, ScreenshotService::class.java).apply {
                    action = ScreenshotService.ACTION_START_CAPTURE
                    putExtra(ScreenshotService.EXTRA_RESULT_CODE, resultCode)
                    putExtra(ScreenshotService.EXTRA_RESULT_DATA, data)
                    putExtra(ScreenshotService.EXTRA_INTERVAL_MILLIS, 300000L) // 5 minutes default
                }
                startService(serviceIntent)
            }
        }
    }

    private fun registerScreenshotReceiver() {
        screenshotReceiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                if (intent?.action == "red.steele.loom.SCREENSHOT_CAPTURED") {
                    val screenshotData = intent.getByteArrayExtra("screenshot_data")
                    if (screenshotData != null) {
                        screenshotEventSink?.success(screenshotData)
                    }
                }
            }
        }

        val filter = IntentFilter("red.steele.loom.SCREENSHOT_CAPTURED")
        registerReceiver(screenshotReceiver, filter)
    }

    private fun unregisterScreenshotReceiver() {
        screenshotReceiver?.let {
            try {
                unregisterReceiver(it)
            } catch (e: IllegalArgumentException) {
                // Receiver not registered
            }
        }
        screenshotReceiver = null
    }
}
