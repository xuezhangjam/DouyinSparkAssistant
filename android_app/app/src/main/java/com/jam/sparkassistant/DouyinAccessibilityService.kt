
package com.jam.sparkassistant

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class DouyinAccessibilityService : AccessibilityService() {
    
    enum class State {
        IDLE, CLICK_TAB, FIND_FRIEND, CLICK_INPUT, CLICK_SEND, GO_BACK
    }
    
    companion object {
        var isRunning = false
        var isWaitingForTime = false
        var targetTime = ""
        var targetList: List<String> = emptyList()
        var currentIndex = 0
        var currentState = State.IDLE
        
        private var instance: DouyinAccessibilityService? = null
        
        fun startExecution() {
            currentIndex = 0
            currentState = State.CLICK_TAB
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
                    
                    val launchIntent = packageManager.getLaunchIntentForPackage("com.ss.android.ugc.aweme")
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
        Toast.makeText(this, "火花助手无障碍服务已连接", Toast.LENGTH_SHORT).show()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}

    override fun onInterrupt() {}

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        handler.removeCallbacks(pollRunnable)
    }

    private fun processState() {
        val root = rootInActiveWindow ?: return
        if (currentIndex >= targetList.size) {
            isRunning = false
            currentState = State.IDLE
            handler.post { Toast.makeText(this, "🎉 所有目标续火花完成！", Toast.LENGTH_LONG).show() }
            return
        }
        val targetName = targetList[currentIndex]

        when (currentState) {
            State.CLICK_TAB -> {
                val nodes = root.findAccessibilityNodeInfosByText("消息")
                for (node in nodes) {
                    if (node.isClickable || node.parent?.isClickable == true) {
                        val target = if (node.isClickable) node else node.parent
                        target.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        currentState = State.FIND_FRIEND
                        return
                    }
                }
            }
            State.FIND_FRIEND -> {
                val targetNodes = root.findAccessibilityNodeInfosByText(targetName)
                if (targetNodes.isNotEmpty()) {
                    var node: AccessibilityNodeInfo? = targetNodes[0]
                    while (node != null && !node.isClickable) {
                        node = node.parent
                    }
                    if (node != null) {
                        node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        currentState = State.CLICK_INPUT
                        return
                    }
                }
                
                val scrollableNodes = findScrollableNode(root)
                if (scrollableNodes != null) {
                    scrollableNodes.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                }
            }
            State.CLICK_INPUT -> {
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
