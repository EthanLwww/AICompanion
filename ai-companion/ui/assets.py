# 原版 CSS 视觉样式
CUSTOM_CSS = """
.gradio-container { max-width: 1100px !important; margin: auto !important; }
/* 整体背景 */
.gradio-container > .main { background: #f8fafc; }
.chat-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 20px; border-radius: 15px;
    text-align: center; margin-bottom: 15px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}
.chat-header h1 { margin: 0; font-size: 24px; }
.chat-header p { margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }
#chatbot { height: 400px !important; border-radius: 15px !important; }
#send-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important; border-radius: 10px !important; color: white !important;
}
/* 学习模式面板 */
.study-mode-panel {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-radius: 15px;
    padding: 15px;
    margin-bottom: 15px;
    border: 1px solid #bae6fd;
    box-shadow: 0 2px 8px rgba(14, 165, 233, 0.1);
}
.study-mode-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}
.study-mode-header h3 {
    margin: 0;
    color: #0369a1;
    font-size: 16px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
}
.camera-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s ease;
}
.camera-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}
.camera-btn.stop {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}
.emotion-status-grid {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}
.status-card {
    flex: 1;
    background: rgba(255,255,255,0.8);
    padding: 12px;
    border-radius: 10px;
    text-align: center;
    min-height: 60px;
    border: 1px solid rgba(14, 165, 233, 0.2);
}
.status-card p:first-child {
    margin: 0 0 5px 0;
    font-size: 12px;
    color: #6b7280;
}
.status-card p:last-child {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    min-height: 20px;
    line-height: 20px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
/* 休息按钮 */
.rest-btn {
    width: 100%;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    border: none;
    padding: 12px;
    border-radius: 10px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 15px;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}
.rest-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
}
.quick-btn { border-radius: 20px !important; font-size: 13px !important; margin: 3px !important; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes slideIn {
    from { transform: translateY(-100%); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}
@keyframes slideOut {
    from { transform: translateY(0); opacity: 1; }
    to { transform: translateY(-100%); opacity: 0; }
}
@keyframes achievementIn {
    from { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
    to { transform: translate(-50%, -50%) scale(1); opacity: 1; }
}
@keyframes achievementOut {
    from { transform: translate(-50%, -50%) scale(1); opacity: 1; }
    to { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
}
@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}
#alert-box {
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    padding: 15px 25px;
    border-radius: 12px;
    color: white;
    font-size: 15px;
    font-weight: 500;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    display: none;
    max-width: 90%;
    text-align: center;
}
/* 成就弹窗 */
#achievement-popup {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 10000;
    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
    padding: 30px 40px;
    border-radius: 20px;
    color: white;
    text-align: center;
    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    display: none;
    flex-direction: column;
    align-items: center;
}
#achievement-popup .achievement-icon { font-size: 48px; margin-bottom: 10px; }
#achievement-popup .achievement-title { font-size: 14px; opacity: 0.9; margin-bottom: 5px; }
#achievement-popup .achievement-name { font-size: 20px; font-weight: bold; margin-bottom: 5px; }
#achievement-popup .achievement-desc { font-size: 14px; opacity: 0.9; }
/* 用户状态栏 */
.user-stats-bar {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    padding: 15px;
    color: white;
    margin-bottom: 15px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}
.stats-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}
.stats-row:last-child { margin-bottom: 0; }
.stat-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
}
.stat-value { font-weight: bold; font-size: 15px; }
.level-progress-container {
    background: rgba(255,255,255,0.25);
    border-radius: 10px;
    height: 10px;
    overflow: hidden;
    margin-top: 8px;
}
.level-progress-bar {
    background: linear-gradient(90deg, #fbbf24, #f59e0b);
    height: 100%;
    border-radius: 10px;
    transition: width 0.5s ease;
    box-shadow: 0 0 10px rgba(251, 191, 36, 0.5);
}
/* 成就面板 */
.achievements-panel {
    background: #ffffff;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 15px;
    border: 2px solid #f59e0b;
    box-shadow: 0 2px 8px rgba(251, 191, 36, 0.2);
}
.achievements-panel h4 {
    margin: 0 0 12px 0;
    font-size: 15px;
    color: #111827;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
}
#achievements-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.achievement-item {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 10px;
    border-radius: 20px;
    font-size: 12px;
    background: #f3f4f6;
    color: #374151;
    cursor: default;
    border: 1px solid #9ca3af;
    transition: all 0.2s ease;
}
.achievement-item:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.achievement-item.unlocked {
    background: #fef3c7;
    color: #78350f;
    border-color: #f59e0b;
    box-shadow: 0 2px 6px rgba(251, 146, 60, 0.3);
    font-weight: 700;
}
.achievement-icon { font-size: 14px; }
.achievement-name { font-size: 12px; font-weight: 600; color: #1f2937; }
/* 签到日历 */
.checkin-panel {
    background: #ffffff;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 15px;
    border: 2px solid #10b981;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
}
.checkin-panel h4 {
    margin: 0 0 12px 0;
    font-size: 15px;
    color: #111827;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
}
.calendar-header {
    text-align: center;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 10px;
    color: #111827;
    background: #ecfdf5;
    padding: 8px;
    border-radius: 8px;
    border: 1px solid #a7f3d0;
}
.calendar-weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 2px;
    margin-bottom: 6px;
}
.calendar-weekdays span {
    text-align: center;
    font-size: 11px;
    color: #059669;
    font-weight: 700;
    padding: 4px 0;
}
.calendar-days {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
}
.calendar-days span {
    text-align: center;
    padding: 6px 2px;
    font-size: 12px;
    border-radius: 6px;
    color: #111827;
    background: #f3f4f6;
    font-weight: 700;
    border: 1px solid #e5e7eb;
}
.calendar-days span.empty { 
    visibility: hidden; 
    background: transparent;
    border: none;
}
.calendar-days span.checked {
    background: #059669;
    color: #ffffff;
    border-color: #047857;
    box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
}
.calendar-days span.today {
    border: 2px solid #6366f1;
    background: #eef2ff;
    color: #4338ca;
}
/* 快捷操作样式 */
.quick-actions-panel {
    background: #ffffff;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 15px;
    border: 2px solid #8b5cf6;
    box-shadow: 0 2px 8px rgba(139, 92, 246, 0.2);
}
.quick-actions-panel h4 {
    margin: 0 0 12px 0;
    font-size: 15px;
    color: #111827;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
}
.quick-actions-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}
.quick-action-btn {
    background: #f3f4f6;
    border: 2px solid #8b5cf6;
    border-radius: 10px;
    padding: 12px 10px;
    font-size: 13px;
    font-weight: 600;
    color: #4c1d95;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}
.quick-action-btn:hover {
    background: #8b5cf6;
    color: #ffffff;
    border-color: #7c3aed;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}
.quick-action-btn.danger {
    color: #991b1b;
    border-color: #ef4444;
    background: #fef2f2;
}
.quick-action-btn.danger:hover {
    background: #ef4444;
    color: #ffffff;
}
/* 隐藏组件样式 */
.hidden-component {
    display: none !important;
}
"""

# 原版 HTML 基础结构（全局弹窗和提醒框）
CUSTOM_HTML = """
<!-- 提醒消息框 -->
<div id="alert-box">
    <span id="alert-text"></span>
</div>

<!-- 成就解锁弹窗 -->
<div id="achievement-popup">
    <div class="achievement-title">🎉 成就解锁！</div>
    <div id="achievement-icon" class="achievement-icon"></div>
    <div id="achievement-name" class="achievement-name"></div>
    <div id="achievement-desc" class="achievement-desc"></div>
</div>
"""

# 顶部紫色渐变 Banner
HEADER_HTML = """
<div class="chat-header">
    <h1>学习陪伴AI - 学了么</h1>
    <p>有我陪伴，学习不孤单 | 支持实时人脸识别与情绪检测</p>
</div>
"""

# 用户状态卡片（左侧栏顶部）
USER_STATS_HTML = """
<div class="user-stats-bar">
    <div class="stats-row">
        <div class="stat-item">
            <span id="user-level" style="font-size: 20px;">🌱</span>
            <span id="user-level-name" class="stat-value">Lv.1 学习新手</span>
        </div>
        <div class="stat-item">
            <span style="font-size: 16px;">💰</span>
            <span id="user-points" class="stat-value">0</span>
            <span style="opacity: 0.8;">积分</span>
        </div>
    </div>
    <div class="stats-row">
        <div class="stat-item">
            <span style="font-size: 16px;">🔥</span>
            <span style="opacity: 0.8;">连续签到</span>
            <span id="user-streak" class="stat-value">0</span>
            <span style="opacity: 0.8;">天</span>
        </div>
        <div class="stat-item">
            <span id="level-progress-text" style="font-size: 12px; opacity: 0.9; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 10px;">0/100</span>
        </div>
    </div>
    <div class="level-progress-container">
        <div id="level-progress" class="level-progress-bar" style="width: 0%;"></div>
    </div>
</div>
"""

# 学习中心（摄像头 + 休息按钮）
STUDY_CENTER_HTML = """
<div class="study-mode-panel">
    <div class="study-mode-header">
        <h3 style="margin:0; font-size:16px; color:#0369a1;">📹 专注监测</h3>
        <div style="display:flex; gap:5px;">
            <button id="start-btn" type="button" class="camera-btn">开启</button>
            <button id="stop-btn" type="button" class="camera-btn stop" style="display: none;">关闭</button>
        </div>
    </div>
    <div id="video-container" style="position: relative; width: 100%; max-width: 320px; margin: 0 auto; display: none; min-height: 180px;"></div>
    <div id="camera-placeholder" style="width: 100%; max-width: 320px; height: 160px; margin: 0 auto; background: rgba(255,255,255,0.6); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #64748b; border: 2px dashed #cbd5e1;">
        <p style="margin: 0; font-size: 12px; opacity: 0.7;">点击"开启"进入专注模式</p>
    </div>
    <div id="loading-indicator" style="display: none; text-align: center; padding: 15px; color: #6366f1;">
        <div style="display: inline-block; width: 24px; height: 24px; border: 3px solid #e5e7eb; border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <p style="margin: 5px 0 0 0; font-size: 12px;">载入模型...</p>
    </div>
    <div class="emotion-status-grid">
        <div class="status-card"><p>情绪</p><p id="emotion-display">---</p></div>
        <div class="status-card"><p>状态</p><p id="attention-display">就绪</p></div>
    </div>
</div>

<div id="rest-panel" style="display: none; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 15px; padding: 15px; margin-bottom: 10px; color: white;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <h3 style="margin: 0; font-size: 15px;">☕ 休息中</h3>
        <button id="cancel-rest-btn" type="button" style="background: rgba(255,255,255,0.2); color: white; border: none; padding: 3px 8px; border-radius: 6px; cursor: pointer; font-size: 11px;">返回</button>
    </div>
    <div id="rest-options">
        <div style="display: flex; gap: 6px; margin-bottom: 8px;">
            <button id="rest-5" type="button" style="flex:1; background:rgba(255,255,255,0.2); border:none; padding:8px; border-radius:6px; color:white;">5m</button>
            <button id="rest-10" type="button" style="flex:1; background:rgba(255,255,255,0.2); border:none; padding:8px; border-radius:6px; color:white;">10m</button>
            <button id="rest-15" type="button" style="flex:1; background:rgba(255,255,255,0.2); border:none; padding:8px; border-radius:6px; color:white;">15m</button>
        </div>
        <button id="rest-custom" type="button" style="width:100%; background:rgba(255,255,255,0.15); border:none; padding:6px; border-radius:6px; color:white; font-size:12px;">⏰ 自定义</button>
        <div id="custom-time-input" style="display: none; margin-top: 10px; align-items: center; gap: 6px;">
            <input id="custom-minutes" type="number" min="1" max="60" value="20" style="flex: 1; padding: 6px; border-radius: 4px; border: none; text-align: center;">
            <button id="start-custom-rest" type="button" style="background: white; color: #059669; border: none; padding: 6px 12px; border-radius: 4px; font-weight: 600;">开始</button>
        </div>
    </div>
    <div id="rest-countdown" style="display: none; text-align: center;">
        <p id="countdown-display" style="margin: 0 0 10px 0; font-size: 36px; font-weight: bold; font-family: monospace;">00:00</p>
        <button id="stop-rest-btn" type="button" style="background: white; color: #059669; border: none; padding: 8px 20px; border-radius: 6px; font-weight: 600;">提前结束</button>
    </div>
</div>
<button id="rest-mode-btn" type="button" class="rest-btn" style="margin-bottom: 10px;">☕ 休息一下</button>
"""

# 成就与签到面板
ACHIEVEMENTS_HTML = """
<h4 style="margin:10px 0 8px 0; font-size:14px; color:#059669; font-weight:700;">📅 签到日历</h4>
<div id="checkin-calendar" style="margin-bottom:15px; min-height:160px; background: rgba(255,255,255,0.5); border-radius: 8px;"></div>
<h4 style="margin:10px 0 8px 0; font-size:14px; color:#b45309; font-weight:700;">🏆 我的成就</h4>
<div id="achievements-container" style="min-height:80px; background: rgba(255,255,255,0.5); border-radius: 8px;"></div>
"""

# 学习报告按钮
REPORT_BUTTON_HTML = """
<button id="show-report-btn" type="button" style="width:100%; background:linear-gradient(135deg,#3b82f6 0%,#1d4ed8 100%); color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-size:14px; font-weight:600; margin-top:10px; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);">
    📊 查看学习报告
</button>
"""

# 学习数据概览面板
DATA_DASHBOARD_HTML = """
<div id="stats-dashboard" style="background:#ffffff; padding:10px;">
    <h4 style="margin:0 0 15px 0; font-size:15px; color:#1e40af; font-weight:700; display:flex; align-items:center; gap:8px;">
        📊 实时数据统计
        <span id="dashboard-date" style="font-size:12px; color:#6b7280; font-weight:500; margin-left:auto;"></span>
    </h4>
    <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:15px;">
        <div style="background:#eff6ff; border-radius:10px; padding:10px; text-align:center;">
            <p style="margin:0 0 5px 0; font-size:11px; color:#3b82f6; font-weight:600;">今日</p>
            <p id="today-minutes" style="margin:0; font-size:18px; font-weight:700; color:#1e40af;">0</p>
        </div>
        <div style="background:#f0fdf4; border-radius:10px; padding:10px; text-align:center;">
            <p style="margin:0 0 5px 0; font-size:11px; color:#16a34a; font-weight:600;">本周</p>
            <p id="week-minutes" style="margin:0; font-size:18px; font-weight:700; color:#15803d;">0</p>
        </div>
        <div style="background:#fef3c7; border-radius:10px; padding:10px; text-align:center;">
            <p style="margin:0 0 5px 0; font-size:11px; color:#d97706; font-weight:600;">本月</p>
            <p id="month-minutes" style="margin:0; font-size:18px; font-weight:700; color:#b45309;">0</p>
        </div>
    </div>
    <div style="margin-bottom:15px;">
        <p style="margin:0 0 8px 0; font-size:12px; color:#374151; font-weight:600;">📈 专注度趋势</p>
        <div id="week-chart" style="display:flex; align-items:flex-end; justify-content:space-between; height:60px; padding:5px 0; background:#f9fafb; border-radius:8px; overflow:hidden;"></div>
    </div>
    <div>
        <p style="margin:0 0 8px 0; font-size:12px; color:#374151; font-weight:600;">🎯 今日专注度: <span id="focus-text">0%</span></p>
        <div style="background:#e5e7eb; border-radius:10px; height:12px; overflow:hidden;">
            <div id="focus-bar" style="background:linear-gradient(90deg,#10b981,#059669); height:100%; width:0%; transition:width 0.5s;"></div>
        </div>
    </div>
    <div id="best-hours" style="display:none;"></div>
</div>
"""

# 周报弹窗
WEEKLY_REPORT_MODAL_HTML = """
<div id="weekly-report-modal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:10001; align-items:center; justify-content:center;">
    <div style="background:white; border-radius:16px; padding:25px; max-width:500px; width:90%; max-height:80vh; overflow-y:auto;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3 style="margin:0; font-size:18px; font-weight:700;">📋 学习周报</h3>
            <button id="close-report-btn" type="button" style="background:none; border:none; font-size:24px; cursor:pointer;">×</button>
        </div>
        <div id="report-content">正在生成报告...</div>
    </div>
</div>
"""

# ========== 抽卡系统 UI 组件 (步顤4) ==========

# 抽卡面板 HTML
GACHA_PANEL_HTML = """
<div style="padding:10px 0;">
    <!-- 抽卡介绍 -->
    <div style="background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:12px;padding:15px;margin-bottom:15px;text-align:center;">
        <p style="margin:0 0 8px 0;font-size:14px;color:#92400e;font-weight:600;">🎁 消耗积分抽取稀有道具！</p>
        <div style="display:flex;justify-content:center;gap:8px;font-size:12px;">
            <span style="padding:3px 8px;background:rgba(255,255,255,0.6);border-radius:10px;color:#6b7280;">普通</span>
            <span style="padding:3px 8px;background:rgba(59,130,246,0.2);border-radius:10px;color:#3b82f6;">稀有</span>
            <span style="padding:3px 8px;background:rgba(139,92,246,0.2);border-radius:10px;color:#8b5cf6;">超稀</span>
            <span style="padding:3px 8px;background:rgba(245,158,11,0.3);border-radius:10px;color:#d97706;">传说</span>
        </div>
    </div>
    
    <!-- 积分显示 -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;padding:12px 15px;background:#f0f9ff;border-radius:10px;border:1px solid #bae6fd;">
        <span style="font-size:13px;color:#0369a1;font-weight:600;">💰 可用积分</span>
        <div style="display:flex;align-items:center;gap:10px;">
            <span id="gacha-points-display" style="font-size:16px;color:#0c4a6e;font-weight:700;">0 积分</span>
            <!-- 调试开关：快速增加积分 -->
            <button id="debug-add-points" type="button" 
                style="padding:2px 6px;background:#fee2e2;color:#b91c1c;border:1px solid #fecaca;border-radius:4px;font-size:10px;cursor:pointer;opacity:0.6;"
                onmouseover="this.style.opacity='1'"
                onmouseout="this.style.opacity='0.6'">
                +1000
            </button>
        </div>
    </div>
    
    <!-- 抽卡按钮 -->
    <button id="gacha-btn" type="button" 
        style="width:100%;padding:15px;background:linear-gradient(135deg,#f59e0b,#d97706);color:white;border:none;border-radius:12px;font-size:16px;font-weight:700;cursor:pointer;box-shadow:0 4px 15px rgba(245,158,11,0.4);transition:all 0.3s ease;"
        onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(245,158,11,0.5)';"
        onmouseout="this.style.transform='none';this.style.boxShadow='0 4px 15px rgba(245,158,11,0.4);'">
        🎲 抽卡一次 (20积分)
    </button>
    
    <!-- 抽卡记录 -->
    <div style="margin-top:15px;">
        <p style="margin:0 0 8px 0;font-size:12px;color:#6b7280;">最近抽卡记录：</p>
        <div id="gacha-history" style="display:flex;gap:5px;flex-wrap:wrap;min-height:30px;">
            <span style="color:#9ca3af;font-size:11px;">暂无记录</span>
        </div>
    </div>
</div>
"""

# 背包面板 HTML
INVENTORY_PANEL_HTML = """
<div style="padding:10px 0;">
    <!-- 背包物品容器 -->
    <div id="inventory-container" style="min-height:100px;">
        <div style="text-align:center;padding:30px;color:#9ca3af;">
            <p style="font-size:24px;margin:0 0 10px 0;">📦</p>
            <p style="margin:0;">背包空空如也，快去抽卡吧！</p>
        </div>
    </div>
</div>
"""
