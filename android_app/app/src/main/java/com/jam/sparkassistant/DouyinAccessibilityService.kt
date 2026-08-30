
package com.jam.sparkassistant

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class DouyinAccessibilityService : AccessibilityService() {
    
    enum class State {
        IDLE, FIND_FRIEND, CLICK_INPUT, CLICK_SEND, GO_BACK
    }
    
    companion object {
        var isRunning = false
        var isWaitingForTime = false
        var targetTime = ""
        var targetList: List<String> = emptyList()
        var currentIndex = 0
        var currentState = State.IDLE
        
        var instance: DouyinAccessibilityService? = null
        
        fun startExecution() {
            currentIndex = 0
            currentState = State.FIND_FRIEND
            instance?.showFloatingWindow()
            instance?.appendLog("🚀 任务启动，目标总数: \${targetList.size}")
        }
        
        fun hideFloatingWindow() {
            instance?.hideWindow()
        }
    }
    
    private var windowManager: WindowManager? = null
    private var floatingView: View? = null
    private var tvLog: TextView? = null

    fun showFloatingWindow() {
        if (floatingView != null) return
        try {
            windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
            val params = WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.TRANSLUCENT
            )
            params.gravity = Gravity.TOP or Gravity.START
            params.x = 20
            params.y = 200
            
            val layout = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setBackgroundColor(Color.parseColor("#99000000"))
                setPadding(20, 20, 20, 20)
            }
            
            tvLog = TextView(this).apply {
                text = "⚡ 悬浮调试日志就绪"
                setTextColor(Color.GREEN)
                textSize = 10f
            }
            layout.addView(tvLog)
            
            floatingView = layout
            windowManager?.addView(floatingView, params)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun hideWindow() {
        if (floatingView != null) {
            windowManager?.removeView(floatingView)
            floatingView = null
        }
    }

    fun appendLog(msg: String) {
        handler.post {
            val current = tvLog?.text?.toString() ?: ""
            val lines = current.split("\n").takeLast(6)
            tvLog?.text = (lines + msg).joinToString("\n")
        }
    }
    
    private val handler = Handler(Looper.getMainLooper())
    private val pollRunnable = object : Runnable {
        override fun run() {
            if (isWaitingForTime) {
                val sdf = SimpleDateFormat("HH:mm", Locale.getDefault())
                val currentTime = sdf.format(Date())
                if (currentTime == targetTime) {
                    isWaitingForTime = false
                    isRunning = true
                    startExecution()
                    
                    val launchIntent = packageManager.getLaunchIntentForPackage("my.maya.android")
                    if (launchIntent != null) {
                        launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        startActivity(launchIntent)
                    }
                }
            }
            
            if (isRunning) {
                processState()
            }
            handler.postDelayed(this, 1500)
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        handler.post(pollRunnable)
        Toast.makeText(this, "无障碍服务已连接", Toast.LENGTH_SHORT).show()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}

    override fun onInterrupt() {}

    override fun onDestroy() {
        super.onDestroy()
        hideWindow()
        instance = null
        handler.removeCallbacks(pollRunnable)
    }

    private fun processState() {
        val root = rootInActiveWindow ?: return
        if (currentIndex >= targetList.size) {
            isRunning = false
            currentState = State.IDLE
            appendLog("✅ 所有目标续火花完成！")
            handler.postDelayed({ hideWindow() }, 3000)
            return
        }
        val targetName = targetList[currentIndex]

        when (currentState) {
            State.FIND_FRIEND -> {
                appendLog("🔍 正在寻找好友: \$targetName")
                val targetNodes = root.findAccessibilityNodeInfosByText(targetName)
                if (targetNodes.isNotEmpty()) {
                    var node: AccessibilityNodeInfo? = targetNodes[0]
                    while (node != null && !node.isClickable) {
                        node = node.parent
                    }
                    if (node != null) {
                        node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        appendLog("👉 点击进入聊天界面")
                        currentState = State.CLICK_INPUT
                        return
                    }
                }
                
                val scrollableNodes = findScrollableNode(root)
                if (scrollableNodes != null) {
                    appendLog("🔄 正在下滑屏幕寻找...")
                    scrollableNodes.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                }
            }
            State.CLICK_INPUT -> {
                appendLog("✍️ 尝试输入 🔥")
                val editTexts = findEditText(root)
                if (editTexts != null) {
                    val arguments = Bundle()
                    arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, "🔥")
                    editTexts.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments)
                    currentState = State.CLICK_SEND
                } else {
                    val chatInput = root.findAccessibilityNodeInfosByText("发送消息...")
                    if (chatInput.isNotEmpty()) {
                        chatInput[0].parent?.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    }
                }
            }
            State.CLICK_SEND -> {
                appendLog("📤 点击发送按钮")
                val sendNodes = root.findAccessibilityNodeInfosByText("发送")
                for (node in sendNodes) {
                    if (node.isClickable || node.parent?.isClickable == true) {
                        val target = if (node.isClickable) node else node.parent
                        target.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        currentState = State.GO_BACK
                        return
                    }
                }
            }
            State.GO_BACK -> {
                appendLog("🔙 全局返回，准备下一个")
                performGlobalAction(GLOBAL_ACTION_BACK)
                currentIndex++
                currentState = State.FIND_FRIEND
            }
            else -> {}
        }
    }
    
    private fun findScrollableNode(root: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        if (root.isScrollable) return root
        for (i in 0 until root.childCount) {
            val child = root.getChild(i)
            if (child != null) {
                val res = findScrollableNode(child)
                if (res != null) return res
            }
        }
        return null
    }

    private fun findEditText(root: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        if (root.className?.contains("EditText") == true) return root
        for (i in 0 until root.childCount) {
            val child = root.getChild(i)
            if (child != null) {
                val res = findEditText(child)
                if (res != null) return res
            }
        }
        return null
    }
}
