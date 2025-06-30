package red.steele.loom

import android.app.ActivityManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import io.flutter.plugin.common.EventChannel
import java.util.*

class AppLifecycleMonitor(private val context: Context) {
    private val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
    private val packageManager = context.packageManager
    private val usageStatsManager = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
        context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
    } else null
    
    private val trackedApps = mutableMapOf<String, AppState>()
    private var eventSink: EventChannel.EventSink? = null
    
    data class AppState(
        val packageName: String,
        val appName: String,
        var lastEventType: String,
        var lastEventTime: Long
    )
    
    fun setEventSink(sink: EventChannel.EventSink?) {
        eventSink = sink
    }
    
    fun startMonitoring() {
        // Initial scan of running apps
        scanRunningApps()
    }
    
    fun stopMonitoring() {
        trackedApps.clear()
    }
    
    fun getRunningApps(): List<Map<String, Any>> {
        val runningApps = mutableListOf<Map<String, Any>>()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            // Use UsageStats for newer versions
            val endTime = System.currentTimeMillis()
            val startTime = endTime - 1000 * 60 * 5 // Last 5 minutes
            
            val usageEvents = usageStatsManager?.queryEvents(startTime, endTime)
            val activeApps = mutableSetOf<String>()
            
            while (usageEvents?.hasNextEvent() == true) {
                val event = UsageEvents.Event()
                usageEvents.getNextEvent(event)
                
                if (event.eventType == UsageEvents.Event.MOVE_TO_FOREGROUND ||
                    event.eventType == UsageEvents.Event.MOVE_TO_BACKGROUND) {
                    activeApps.add(event.packageName)
                }
            }
            
            // Get app info for active apps
            activeApps.forEach { packageName ->
                try {
                    val appInfo = packageManager.getApplicationInfo(packageName, 0)
                    val appName = packageManager.getApplicationLabel(appInfo).toString()
                    val pid = getProcessIdForPackage(packageName)
                    
                    runningApps.add(mapOf(
                        "packageName" to packageName,
                        "appName" to appName,
                        "pid" to (pid ?: 0),
                        "isForeground" to isAppInForeground(packageName),
                        "launchTime" to getAppLaunchTime(packageName),
                        "versionCode" to getAppVersionCode(packageName),
                        "versionName" to getAppVersionName(packageName)
                    ))
                } catch (e: PackageManager.NameNotFoundException) {
                    // App not found, skip
                }
            }
        } else {
            // Fallback for older versions
            val runningTasks = activityManager.runningAppProcesses
            runningTasks?.forEach { process ->
                try {
                    val appInfo = packageManager.getApplicationInfo(process.processName, 0)
                    val appName = packageManager.getApplicationLabel(appInfo).toString()
                    
                    runningApps.add(mapOf(
                        "packageName" to process.processName,
                        "appName" to appName,
                        "pid" to process.pid,
                        "isForeground" to (process.importance == ActivityManager.RunningAppProcessInfo.IMPORTANCE_FOREGROUND),
                        "launchTime" to 0L
                    ))
                } catch (e: PackageManager.NameNotFoundException) {
                    // App not found, skip
                }
            }
        }
        
        return runningApps
    }
    
    fun getUsageStats(intervalMinutes: Int): Map<String, Any> {
        val stats = mutableMapOf<String, Any>()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP && hasUsageStatsPermission()) {
            val endTime = System.currentTimeMillis()
            val startTime = endTime - (intervalMinutes * 60 * 1000)
            
            val usageStatsList = usageStatsManager?.queryUsageStats(
                UsageStatsManager.INTERVAL_BEST,
                startTime,
                endTime
            )
            
            val appUsageList = mutableListOf<Map<String, Any>>()
            var totalScreenTime = 0L
            
            usageStatsList?.forEach { usageStats ->
                if (usageStats.totalTimeInForeground > 0) {
                    try {
                        val appInfo = packageManager.getApplicationInfo(usageStats.packageName, 0)
                        val appName = packageManager.getApplicationLabel(appInfo).toString()
                        
                        appUsageList.add(mapOf(
                            "packageName" to usageStats.packageName,
                            "appName" to appName,
                            "totalTimeInForeground" to usageStats.totalTimeInForeground,
                            "lastTimeUsed" to usageStats.lastTimeUsed,
                            "launchCount" to getAppLaunchCount(usageStats.packageName, startTime, endTime)
                        ))
                        
                        totalScreenTime += usageStats.totalTimeInForeground
                    } catch (e: PackageManager.NameNotFoundException) {
                        // Skip
                    }
                }
            }
            
            stats["startTime"] = startTime
            stats["endTime"] = endTime
            stats["totalScreenTime"] = totalScreenTime
            stats["apps"] = appUsageList
        }
        
        return stats
    }
    
    fun hasUsageStatsPermission(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.LOLLIPOP) return false
        
        val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as android.app.AppOpsManager
            appOps.unsafeCheckOpNoThrow(
                android.app.AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                context.packageName
            )
        } else {
            @Suppress("DEPRECATION")
            val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as android.app.AppOpsManager
            appOps.checkOpNoThrow(
                android.app.AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                context.packageName
            )
        }
        
        return mode == android.app.AppOpsManager.MODE_ALLOWED
    }
    
    private fun scanRunningApps() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP && hasUsageStatsPermission()) {
            val endTime = System.currentTimeMillis()
            val startTime = endTime - 1000 * 60 // Last minute
            
            val usageEvents = usageStatsManager?.queryEvents(startTime, endTime)
            
            while (usageEvents?.hasNextEvent() == true) {
                val event = UsageEvents.Event()
                usageEvents.getNextEvent(event)
                
                handleUsageEvent(event)
            }
        }
    }
    
    private fun handleUsageEvent(event: UsageEvents.Event) {
        val packageName = event.packageName
        val timestamp = event.timeStamp
        
        val eventType = when (event.eventType) {
            UsageEvents.Event.MOVE_TO_FOREGROUND -> "foreground"
            UsageEvents.Event.MOVE_TO_BACKGROUND -> "background"
            else -> return
        }
        
        // Get app name
        val appName = try {
            val appInfo = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(appInfo).toString()
        } catch (e: PackageManager.NameNotFoundException) {
            packageName
        }
        
        // Check if this is a new event
        val lastState = trackedApps[packageName]
        if (lastState == null || lastState.lastEventType != eventType) {
            // Calculate duration for previous state
            val duration = if (lastState != null) {
                ((timestamp - lastState.lastEventTime) / 1000).toInt()
            } else null
            
            // Send event
            eventSink?.success(mapOf(
                "packageName" to packageName,
                "appName" to appName,
                "eventType" to eventType,
                "timestamp" to timestamp,
                "durationSeconds" to duration
            ))
            
            // Update tracked state
            trackedApps[packageName] = AppState(packageName, appName, eventType, timestamp)
        }
    }
    
    private fun isAppInForeground(packageName: String): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
            val endTime = System.currentTimeMillis()
            val startTime = endTime - 1000 // Last second
            
            val usageEvents = usageStatsManager?.queryEvents(startTime, endTime)
            var lastEventType = ""
            
            while (usageEvents?.hasNextEvent() == true) {
                val event = UsageEvents.Event()
                usageEvents.getNextEvent(event)
                
                if (event.packageName == packageName) {
                    when (event.eventType) {
                        UsageEvents.Event.MOVE_TO_FOREGROUND -> lastEventType = "foreground"
                        UsageEvents.Event.MOVE_TO_BACKGROUND -> lastEventType = "background"
                    }
                }
            }
            
            return lastEventType == "foreground"
        }
        
        return false
    }
    
    private fun getProcessIdForPackage(packageName: String): Int? {
        val runningProcesses = activityManager.runningAppProcesses
        return runningProcesses?.find { it.processName == packageName }?.pid
    }
    
    private fun getAppLaunchTime(packageName: String): Long {
        // This is an approximation - actual launch time tracking requires more complex logic
        return 0L
    }
    
    private fun getAppVersionCode(packageName: String): Int {
        return try {
            val packageInfo = packageManager.getPackageInfo(packageName, 0)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                packageInfo.longVersionCode.toInt()
            } else {
                @Suppress("DEPRECATION")
                packageInfo.versionCode
            }
        } catch (e: PackageManager.NameNotFoundException) {
            0
        }
    }
    
    private fun getAppVersionName(packageName: String): String {
        return try {
            val packageInfo = packageManager.getPackageInfo(packageName, 0)
            packageInfo.versionName ?: ""
        } catch (e: PackageManager.NameNotFoundException) {
            ""
        }
    }
    
    private fun getAppLaunchCount(packageName: String, startTime: Long, endTime: Long): Int {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.LOLLIPOP) return 0
        
        var launchCount = 0
        val usageEvents = usageStatsManager?.queryEvents(startTime, endTime)
        
        while (usageEvents?.hasNextEvent() == true) {
            val event = UsageEvents.Event()
            usageEvents.getNextEvent(event)
            
            if (event.packageName == packageName && 
                event.eventType == UsageEvents.Event.MOVE_TO_FOREGROUND) {
                launchCount++
            }
        }
        
        return launchCount
    }
}