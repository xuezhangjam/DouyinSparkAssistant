
package com.jam.sparkassistant

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.textfield.TextInputEditText

class MainActivity : AppCompatActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val etFriends = findViewById<TextInputEditText>(R.id.etFriends)
        val etTime = findViewById<TextInputEditText>(R.id.etTime)
        val btnPermission = findViewById<Button>(R.id.btnPermission)
        val btnStart = findViewById<Button>(R.id.btnStart)
        val btnStop = findViewById<Button>(R.id.btnStop)
        val tvStatus = findViewById<TextView>(R.id.tvStatus)

        val prefs = getSharedPreferences("spark_prefs", Context.MODE_PRIVATE)
        val savedFriends = prefs.getString("friends_list", "")
        val savedTime = prefs.getString("target_time", "")
        etFriends.setText(savedFriends)
        etTime.setText(savedTime)

        btnPermission.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }

        btnStart.setOnClickListener {
            val text = etFriends.text.toString()
            val time = etTime.text.toString().trim()
            prefs.edit().putString("friends_list", text).putString("target_time", time).apply()
            
            val list = text.split(Regex("[,\n]+")).map { it.trim() }.filter { it.isNotEmpty() }
            if (list.isEmpty()) {
                Toast.makeText(this, "名单不能为空！", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            
            DouyinAccessibilityService.targetList = list
            
            if (time.isNotEmpty()) {
                DouyinAccessibilityService.targetTime = time
                DouyinAccessibilityService.isWaitingForTime = true
                tvStatus.text = "当前状态：等待定时执行 (" + time + ")，共 " + list.size + " 个目标"
                Toast.makeText(this, "定时任务已开启，请保持后台运行", Toast.LENGTH_LONG).show()
            } else {
                DouyinAccessibilityService.isWaitingForTime = false
                DouyinAccessibilityService.isRunning = true
                DouyinAccessibilityService.startExecution()
                
                tvStatus.text = "当前状态：正在运行，共 " + list.size + " 个目标"
                Toast.makeText(this, "即将跳转抖音...", Toast.LENGTH_LONG).show()
                
                val launchIntent = packageManager.getLaunchIntentForPackage("com.ss.android.ugc.aweme")
                if (launchIntent != null) {
                    startActivity(launchIntent)
                } else {
                    Toast.makeText(this, "未找到抖音App！请确认是否已安装", Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        btnStop.setOnClickListener {
            DouyinAccessibilityService.isRunning = false
            DouyinAccessibilityService.isWaitingForTime = false
            tvStatus.text = "当前状态：已停止"
            Toast.makeText(this, "已停止所有自动化任务！", Toast.LENGTH_SHORT).show()
        }
    }
}
