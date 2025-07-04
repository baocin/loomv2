package red.steele.loom

import android.app.Service
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.DisplayMetrics
import android.view.WindowManager
import java.io.ByteArrayOutputStream
import java.util.Timer
import java.util.TimerTask

class ScreenshotService : Service() {
    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var timer: Timer? = null
    private var intervalMillis: Long = 300000 // 5 minutes default

    companion object {
        const val ACTION_START_CAPTURE = "red.steele.loom.START_CAPTURE"
        const val ACTION_STOP_CAPTURE = "red.steele.loom.STOP_CAPTURE"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        const val EXTRA_INTERVAL_MILLIS = "interval_millis"
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START_CAPTURE -> {
                val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, -1)
                val resultData = intent.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)
                intervalMillis = intent.getLongExtra(EXTRA_INTERVAL_MILLIS, 300000)

                if (resultCode != -1 && resultData != null) {
                    startCapture(resultCode, resultData)
                }
            }
            ACTION_STOP_CAPTURE -> {
                stopCapture()
                stopSelf()
            }
        }

        return START_STICKY
    }

    private fun startCapture(resultCode: Int, resultData: Intent) {
        val mediaProjectionManager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjection = mediaProjectionManager.getMediaProjection(resultCode, resultData)

        setupVirtualDisplay()
        startTimer()
    }

    private fun setupVirtualDisplay() {
        val windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        val displayMetrics = DisplayMetrics()
        windowManager.defaultDisplay.getMetrics(displayMetrics)

        val width = displayMetrics.widthPixels
        val height = displayMetrics.heightPixels
        val density = displayMetrics.densityDpi

        imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)

        virtualDisplay = mediaProjection?.createVirtualDisplay(
            "ScreenshotVirtualDisplay",
            width, height, density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader?.surface, null, null
        )
    }

    private fun startTimer() {
        timer = Timer()
        timer?.scheduleAtFixedRate(object : TimerTask() {
            override fun run() {
                captureScreenshot()
            }
        }, 0, intervalMillis)
    }

    private fun captureScreenshot() {
        val handler = Handler(Looper.getMainLooper())
        handler.post {
            try {
                val image = imageReader?.acquireLatestImage()
                if (image != null) {
                    val planes = image.planes
                    val buffer = planes[0].buffer
                    val pixelStride = planes[0].pixelStride
                    val rowStride = planes[0].rowStride
                    val rowPadding = rowStride - pixelStride * image.width

                    val bitmap = Bitmap.createBitmap(
                        image.width + rowPadding / pixelStride,
                        image.height,
                        Bitmap.Config.ARGB_8888
                    )
                    bitmap.copyPixelsFromBuffer(buffer)

                    // Crop if necessary
                    val croppedBitmap = if (rowPadding > 0) {
                        Bitmap.createBitmap(bitmap, 0, 0, image.width, image.height)
                    } else {
                        bitmap
                    }

                    // Compress to PNG
                    val outputStream = ByteArrayOutputStream()
                    croppedBitmap.compress(Bitmap.CompressFormat.PNG, 90, outputStream)
                    val screenshotBytes = outputStream.toByteArray()

                    // Send to Flutter
                    sendScreenshotToFlutter(screenshotBytes)

                    // Clean up
                    image.close()
                    if (rowPadding > 0) {
                        bitmap.recycle()
                    }
                    croppedBitmap.recycle()
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun sendScreenshotToFlutter(imageBytes: ByteArray) {
        // This will be handled by the MethodChannel in MainActivity
        val intent = Intent("red.steele.loom.SCREENSHOT_CAPTURED")
        intent.putExtra("screenshot_data", imageBytes)
        sendBroadcast(intent)
    }

    private fun stopCapture() {
        timer?.cancel()
        timer = null

        virtualDisplay?.release()
        virtualDisplay = null

        imageReader?.close()
        imageReader = null

        mediaProjection?.stop()
        mediaProjection = null
    }

    override fun onDestroy() {
        stopCapture()
        super.onDestroy()
    }
}
