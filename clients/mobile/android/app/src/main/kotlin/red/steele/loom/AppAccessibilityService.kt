package red.steele.loom

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.pm.PackageManager
import android.view.accessibility.AccessibilityEvent
import android.content.Intent
import android.os.Handler
import android.os.Looper
import io.flutter.plugin.common.EventChannel
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.dart.DartExecutor

class AppAccessibilityService : AccessibilityService() {
    companion object {
        private var eventSink: EventChannel.EventSink? = null
        private var instance: AppAccessibilityService? = null
        private var screenshotEventSink: EventChannel.EventSink? = null

        fun setEventSink(sink: EventChannel.EventSink?) {
            eventSink = sink
        }

        fun setScreenshotEventSink(sink: EventChannel.EventSink?) {
            screenshotEventSink = sink
        }

        fun isServiceEnabled(): Boolean {
            return instance != null
        }

        fun requestScreenshot() {
            instance?.triggerScreenshot()
        }
    }

    private val appPackageManager: PackageManager by lazy { applicationContext.packageManager }
    private val currentForegroundApps = mutableMapOf<String, Long>()
    private val handler = Handler(Looper.getMainLooper())
    private var lastScreenshotTime = 0L
    private val SCREENSHOT_COOLDOWN_MS = 5000L // 5 seconds minimum between screenshots

    override fun onCreate() {
        super.onCreate()
        instance = this
        println("WARNING: AppAccessibilityService created")
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        println("WARNING: AppAccessibilityService destroyed")
    }

    override fun onServiceConnected() {
        val info = AccessibilityServiceInfo()

        // Configure the service to listen for window state changes
        info.eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
        info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
        info.flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS
        info.notificationTimeout = 100

        serviceInfo = info

        println("WARNING: AppAccessibilityService connected and configured")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return

        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            val packageName = event.packageName?.toString() ?: return

            // Skip system UI and launcher events
            if (packageName.startsWith("com.android.systemui") ||
                packageName.contains("launcher")) {
                return
            }

            val timestamp = System.currentTimeMillis()

            // Get app name
            val appName = try {
                val appInfo = appPackageManager.getApplicationInfo(packageName, 0)
                appPackageManager.getApplicationLabel(appInfo).toString()
            } catch (e: PackageManager.NameNotFoundException) {
                packageName
            }

            // Determine event type
            val eventType = if (currentForegroundApps.containsKey(packageName)) {
                // App was already in foreground, this might be a screen change within the app
                return
            } else {
                // New app came to foreground
                "foreground"
            }

            // Calculate duration for previous foreground app
            var previousAppPackage: String? = null
            var previousAppDuration: Int? = null

            if (currentForegroundApps.isNotEmpty()) {
                // Find the most recent foreground app
                val mostRecent = currentForegroundApps.maxByOrNull { it.value }
                if (mostRecent != null) {
                    previousAppPackage = mostRecent.key
                    previousAppDuration = ((timestamp - mostRecent.value) / 1000).toInt()

                    // Send background event for previous app
                    sendAppLifecycleEvent(
                        packageName = previousAppPackage,
                        eventType = "background",
                        timestamp = timestamp,
                        durationSeconds = previousAppDuration
                    )
                }
            }

            // Update current foreground app
            currentForegroundApps.clear()
            currentForegroundApps[packageName] = timestamp

            // Send foreground event for new app
            sendAppLifecycleEvent(
                packageName = packageName,
                appName = appName,
                eventType = eventType,
                timestamp = timestamp
            )

            println("WARNING: App lifecycle event detected via Accessibility - app: $appName ($packageName), event: $eventType")

            // Trigger a screenshot when apps change (with cooldown)
            if (eventType == "foreground" && shouldTakeScreenshot()) {
                // Delay screenshot slightly to let the app fully render
                handler.postDelayed({
                    triggerScreenshot()
                }, 1000)
            }
        }
    }

    private fun sendAppLifecycleEvent(
        packageName: String,
        appName: String? = null,
        eventType: String,
        timestamp: Long,
        durationSeconds: Int? = null
    ) {
        val eventData = mutableMapOf(
            "packageName" to packageName,
            "eventType" to eventType,
            "timestamp" to timestamp
        )

        appName?.let { eventData["appName"] = it }
        durationSeconds?.let { eventData["durationSeconds"] = it }

        eventSink?.success(eventData)
    }

    private fun shouldTakeScreenshot(): Boolean {
        val now = System.currentTimeMillis()
        if (now - lastScreenshotTime < SCREENSHOT_COOLDOWN_MS) {
            return false
        }
        return true
    }

    private fun triggerScreenshot() {
        if (!shouldTakeScreenshot()) {
            println("WARNING: Screenshot skipped - cooldown period")
            return
        }

        lastScreenshotTime = System.currentTimeMillis()

        // Check if screenshot service is running
        if (ScreenshotService.isServiceRunning(this)) {
            // Send broadcast to take screenshot
            val intent = Intent("red.steele.loom.TAKE_SCREENSHOT_NOW")
            intent.putExtra("reason", "app_change")
            sendBroadcast(intent)
            println("WARNING: Screenshot triggered by accessibility service - app change detected")
        } else {
            // Notify Flutter to request screenshot permission
            screenshotEventSink?.success(mapOf(
                "event" to "screenshot_permission_needed",
                "reason" to "app_change_detected"
            ))
        }
    }

    override fun onInterrupt() {
        println("WARNING: AppAccessibilityService interrupted")
    }
}
