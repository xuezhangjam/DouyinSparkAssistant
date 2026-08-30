
package com.jam.sparkassistant

import android.accessibilityservice.AccessibilityService
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Toast

class DouyinAccessibilityService : AccessibilityService() {
    
    enum class State {
        IDLE, CLICK_TAB, FIND_FRIEND, CLICK_INPUT, CLICK_SEND, GO_BACK
    }
    
    companion object {
        var isRunning = false
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
            if (isRunning) {
                processState()
            }
            handler.postDelayed(this, 1500) // Poll every 1.5 seconds
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
            handler.post { Toast.makeText(this, "所有续火花任务完成！", Toast.LENGTH_LONG).show() }
            return
        }
        val targetName = targetList[currentIndex]

        when (currentState) {
            State.CLICK_TAB -> {
                val nodes = root.findAccessibilityNodeInfosByText("消息")
                for (node in nodes) {
                    if (node.isClickable) {
                        node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        currentState = State.FIND_FRIEND
                        return
                    } else if (node.parent?.isClickable == true) {
                        node.parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        currentState = State.FIND_FRIEND
                        return
                    }
                }
            }
            State.FIND_FRIEND -> {
                val targetNodes = root.findAccessibilityNodeInfosByText(targetName)
                if (targetNodes.isNotEmpty()) {
                    val node = targetNodes[0]
                    var clickableParent = node
                    while (clickableParent != null && !clickableParent.isClickable) {
                        clickableParent = clickableParent.parent
                    }
                    if (clickableParent != null) {
                        clickableParent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        currentState = State.CLICK_INPUT
                        return
                    }
                }
                
                // If not found, try to scroll down. 
                // We find a RecyclerView or ListView and scroll it.
                val scrollableNodes = findScrollableNode(root)
                if (scrollableNodes != null) {
                    scrollableNodes.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                }
            }
            State.CLICK_INPUT -> {
                // Find EditText to input emoji
                val editTexts = findEditText(root)
                if (editTexts != null) {
                    val arguments = Bundle()
                    arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, "🔥")
                    editTexts.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments)
                    currentState = State.CLICK_SEND
                } else {
                    // Sometimes we need to click the bottom bar to show input
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
