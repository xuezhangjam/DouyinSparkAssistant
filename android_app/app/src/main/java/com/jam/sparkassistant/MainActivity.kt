
package com.jam.sparkassistant

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
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
        val btnAbout = findViewById<Button>(R.id.btnAbout)
        val tvStatus = findViewById<TextView>(R.id.tvStatus)

        val prefs = getSharedPreferences("spark_prefs", Context.MODE_PRIVATE)
        val savedFriends = prefs.getString("friends_list", "")
        val savedTime = prefs.getString("target_time", "")
        etFriends.setText(savedFriends)
        etTime.setText(savedTime)

        btnPermission.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
        
        btnAbout.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("关于火花助手 V4")
                .setMessage("本软件基于原生 Android 与无障碍服务开发，完全本地运行。\n" +
                            "V4 更新：\n" +
                            "1. 全面适配【多闪】(抖音聊天版) App，省去点击消息的步骤，极大提升稳定性。\n" +
                            "2. 新增实时悬浮调试日志窗口，方便开发者排查和迭代。\n\n" +
                            "开发支持：Google Antigravity")
                .setPositiveButton("知道啦", null)
                .show()
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
                Toast.makeText(this, "即将跳转多闪...", Toast.LENGTH_LONG).show()
                
                val launchIntent = packageManager.getLaunchIntentForPackage("my.maya.android")
                if (launchIntent != null) {
                    startActivity(launchIntent)
                } else {
                    Toast.makeText(this, "未找到多闪App！请确认是否已安装", Toast.LENGTH_LONG).show()
                }
            }
        }
        
        btnStop.setOnClickListener {
            DouyinAccessibilityService.isRunning = false
            DouyinAccessibilityService.isWaitingForTime = false
            DouyinAccessibilityService.hideFloatingWindow()
            tvStatus.text = "当前状态：已停止"
            Toast.makeText(this, "已停止所有自动化任务！", Toast.LENGTH_SHORT).show()
        }
    }
}
