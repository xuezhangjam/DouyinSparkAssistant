
package com.jam.sparkassistant

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import android.widget.LinearLayout
import android.widget.TextView
import android.view.Gravity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(50, 50, 50, 50)
        }
        
        val title = TextView(this).apply {
            text = "抖音自动续火花 (安卓版)"
            textSize = 24f
            setPadding(0, 0, 0, 50)
        }
        layout.addView(title)
        
        val btnAccess = Button(this).apply {
            text = "第一步：去开启无障碍权限"
            setOnClickListener {
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            }
        }
        layout.addView(btnAccess)
        
        val btnStart = Button(this).apply {
            text = "第二步：打开抖音开始运行"
            setPadding(0, 50, 0, 0)
            setOnClickListener {
                Toast.makeText(this@MainActivity, "请确保已开启无障碍权限，正在跳转抖音...", Toast.LENGTH_LONG).show()
                DouyinAccessibilityService.isRunning = true
                val launchIntent = packageManager.getLaunchIntentForPackage("com.ss.android.ugc.aweme")
                if (launchIntent != null) {
                    startActivity(launchIntent)
                } else {
                    Toast.makeText(this@MainActivity, "未找到抖音App！", Toast.LENGTH_SHORT).show()
                }
            }
        }
        layout.addView(btnStart)
        
        val btnStop = Button(this).apply {
            text = "停止自动运行"
            setPadding(0, 50, 0, 0)
            setOnClickListener {
                DouyinAccessibilityService.isRunning = false
                Toast.makeText(this@MainActivity, "已停止自动化！", Toast.LENGTH_SHORT).show()
            }
        }
        layout.addView(btnStop)
        
        setContentView(layout)
    }
}
