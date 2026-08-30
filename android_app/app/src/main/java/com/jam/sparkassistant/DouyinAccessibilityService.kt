
package com.jam.sparkassistant

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.os.Handler
import android.os.Looper

class DouyinAccessibilityService : AccessibilityService() {
    
    companion object {
        var isRunning = false
    }
    
    private var lastActionTime = 0L
    private val handler = Handler(Looper.getMainLooper())

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (!isRunning || event == null) return
        
        val root = rootInActiveWindow ?: return
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastActionTime < 2000) return // Throttling
        
        // Very basic logic: if we see "发消息", click it
        val nodes = root.findAccessibilityNodeInfosByText("发消息")
        for (node in nodes) {
            if (node.isClickable) {
                node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                lastActionTime = System.currentTimeMillis()
                return
            } else if (node.parent?.isClickable == true) {
                node.parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                lastActionTime = System.currentTimeMillis()
                return
            }
        }
        
        // If we see "表情", click it
        val emojiNodes = root.findAccessibilityNodeInfosByText("表情")
        for (node in emojiNodes) {
             if (node.isClickable) {
                node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                lastActionTime = System.currentTimeMillis()
                return
            }
        }
    }

    override fun onInterrupt() {}
}
