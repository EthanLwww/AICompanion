"""
学习陪伴AI - 魔搭创空间版本
使用Gradio原生组件 + 前端JS实现实时人脸识别
优化版：预加载模型 + 调整检测频率 + 流式响应
"""

import gradio as gr
import requests
import os
import json
import time

# 魔搭社区API配置
MODELSCOPE_API_KEY = os.environ.get("MODELSCOPE_API_KEY", "ms-b1bc1697-2446-4e33-8f45-2999b9c83471")
MODELSCOPE_API_URL = "https://api-inference.modelscope.cn/v1/chat/completions"

# 系统提示词
SYSTEM_PROMPT = """你是一个温暖、有耐心的学习陪伴AI助手，名叫"小伴"。你的职责是：
1. 帮助用户解答学习中的各种问题
2. 当用户感到沮丧或疲惫时，给予鼓励和安慰
3. 当用户注意力不集中时，温和地提醒并给出建议
4. 提供学习方法和时间管理建议
5. 保持积极、友好的态度，像朋友一样陪伴用户

请用简洁、温暖的语言回复，适当使用一些语气词让对话更自然。"""

# 存储对话历史
conversation_history = []

def call_ai_api_stream(messages):
    """流式调用魔搭API"""
    try:
        response = requests.post(
            MODELSCOPE_API_URL,
            headers={"Authorization": f"Bearer {MODELSCOPE_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "Qwen/Qwen2.5-72B-Instruct", 
                "messages": messages, 
                "temperature": 0.7, 
                "max_tokens": 1000,
                "stream": True  # 开启流式输出
            },
            timeout=60,
            stream=True  # 重要：启用流式接收
        )
        
        if response.status_code == 200:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    # 处理流式数据格式
                    if line.startswith('data: '):
                        data = line[6:]
                        if data != '[DONE]':
                            try:
                                chunk = json.loads(data)
                                if chunk.get('choices') and chunk['choices'][0].get('delta'):
                                    content = chunk['choices'][0]['delta'].get('content', '')
                                    if content:
                                        full_response += content
                                        yield content  # 流式返回每个片段
                            except json.JSONDecodeError:
                                continue
            return full_response
        else:
            yield f"API请求失败: {response.status_code}"
    except Exception as e:
        yield f"请求出错: {str(e)}"

def chat(message, history):
    """处理聊天消息 - 流式版本"""
    global conversation_history
    
    if not message.strip():
        return history, ""
    
    # 添加用户消息到历史
    conversation_history.append({"role": "user", "content": message})
    
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    # 构建消息列表
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history
    
    # 初始化AI消息
    ai_message = ""
    
    # 逐步获取流式响应
    for chunk in call_ai_api_stream(messages):
        ai_message += chunk
        # 更新聊天历史（流式显示）
        current_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": ai_message + "▌"}  # 添加打字光标
        ]
        yield current_history, ""
    
    # 移除光标，显示完整消息
    final_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": ai_message}
    ]
    
    # 保存完整消息到对话历史
    conversation_history.append({"role": "assistant", "content": ai_message})
    
    yield final_history, ""

def clear_history():
    """清空对话历史"""
    global conversation_history
    conversation_history = []
    return [], ""

# 初始消息
INITIAL_MESSAGES = [
    {"role": "assistant", "content": "你好呀！我是小伴，你的学习陪伴AI助手~\n\n有什么问题都可以问我，学习累了也可以和我聊聊天。\n\n点击左侧的\"开启摄像头\"按钮，我还能通过人脸识别实时关注你的学习状态哦！"}
]

# 优化后的JavaScript代码 - 包含预加载和调整频率
LOAD_JS = """
async () => {
    console.log('Gradio load JS executing...');
    
    // 初始化全局变量
    window.isRunning = false;
    window.modelsLoaded = false;
    window.noFaceCount = 0;
    window.webcamStream = null;
    window.detectionInterval = null;
    window.emotionHistory = [];
    window.useSsdModel = false;
    
    // 新增：分神和消极情绪计数器
    window.distractedCount = 0;
    window.negativeEmotionCount = 0;
    window.lastAlertTime = 0;
    window.alertCooldown = 30000;
    
    // ========== 游戏化系统 ==========
    const STORAGE_KEY = 'studyCompanionData';
    
    const defaultUserData = {
        points: 0,
        level: 1,
        totalStudyMinutes: 0,
        todayStudyMinutes: 0,
        consecutiveDays: 0,
        lastCheckInDate: null,
        checkInHistory: [],
        achievements: [],
        positiveEmotionMinutes: 0,
        earlyEndRestCount: 0,
        firstStudyDate: null,
        lastStudyDate: null
    };
    
    // 等级配置
    const levelConfig = [
        { level: 1, name: '学习新手', minPoints: 0, icon: '🌱' },
        { level: 2, name: '初级学者', minPoints: 100, icon: '🌿' },
        { level: 3, name: '勤奋学徒', minPoints: 300, icon: '🌳' },
        { level: 4, name: '专注达人', minPoints: 600, icon: '⭐' },
        { level: 5, name: '学习能手', minPoints: 1000, icon: '🌟' },
        { level: 6, name: '知识探索者', minPoints: 1500, icon: '💫' },
        { level: 7, name: '学霸预备', minPoints: 2200, icon: '🔥' },
        { level: 8, name: '学习大师', minPoints: 3000, icon: '👑' },
        { level: 9, name: '知识王者', minPoints: 4000, icon: '💎' },
        { level: 10, name: '传奇学神', minPoints: 5500, icon: '🏆' }
    ];
    
    // 成就配置
    const achievementConfig = [
        { id: 'first_study', name: '初次启程', desc: '首次开启学习模式', icon: '🎯', check: (d) => d.totalStudyMinutes > 0 },
        { id: 'study_30min', name: '专注新手', desc: '累计学习30分钟', icon: '⏱️', check: (d) => d.totalStudyMinutes >= 30 },
        { id: 'study_1hour', name: '一小时挑战', desc: '累计学习1小时', icon: '🕐', check: (d) => d.totalStudyMinutes >= 60 },
        { id: 'study_5hours', name: '专注达人', desc: '累计学习5小时', icon: '🎖️', check: (d) => d.totalStudyMinutes >= 300 },
        { id: 'study_10hours', name: '学习能手', desc: '累计学习10小时', icon: '🏅', check: (d) => d.totalStudyMinutes >= 600 },
        { id: 'study_24hours', name: '一天一夜', desc: '累计学习24小时', icon: '🌙', check: (d) => d.totalStudyMinutes >= 1440 },
        { id: 'checkin_3days', name: '三日坚持', desc: '连续签到3天', icon: '📅', check: (d) => d.consecutiveDays >= 3 },
        { id: 'checkin_7days', name: '一周达人', desc: '连续签到7天', icon: '🗓️', check: (d) => d.consecutiveDays >= 7 },
        { id: 'checkin_14days', name: '半月坚守', desc: '连续签到14天', icon: '📆', check: (d) => d.consecutiveDays >= 14 },
        { id: 'checkin_30days', name: '月度之星', desc: '连续签到30天', icon: '🌟', check: (d) => d.consecutiveDays >= 30 },
        { id: 'early_rest_5', name: '自律新秀', desc: '主动结束休息5次', icon: '💪', check: (d) => d.earlyEndRestCount >= 5 },
        { id: 'early_rest_20', name: '自律王者', desc: '主动结束休息20次', icon: '👊', check: (d) => d.earlyEndRestCount >= 20 },
        { id: 'level_5', name: '小有成就', desc: '达到5级', icon: '🎯', check: (d) => d.level >= 5 },
        { id: 'level_10', name: '登峰造极', desc: '达到10级', icon: '🏆', check: (d) => d.level >= 10 },
        { id: 'points_1000', name: '千分成就', desc: '累计获得1000积分', icon: '💰', check: (d) => d.points >= 1000 },
        { id: 'points_5000', name: '积分大户', desc: '累计获得5000积分', icon: '💎', check: (d) => d.points >= 5000 }
    ];
    
    // 加载用户数据
    function loadUserData() {
        try {
            const data = localStorage.getItem(STORAGE_KEY);
            if (data) {
                const parsed = JSON.parse(data);
                return { ...defaultUserData, ...parsed };
            }
        } catch (e) {
            console.error('Load user data error:', e);
        }
        return { ...defaultUserData };
    }
    
    // 保存用户数据
    function saveUserData(data) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } catch (e) {
            console.error('Save user data error:', e);
        }
    }
    
    // 获取今日日期字符串
    function getTodayStr() {
        return new Date().toISOString().split('T')[0];
    }
    
    // 计算等级
    function calculateLevel(points) {
        for (let i = levelConfig.length - 1; i >= 0; i--) {
            if (points >= levelConfig[i].minPoints) {
                return levelConfig[i];
            }
        }
        return levelConfig[0];
    }
    
    // 获取下一级所需积分
    function getNextLevelPoints(currentLevel) {
        const nextLevel = levelConfig.find(l => l.level === currentLevel + 1);
        return nextLevel ? nextLevel.minPoints : null;
    }
    
    // 检查并解锁成就
    function checkAchievements(userData) {
        const newAchievements = [];
        achievementConfig.forEach(achievement => {
            if (!userData.achievements.includes(achievement.id) && achievement.check(userData)) {
                userData.achievements.push(achievement.id);
                newAchievements.push(achievement);
            }
        });
        return newAchievements;
    }
    
    // 处理每日签到
    function handleCheckIn(userData) {
        const today = getTodayStr();
        
        if (userData.lastCheckInDate !== today) {
            userData.todayStudyMinutes = 0;
        }
        
        if (userData.lastCheckInDate === today) {
            return { isNew: false, bonus: 0 };
        }
        
        if (userData.lastCheckInDate) {
            const lastDate = new Date(userData.lastCheckInDate);
            const todayDate = new Date(today);
            const diffDays = Math.floor((todayDate - lastDate) / (1000 * 60 * 60 * 24));
            
            if (diffDays === 1) {
                userData.consecutiveDays++;
            } else {
                userData.consecutiveDays = 1;
            }
        } else {
            userData.consecutiveDays = 1;
        }
        
        userData.lastCheckInDate = today;
        
        if (!userData.checkInHistory.includes(today)) {
            userData.checkInHistory.push(today);
            if (userData.checkInHistory.length > 30) {
                userData.checkInHistory.shift();
            }
        }
        
        const bonus = Math.min(10 + userData.consecutiveDays * 2, 50);
        userData.points += bonus;
        
        return { isNew: true, bonus: bonus };
    }
    
    // 添加积分
    function addPoints(userData, amount, reason) {
        userData.points += amount;
        const levelInfo = calculateLevel(userData.points);
        const oldLevel = userData.level;
        userData.level = levelInfo.level;
        
        const leveledUp = levelInfo.level > oldLevel;
        
        return { leveledUp, newLevel: levelInfo };
    }
    
    // 初始化用户数据
    window.userData = loadUserData();
    
    // 学习计时器
    window.studyPointsInterval = null;
    window.positiveEmotionTime = 0;
    
    function startStudyPointsTimer() {
        if (window.studyPointsInterval) return;
        
        window.studyPointsInterval = setInterval(() => {
            if (window.isRunning && !window.isResting) {
                window.userData.totalStudyMinutes++;
                window.userData.todayStudyMinutes++;
                
                let pointsToAdd = 1;
                
                if (window.userData.todayStudyMinutes % 30 === 0) {
                    pointsToAdd += 10;
                    showAlert('连续专注30分钟，额外获得10积分！', 'encourage');
                    playAlertSound('levelup');
                }
                
                const result = addPoints(window.userData, pointsToAdd, 'study');
                
                if (result.leveledUp) {
                    showAlert('恭喜升级！你现在是 ' + result.newLevel.icon + ' ' + result.newLevel.name + ' 了！', 'encourage');
                    playAlertSound('levelup');
                }
                
                const newAchievements = checkAchievements(window.userData);
                newAchievements.forEach(achievement => {
                    setTimeout(() => {
                        showAchievementPopup(achievement);
                    }, 1000);
                });
                
                saveUserData(window.userData);
                updateStatsDisplay();
            }
        }, 60000);
    }
    
    function stopStudyPointsTimer() {
        if (window.studyPointsInterval) {
            clearInterval(window.studyPointsInterval);
            window.studyPointsInterval = null;
        }
    }
    
    // 显示成就弹窗
    function showAchievementPopup(achievement) {
        playAlertSound('achievement');
        
        const popup = document.getElementById('achievement-popup');
        const icon = document.getElementById('achievement-icon');
        const name = document.getElementById('achievement-name');
        const desc = document.getElementById('achievement-desc');
        
        if (popup && icon && name && desc) {
            icon.textContent = achievement.icon;
            name.textContent = achievement.name;
            desc.textContent = achievement.desc;
            
            popup.style.display = 'flex';
            popup.style.animation = 'achievementIn 0.5s ease-out';
            
            setTimeout(() => {
                popup.style.animation = 'achievementOut 0.5s ease-in';
                setTimeout(() => {
                    popup.style.display = 'none';
                }, 500);
            }, 4000);
        }
    }
    
    // 更新统计显示
    function updateStatsDisplay() {
        const pointsEl = document.getElementById('user-points');
        const levelEl = document.getElementById('user-level');
        const levelNameEl = document.getElementById('user-level-name');
        const streakEl = document.getElementById('user-streak');
        const progressEl = document.getElementById('level-progress');
        const progressTextEl = document.getElementById('level-progress-text');
        
        const levelInfo = calculateLevel(window.userData.points);
        const nextLevelPoints = getNextLevelPoints(levelInfo.level);
        
        if (pointsEl) pointsEl.textContent = window.userData.points;
        if (levelEl) levelEl.textContent = levelInfo.icon;
        if (levelNameEl) levelNameEl.textContent = 'Lv.' + levelInfo.level + ' ' + levelInfo.name;
        if (streakEl) streakEl.textContent = window.userData.consecutiveDays;
        
        if (progressEl && nextLevelPoints) {
            const currentLevelMin = levelInfo.minPoints;
            const progress = ((window.userData.points - currentLevelMin) / (nextLevelPoints - currentLevelMin)) * 100;
            progressEl.style.width = Math.min(progress, 100) + '%';
        }
        if (progressTextEl && nextLevelPoints) {
            progressTextEl.textContent = window.userData.points + '/' + nextLevelPoints;
        } else if (progressTextEl) {
            progressTextEl.textContent = '已满级';
        }
    }
    
    // 更新成就面板
    function updateAchievementsPanel() {
        const container = document.getElementById('achievements-container');
        if (!container) return;
        
        container.innerHTML = '';
        container.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;';
        
        achievementConfig.forEach(achievement => {
            const isUnlocked = window.userData.achievements.includes(achievement.id);
            const div = document.createElement('div');
            
            if (isUnlocked) {
                div.style.cssText = 'display:flex;align-items:center;gap:4px;padding:6px 10px;border-radius:20px;font-size:12px;background:#fef3c7;color:#78350f;border:2px solid #f59e0b;font-weight:700;cursor:default;';
            } else {
                div.style.cssText = 'display:flex;align-items:center;gap:4px;padding:6px 10px;border-radius:20px;font-size:12px;background:#e5e7eb;color:#374151;border:1px solid #9ca3af;font-weight:600;cursor:default;';
            }
            
            div.innerHTML = '<span style="font-size:14px;">' + (isUnlocked ? achievement.icon : '🔒') + '</span>' +
                '<span style="font-size:12px;font-weight:700;color:' + (isUnlocked ? '#78350f' : '#000000') + ';">' + achievement.name + '</span>';
            div.title = achievement.desc;
            container.appendChild(div);
        });
    }
    
    // 生成签到日历
    function generateCheckInCalendar() {
        const container = document.getElementById('checkin-calendar');
        if (!container) return;
        
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth();
        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        let html = '<div style="text-align:center;font-size:14px;font-weight:700;margin-bottom:10px;color:#000000;background:#e5e7eb;padding:8px;border-radius:8px;">' + year + '年' + (month + 1) + '月</div>';
        html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-bottom:6px;">';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">日</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">一</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">二</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">三</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">四</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">五</span>';
        html += '<span style="text-align:center;font-size:11px;color:#000000;font-weight:700;padding:4px 0;">六</span>';
        html += '</div>';
        html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px;">';
        
        for (let i = 0; i < firstDay; i++) {
            html += '<span style="visibility:hidden;"></span>';
        }
        
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
            const isCheckedIn = window.userData.checkInHistory.includes(dateStr);
            const isToday = day === today.getDate();
            
            let style = 'text-align:center;padding:6px 2px;font-size:12px;border-radius:6px;font-weight:700;';
            if (isCheckedIn) {
                style += 'background:#059669;color:#ffffff;';
            } else if (isToday) {
                style += 'background:#dbeafe;color:#1e40af;border:2px solid #3b82f6;';
            } else {
                style += 'background:#e5e7eb;color:#000000;';
            }
            html += '<span style="' + style + '">' + day + '</span>';
        }
        
        html += '</div>';
        container.innerHTML = html;
    }
    
    const emotionMap = {
        'neutral': '平静', 'happy': '开心', 'sad': '难过',
        'angry': '生气', 'fearful': '紧张', 'disgusted': '不适', 'surprised': '惊讶'
    };
    
    // 消极情绪列表
    const negativeEmotions = ['sad', 'angry', 'fearful', 'disgusted'];
    
    // 多样化鼓励语句库 - 分神提醒
    const distractedMessages = [
        "嘿，注意力回来啦~专注一下，你可以的！",
        "小伴发现你走神了哦，深呼吸，继续加油！",
        "学习需要专注力，让我们重新集中注意力吧！",
        "休息一下眼睛，然后继续专注学习哦~",
        "走神了？没关系，现在开始重新专注！",
        "专注是成功的关键，让我们一起努力！",
        "小伴提醒你：回到学习状态啦~",
        "发现你有点分心，要不要休息一下再继续？",
        "注意力是学习的第一步，加油！",
        "集中精神，你离目标又近了一步！"
    ];
    
    // 多样化鼓励语句库 - 消极情绪鼓励
    const encourageMessages = [
        "看起来你有点累了，记得适当休息哦，你已经很棒了！",
        "学习路上难免有低谷，但每一步都算数，加油！",
        "小伴看到你在努力，无论结果如何，你都很了不起！",
        "感到沮丧是正常的，休息一下，我们再出发！",
        "每个人都会有疲惫的时候，给自己一个拥抱吧~",
        "困难只是暂时的，你的努力终将开花结果！",
        "累了就休息，明天又是元气满满的一天！",
        "小伴相信你，你比想象中更强大！",
        "坚持不一定成功，但放弃一定不会，继续加油！",
        "每一次挫折都是成长的机会，你在变得更好！",
        "学习是马拉松，不是短跑，慢慢来~",
        "感到压力？深呼吸，你已经做得很好了！",
        "今天的辛苦是明天的收获，继续努力！",
        "小伴一直在这里陪着你，你不是一个人在战斗！",
        "即使进步很小，也是进步，为自己鼓掌！"
    ];
    
    // 播放提示音函数
    function playAlertSound(type) {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            if (type === 'distracted') {
                oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
                oscillator.frequency.setValueAtTime(660, audioContext.currentTime + 0.15);
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
            } else if (type === 'encourage') {
                oscillator.frequency.setValueAtTime(523, audioContext.currentTime);
                oscillator.frequency.setValueAtTime(659, audioContext.currentTime + 0.15);
                oscillator.frequency.setValueAtTime(784, audioContext.currentTime + 0.3);
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
            } else if (type === 'levelup') {
                const notes = [523, 659, 784, 1047];
                notes.forEach((freq, i) => {
                    const osc = audioContext.createOscillator();
                    const gain = audioContext.createGain();
                    osc.connect(gain);
                    gain.connect(audioContext.destination);
                    osc.frequency.setValueAtTime(freq, audioContext.currentTime + i * 0.1);
                    osc.type = 'sine';
                    gain.gain.setValueAtTime(0.25, audioContext.currentTime + i * 0.1);
                    gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + i * 0.1 + 0.2);
                    osc.start(audioContext.currentTime + i * 0.1);
                    osc.stop(audioContext.currentTime + i * 0.1 + 0.2);
                });
                return;
            } else if (type === 'achievement') {
                const notes = [784, 988, 1175, 1568];
                notes.forEach((freq, i) => {
                    const osc = audioContext.createOscillator();
                    const gain = audioContext.createGain();
                    osc.connect(gain);
                    gain.connect(audioContext.destination);
                    osc.frequency.setValueAtTime(freq, audioContext.currentTime + i * 0.12);
                    osc.type = 'triangle';
                    gain.gain.setValueAtTime(0.3, audioContext.currentTime + i * 0.12);
                    gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + i * 0.12 + 0.25);
                    osc.start(audioContext.currentTime + i * 0.12);
                    osc.stop(audioContext.currentTime + i * 0.12 + 0.25);
                });
                return;
            } else if (type === 'checkin') {
                oscillator.frequency.setValueAtTime(1047, audioContext.currentTime);
                oscillator.frequency.setValueAtTime(1319, audioContext.currentTime + 0.1);
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.25, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.3);
            } else {
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
            }
        } catch (e) {
            console.log('Audio playback not supported:', e);
        }
    }
    
    // 显示提醒消息的函数
    function showAlert(message, type) {
        const now = Date.now();
        if (now - window.lastAlertTime < window.alertCooldown) {
            return;
        }
        window.lastAlertTime = now;
        
        playAlertSound(type);
        
        const alertBox = document.getElementById('alert-box');
        const alertText = document.getElementById('alert-text');
        
        if (alertBox && alertText) {
            alertText.textContent = message;
            
            if (type === 'distracted') {
                alertBox.style.background = 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)';
            } else if (type === 'encourage') {
                alertBox.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            }
            
            alertBox.style.display = 'block';
            alertBox.style.animation = 'slideIn 0.5s ease-out';
            
            setTimeout(() => {
                alertBox.style.animation = 'slideOut 0.5s ease-in';
                setTimeout(() => {
                    alertBox.style.display = 'none';
                }, 500);
            }, 8000);
        }
        
        console.log('Alert shown:', type, message);
    }
    
    // 获取随机消息
    function getRandomMessage(messages) {
        return messages[Math.floor(Math.random() * messages.length)];
    }
    
    // ========== 优化1：预加载人脸识别模型 ==========
    // 页面加载时立即开始加载模型
    console.log('Starting pre-load of face detection models...');
    
    // 加载face-api.js库
    async function loadFaceApiLibrary() {
        if (typeof faceapi !== 'undefined') {
            console.log('face-api.js already loaded');
            return true;
        }
        
        const cdnUrls = [
            'https://unpkg.com/face-api.js@0.22.2/dist/face-api.min.js',
            'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/face-api.js/0.22.2/face-api.min.js'
        ];
        
        for (const url of cdnUrls) {
            try {
                console.log('Trying to load face-api.js from:', url);
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = url;
                    script.onload = () => resolve();
                    script.onerror = () => reject();
                    document.head.appendChild(script);
                });
                console.log('face-api.js loaded from:', url);
                return true;
            } catch (e) {
                console.warn('Failed to load from:', url);
                continue;
            }
        }
        console.error('Failed to load face-api.js from all CDN sources');
        return false;
    }
    
    // 加载模型函数
    async function loadModels() {
        if (typeof faceapi === 'undefined') {
            console.log('face-api.js not loaded yet, loading...');
            const loaded = await loadFaceApiLibrary();
            if (!loaded) {
                console.error('Failed to load face-api.js library');
                return false;
            }
            
            // 等待faceapi对象可用
            let waitCount = 0;
            while (typeof faceapi === 'undefined' && waitCount < 30) {
                await new Promise(r => setTimeout(r, 100));
                waitCount++;
            }
            
            if (typeof faceapi === 'undefined') {
                console.error('faceapi object not available after loading');
                return false;
            }
        }
        
        console.log('Loading face detection models...');
        
        const modelUrls = [
            'https://unpkg.com/@vladmandic/face-api@1.7.12/model',
            'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model',
            'https://justadudewhohacks.github.io/face-api.js/models'
        ];
        
        for (const MODEL_URL of modelUrls) {
            try {
                console.log('Trying to load models from:', MODEL_URL);
                
                await Promise.all([
                    faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
                    faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL)
                ]);
                
                window.modelsLoaded = true;
                console.log('Face detection models loaded successfully');
                
                // 更新状态显示
                const startBtn = document.getElementById('start-btn');
                if (startBtn) {
                    startBtn.title = '人脸识别模型已预加载，点击开始';
                    console.log('Models pre-loaded, ready to start');
                }
                
                return true;
            } catch (e) {
                console.warn('Model loading failed from:', MODEL_URL, e.message);
                continue;
            }
        }
        console.error('Failed to load models from all sources');
        return false;
    }
    
    // 页面加载后立即开始预加载模型
    setTimeout(async () => {
        console.log('Starting model pre-load on page load');
        await loadModels();
    }, 1000);
    
    // 情绪平滑处理
    function smoothEmotion(newEmotion, confidence) {
        const historySize = 5;
        window.emotionHistory.push({ emotion: newEmotion, confidence: confidence, time: Date.now() });
        
        if (window.emotionHistory.length > historySize) {
            window.emotionHistory.shift();
        }
        
        if (window.emotionHistory.length < 3) {
            return { emotion: newEmotion, confidence: confidence };
        }
        
        const emotionStats = {};
        window.emotionHistory.forEach(item => {
            if (!emotionStats[item.emotion]) {
                emotionStats[item.emotion] = { count: 0, totalConf: 0 };
            }
            emotionStats[item.emotion].count++;
            emotionStats[item.emotion].totalConf += item.confidence;
        });
        
        let bestEmotion = newEmotion;
        let bestScore = 0;
        
        for (const [emotion, stats] of Object.entries(emotionStats)) {
            const avgConf = stats.totalConf / stats.count;
            const score = stats.count * avgConf;
            if (score > bestScore) {
                bestScore = score;
                bestEmotion = emotion;
            }
        }
        
        const avgConfidence = emotionStats[bestEmotion].totalConf / emotionStats[bestEmotion].count;
        return { emotion: bestEmotion, confidence: avgConfidence };
    }
    
    // ========== 优化2：优化人脸检测频率 ==========
    // 从300ms调整为500ms，减轻CPU负担同时保持响应性
    const DETECTION_INTERVAL = 500; // 500ms检测一次，原来是300ms
    
    // 检测函数
    async function detectFace() {
        if (!window.isRunning || !window.modelsLoaded) return;
        
        const video = document.getElementById('webcam-video');
        const canvas = document.getElementById('webcam-canvas');
        const emotionEl = document.getElementById('emotion-display');
        const attentionEl = document.getElementById('attention-display');
        
        if (!video || !canvas || video.paused || video.ended || video.readyState < 2) return;
        
        const ctx = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        try {
            let detections;
            
            detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions({
                inputSize: 320, // 适当降低分辨率以提升性能
                scoreThreshold: 0.5
            }))
            .withFaceExpressions();
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            if (detections.length > 0) {
                window.noFaceCount = 0;
                const detection = detections[0];
                const box = detection.detection.box;
                
                // 绘制人脸框
                ctx.strokeStyle = '#6366f1';
                ctx.lineWidth = 2; // 稍微细一点的线
                ctx.strokeRect(box.x, box.y, box.width, box.height);
                
                // 获取情绪
                const expressions = detection.expressions;
                const sorted = Object.entries(expressions).sort((a, b) => b[1] - a[1]);
                
                const topEmotion = sorted[0][0];
                const topConfidence = sorted[0][1];
                
                // 应用情绪平滑处理
                const smoothed = smoothEmotion(topEmotion, topConfidence);
                const emotionCN = emotionMap[smoothed.emotion] || '平静';
                const displayConfidence = Math.round(smoothed.confidence * 100);
                
                // 绘制情绪标签
                const labelWidth = 100;
                ctx.fillStyle = '#6366f1';
                ctx.fillRect(box.x, box.y - 25, labelWidth, 22);
                ctx.fillStyle = 'white';
                ctx.font = 'bold 12px sans-serif';
                ctx.fillText(emotionCN + ' ' + displayConfidence + '%', box.x + 5, box.y - 8);
                
                if (emotionEl) {
                    emotionEl.textContent = emotionCN + ' ' + displayConfidence + '%';
                }
                
                // 根据情绪类型设置专注状态
                if (attentionEl) {
                    if (['happy', 'neutral'].includes(smoothed.emotion)) {
                        attentionEl.textContent = '专注中';
                        attentionEl.style.color = '#059669';
                        window.distractedCount = 0;
                        if (window.negativeEmotionCount > 0) window.negativeEmotionCount--;
                    } else if (['sad', 'fearful'].includes(smoothed.emotion)) {
                        attentionEl.textContent = '情绪低落';
                        attentionEl.style.color = '#f59e0b';
                        window.negativeEmotionCount++;
                        window.distractedCount = 0;
                    } else if (['angry', 'disgusted'].includes(smoothed.emotion)) {
                        attentionEl.textContent = '有些烦躁';
                        attentionEl.style.color = '#ef4444';
                        window.negativeEmotionCount++;
                        window.distractedCount = 0;
                    } else if (smoothed.emotion === 'surprised') {
                        attentionEl.textContent = '注意力分散';
                        attentionEl.style.color = '#8b5cf6';
                        window.distractedCount++;
                    } else {
                        attentionEl.textContent = '专注中';
                        attentionEl.style.color = '#059669';
                        window.distractedCount = 0;
                        if (window.negativeEmotionCount > 0) window.negativeEmotionCount--;
                    }
                }
                
                // 检查是否需要显示鼓励消息
                if (window.negativeEmotionCount >= 30) { // 调整为30次检测
                    showAlert(getRandomMessage(encourageMessages), 'encourage');
                    window.negativeEmotionCount = 0;
                }
            } else {
                window.noFaceCount++;
                window.distractedCount++;
                if (emotionEl) emotionEl.textContent = '---';
                if (attentionEl) {
                    if (window.noFaceCount >= 10) { 
                        attentionEl.textContent = '可能走神了'; 
                        attentionEl.style.color = '#f59e0b'; 
                    } else { 
                        attentionEl.textContent = '检测中...'; 
                        attentionEl.style.color = '#7c3aed'; 
                    }
                }
            }
            
            // 检查是否需要显示分神提醒
            if (window.distractedCount >= 25) { // 调整为25次检测
                showAlert(getRandomMessage(distractedMessages), 'distracted');
                window.distractedCount = 0;
            }
        } catch (e) { 
            console.error('Detection error:', e); 
        }
    }
    
    // 开启摄像头
    window.startWebcam = async function() {
        console.log('startWebcam called');
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const videoContainer = document.getElementById('video-container');
        const placeholder = document.getElementById('camera-placeholder');
        const loading = document.getElementById('loading-indicator');
        const attentionEl = document.getElementById('attention-display');
        
        if (window.isRunning) { console.log('Already running'); return; }
        
        if (startBtn) startBtn.style.display = 'none';
        if (placeholder) placeholder.style.display = 'none';
        if (loading) loading.style.display = 'block';
        
        if (!window.modelsLoaded) {
            console.log('Models not loaded, loading now...');
            const loadingText = document.querySelector('#loading-indicator p');
            if (loadingText) loadingText.textContent = '正在加载人脸识别模型...';
            
            const loaded = await loadModels();
            if (!loaded) {
                alert('人脸识别模型加载失败\\n\\n请刷新页面后重试');
                if (loading) loading.style.display = 'none';
                if (placeholder) placeholder.style.display = 'flex';
                if (startBtn) startBtn.style.display = 'inline-block';
                return;
            }
        }
        
        try {
            console.log('Requesting camera access...');
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    width: { ideal: 640 }, 
                    height: { ideal: 480 }, 
                    facingMode: 'user',
                    frameRate: { ideal: 24 } // 降低帧率到24fps以提升性能
                }
            });
            console.log('Camera access granted');
            
            let video = document.getElementById('webcam-video');
            if (!video) {
                video = document.createElement('video');
                video.id = 'webcam-video';
                video.autoplay = true;
                video.muted = true;
                video.playsInline = true;
                video.style.cssText = 'width:100%;border-radius:10px;transform:scaleX(-1);';
            }
            
            let canvas = document.getElementById('webcam-canvas');
            if (!canvas) {
                canvas = document.createElement('canvas');
                canvas.id = 'webcam-canvas';
                canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;border-radius:10px;transform:scaleX(-1);pointer-events:none;';
            }
            
            video.srcObject = stream;
            await video.play();
            
            if (videoContainer) {
                videoContainer.innerHTML = '';
                videoContainer.appendChild(video);
                videoContainer.appendChild(canvas);
                videoContainer.style.display = 'block';
            }
            
            if (loading) loading.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-block';
            
            window.isRunning = true;
            window.noFaceCount = 0;
            window.webcamStream = stream;
            window.emotionHistory = [];
            window.distractedCount = 0;
            window.negativeEmotionCount = 0;
            
            if (attentionEl) attentionEl.textContent = '监测中...';
            
            // 使用优化后的检测频率
            window.detectionInterval = setInterval(detectFace, DETECTION_INTERVAL);
            console.log('Webcam started with detection interval:', DETECTION_INTERVAL, 'ms');
            
            // 启动学习积分计时器
            startStudyPointsTimer();
            
            // 处理签到
            if (!window.userData.firstStudyDate) {
                window.userData.firstStudyDate = getTodayStr();
            }
            window.userData.lastStudyDate = getTodayStr();
            
            const checkInResult = handleCheckIn(window.userData);
            if (checkInResult.isNew) {
                playAlertSound('checkin');
                showAlert('签到成功！连续' + window.userData.consecutiveDays + '天，获得' + checkInResult.bonus + '积分', 'encourage');
                
                const newAchievements = checkAchievements(window.userData);
                newAchievements.forEach(achievement => {
                    setTimeout(() => {
                        showAchievementPopup(achievement);
                    }, 2000);
                });
            }
            
            saveUserData(window.userData);
            updateStatsDisplay();
            generateCheckInCalendar();
            updateAchievementsPanel();
            
        } catch (e) {
            console.error('Camera error:', e);
            alert('无法访问摄像头: ' + e.message);
            if (loading) loading.style.display = 'none';
            if (placeholder) placeholder.style.display = 'flex';
            if (startBtn) startBtn.style.display = 'inline-block';
        }
    };
    
    // 关闭摄像头
    window.stopWebcam = function() {
        console.log('stopWebcam called');
        window.isRunning = false;
        window.emotionHistory = [];
        window.distractedCount = 0;
        window.negativeEmotionCount = 0;
        
        stopStudyPointsTimer();
        
        const alertBox = document.getElementById('alert-box');
        if (alertBox) alertBox.style.display = 'none';
        
        if (window.detectionInterval) { 
            clearInterval(window.detectionInterval); 
            window.detectionInterval = null; 
        }
        if (window.webcamStream) { 
            window.webcamStream.getTracks().forEach(track => track.stop()); 
            window.webcamStream = null; 
        }
        
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const videoContainer = document.getElementById('video-container');
        const placeholder = document.getElementById('camera-placeholder');
        const emotionEl = document.getElementById('emotion-display');
        const attentionEl = document.getElementById('attention-display');
        
        if (videoContainer) { 
            videoContainer.innerHTML = ''; 
            videoContainer.style.display = 'none'; 
        }
        if (placeholder) placeholder.style.display = 'flex';
        if (stopBtn) stopBtn.style.display = 'none';
        if (startBtn) startBtn.style.display = 'inline-block';
        if (emotionEl) emotionEl.textContent = '---';
        if (attentionEl) { 
            attentionEl.textContent = '已关闭'; 
            attentionEl.style.color = '#7c3aed'; 
        }
        
        console.log('Webcam stopped');
    };
    
    // 绑定按钮事件
    function bindButtons() {
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        
        if (startBtn) {
            startBtn.onclick = function(e) {
                e.preventDefault();
                console.log('Start button clicked');
                window.startWebcam();
            };
            console.log('Start button bound');
        } else {
            console.log('Start button not found, retrying...');
            setTimeout(bindButtons, 500);
            return;
        }
        
        if (stopBtn) {
            stopBtn.onclick = function(e) {
                e.preventDefault();
                console.log('Stop button clicked');
                window.stopWebcam();
            };
            console.log('Stop button bound');
        }
    }
    
    // ========== 休息模式功能 ==========
    window.isResting = false;
    window.restTimer = null;
    window.restEndTime = 0;
    window.restCountdownInterval = null;
    
    // 主动结束休息的鼓励语句
    const earlyEndRestMessages = [
        "太棒了！主动结束休息，你的自律让人佩服！",
        "好样的！提前回到学习状态，你真的很努力！",
        "主动学习的态度值得表扬，继续保持！",
        "休息好了就开始学习，你的效率一定很高！",
        "自律的人最可怕，你就是那个人！加油！",
        "提前结束休息，说明你对学习充满热情！",
        "主动投入学习，成功就在不远处等你！",
        "你的积极态度让小伴很感动，一起加油吧！"
    ];
    
    // 休息结束提醒语句
    const restEndMessages = [
        "休息时间到啦！精神饱满地继续学习吧~",
        "充电完成！让我们以最好的状态继续前进！",
        "休息结束，新的学习旅程开始！",
        "元气满满！现在是重新专注的最佳时机~",
        "休息好了吗？让我们一起攻克难题吧！"
    ];
    
    // 显示休息面板
    window.showRestPanel = function() {
        const restPanel = document.getElementById('rest-panel');
        const restOptions = document.getElementById('rest-options');
        const restCountdown = document.getElementById('rest-countdown');
        const restBtn = document.getElementById('rest-mode-btn');
        
        if (restPanel) {
            restPanel.style.display = 'block';
            if (restOptions) restOptions.style.display = 'block';
            if (restCountdown) restCountdown.style.display = 'none';
        }
        if (restBtn) restBtn.style.display = 'none';
    };
    
    // 隐藏休息面板
    window.hideRestPanel = function() {
        const restPanel = document.getElementById('rest-panel');
        const restBtn = document.getElementById('rest-mode-btn');
        
        if (restPanel) restPanel.style.display = 'none';
        if (restBtn) restBtn.style.display = 'inline-block';
    };
    
    // 开始休息
    window.startRest = function(minutes) {
        if (window.isResting) return;
        
        if (window.isRunning) {
            window.stopWebcam();
        }
        
        window.isResting = true;
        const totalSeconds = minutes * 60;
        window.restEndTime = Date.now() + totalSeconds * 1000;
        
        const restOptions = document.getElementById('rest-options');
        const restCountdown = document.getElementById('rest-countdown');
        const countdownDisplay = document.getElementById('countdown-display');
        const attentionEl = document.getElementById('attention-display');
        
        if (restOptions) restOptions.style.display = 'none';
        if (restCountdown) restCountdown.style.display = 'block';
        if (attentionEl) {
            attentionEl.textContent = '休息中...';
            attentionEl.style.color = '#10b981';
        }
        
        function updateCountdown() {
            const remaining = Math.max(0, window.restEndTime - Date.now());
            const mins = Math.floor(remaining / 60000);
            const secs = Math.floor((remaining % 60000) / 1000);
            
            if (countdownDisplay) {
                countdownDisplay.textContent = String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
            }
            
            if (remaining <= 0) {
                window.endRest(false);
            }
        }
        
        updateCountdown();
        window.restCountdownInterval = setInterval(updateCountdown, 1000);
        
        window.restTimer = setTimeout(() => {
            window.endRest(false);
        }, totalSeconds * 1000);
        
        console.log('Rest started for', minutes, 'minutes');
    };
    
    // 结束休息
    window.endRest = function(isEarly) {
        if (!window.isResting) return;
        
        window.isResting = false;
        
        if (window.restTimer) {
            clearTimeout(window.restTimer);
            window.restTimer = null;
        }
        if (window.restCountdownInterval) {
            clearInterval(window.restCountdownInterval);
            window.restCountdownInterval = null;
        }
        
        window.hideRestPanel();
        
        if (isEarly) {
            showAlert(getRandomMessage(earlyEndRestMessages), 'encourage');
            playAlertSound('encourage');
            
            window.userData.earlyEndRestCount++;
            addPoints(window.userData, 5, 'early_rest');
            
            const newAchievements = checkAchievements(window.userData);
            newAchievements.forEach(achievement => {
                setTimeout(() => {
                    showAchievementPopup(achievement);
                }, 1500);
            });
            
            saveUserData(window.userData);
            updateStatsDisplay();
        } else {
            showAlert(getRandomMessage(restEndMessages), 'distracted');
            playAlertSound('distracted');
        }
        
        setTimeout(() => {
            window.startWebcam();
        }, 1000);
        
        console.log('Rest ended,', isEarly ? 'early' : 'time up');
    };
    
    // 自定义时间输入
    window.showCustomTimeInput = function() {
        const customInput = document.getElementById('custom-time-input');
        if (customInput) {
            customInput.style.display = customInput.style.display === 'none' ? 'flex' : 'none';
        }
    };
    
    window.startCustomRest = function() {
        const input = document.getElementById('custom-minutes');
        if (input) {
            const minutes = parseInt(input.value) || 5;
            if (minutes > 0 && minutes <= 60) {
                window.startRest(minutes);
            } else {
                alert('请输入1-60之间的分钟数');
            }
        }
    };
    
    // 绑定休息按钮事件
    function bindRestButtons() {
        const restModeBtn = document.getElementById('rest-mode-btn');
        const cancelRestBtn = document.getElementById('cancel-rest-btn');
        const stopRestBtn = document.getElementById('stop-rest-btn');
        const rest5Btn = document.getElementById('rest-5');
        const rest10Btn = document.getElementById('rest-10');
        const rest15Btn = document.getElementById('rest-15');
        const customBtn = document.getElementById('rest-custom');
        const startCustomBtn = document.getElementById('start-custom-rest');
        
        if (restModeBtn) {
            restModeBtn.onclick = function(e) {
                e.preventDefault();
                window.showRestPanel();
            };
        }
        
        if (cancelRestBtn) {
            cancelRestBtn.onclick = function(e) {
                e.preventDefault();
                window.hideRestPanel();
            };
        }
        
        if (stopRestBtn) {
            stopRestBtn.onclick = function(e) {
                e.preventDefault();
                window.endRest(true);
            };
        }
        
        if (rest5Btn) rest5Btn.onclick = () => window.startRest(5);
        if (rest10Btn) rest10Btn.onclick = () => window.startRest(10);
        if (rest15Btn) rest15Btn.onclick = () => window.startRest(15);
        if (customBtn) customBtn.onclick = () => window.showCustomTimeInput();
        if (startCustomBtn) startCustomBtn.onclick = () => window.startCustomRest();
        
        console.log('Rest buttons bound');
    }
    
    // 绑定快捷操作按钮
    function bindQuickActionButtons() {
        const adviceBtn = document.getElementById('advice-btn');
        const planBtn = document.getElementById('plan-btn');
        const encourageBtn = document.getElementById('encourage-btn');
        const clearBtn = document.getElementById('clear-btn');
        
        function sendMessage(message) {
            const textbox = document.querySelector('textarea[data-testid="textbox"]');
            if (textbox) {
                textbox.value = message;
                textbox.dispatchEvent(new Event('input', { bubbles: true }));
                setTimeout(() => {
                    const sendBtn = document.querySelector('#send-btn');
                    if (sendBtn) sendBtn.click();
                }, 100);
            }
        }
        
        if (adviceBtn) {
            adviceBtn.onclick = () => sendMessage('给我一些学习建议吧');
        }
        if (planBtn) {
            planBtn.onclick = () => sendMessage('帮我制定一个学习计划');
        }
        if (encourageBtn) {
            encourageBtn.onclick = () => sendMessage('我有点沮丧，需要一些鼓励');
        }
        if (clearBtn) {
            clearBtn.onclick = () => {
                if (confirm('确定要清空所有对话吗？')) {
                    location.reload();
                }
            };
        }
        
        console.log('Quick action buttons bound');
    }
    
    // 延迟绑定
    setTimeout(bindButtons, 1000);
    setTimeout(bindRestButtons, 1200);
    setTimeout(bindQuickActionButtons, 1300);
    
    // 初始化游戏化系统显示
    setTimeout(() => {
        updateStatsDisplay();
        generateCheckInCalendar();
        updateAchievementsPanel();
    }, 1500);
    
    console.log('Face detection initialized with optimizations');
}
"""

# 创建Gradio界面
with gr.Blocks(title="学习陪伴AI - 小伴") as demo:
    gr.HTML("""
        <style>
        .gradio-container { max-width: 1100px !important; margin: auto !important; }
        .gradio-container > .main { background: #f8fafc; }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px; border-radius: 15px;
            text-align: center; margin-bottom: 15px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .chat-header h1 { margin: 0; font-size: 24px; }
        .chat-header p { margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }
        #chatbot { 
            height: 480px !important; 
            border-radius: 15px !important; 
            overflow-y: auto !important;
        }
        /* 流式响应光标效果 */
        .typing-cursor {
            display: inline-block;
            width: 3px;
            height: 1em;
            background-color: #667eea;
            animation: blink 1s infinite;
            vertical-align: middle;
            margin-left: 2px;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }
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
        </style>
        
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
    """)
    
    gr.HTML("""
        <div class="chat-header">
            <h1>学习陪伴AI - 小伴 (优化版)</h1>
            <p>模型预加载 + 流式响应 + 优化检测频率 | 响应更快更流畅</p>
        </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            # 用户状态栏
            gr.HTML("""
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
            """)
            
            # 摄像头模块
            gr.HTML("""
                <div class="study-mode-panel">
                    <div class="study-mode-header">
                        <h3>📹 学习模式 (预加载已启用)</h3>
                        <div>
                            <button id="start-btn" type="button" class="camera-btn">
                                开启摄像头
                            </button>
                            <button id="stop-btn" type="button" class="camera-btn stop" style="display: none;">
                                关闭摄像头
                            </button>
                        </div>
                    </div>
                    
                    <div id="video-container" style="position: relative; width: 100%; max-width: 320px; margin: 0 auto; display: none; min-height: 180px;"></div>
                    
                    <div id="camera-placeholder" style="width: 100%; max-width: 320px; height: 180px; margin: 0 auto; background: rgba(255,255,255,0.6); border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #64748b; border: 2px dashed #cbd5e1;">
                        <div style="text-align: center;">
                            <svg style="width: 48px; height: 48px; margin-bottom: 10px; opacity: 0.6;" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"/>
                            </svg>
                            <p style="margin: 0; font-size: 13px;">人脸识别模型预加载中...</p>
                            <p style="margin: 5px 0 0 0; font-size: 12px; color: #6366f1;">点击按钮即可快速开始</p>
                        </div>
                    </div>
                    
                    <div id="loading-indicator" style="display: none; text-align: center; padding: 20px; color: #6366f1;">
                        <div style="display: inline-block; width: 30px; height: 30px; border: 3px solid #e5e7eb; border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                        <p style="margin: 10px 0 0 0; font-size: 14px;">启动摄像头...</p>
                    </div>
                    
                    <div class="emotion-status-grid">
                        <div class="status-card">
                            <p>当前情绪</p>
                            <p id="emotion-display" style="color: #4f46e5;">---</p>
                        </div>
                        <div class="status-card">
                            <p>专注状态</p>
                            <p id="attention-display" style="color: #7c3aed;">等待开启</p>
                        </div>
                    </div>
                </div>
                
                <!-- 休息模式面板 -->
                <div id="rest-panel" style="display: none; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 15px; padding: 15px; margin-bottom: 15px; color: white; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h3 style="margin: 0; font-size: 16px; display: flex; align-items: center; gap: 6px;">☕ 休息模式</h3>
                        <button id="cancel-rest-btn" type="button" style="background: rgba(255,255,255,0.2); color: white; border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 12px;">取消</button>
                    </div>
                    
                    <!-- 时间选择 -->
                    <div id="rest-options">
                        <p style="margin: 0 0 10px 0; font-size: 14px; opacity: 0.9;">选择休息时长：</p>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px;">
                            <button id="rest-5" type="button" style="flex: 1; min-width: 60px; background: rgba(255,255,255,0.2); color: white; border: none; padding: 10px 8px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">5分钟</button>
                            <button id="rest-10" type="button" style="flex: 1; min-width: 60px; background: rgba(255,255,255,0.2); color: white; border: none; padding: 10px 8px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">10分钟</button>
                            <button id="rest-15" type="button" style="flex: 1; min-width: 60px; background: rgba(255,255,255,0.2); color: white; border: none; padding: 10px 8px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">15分钟</button>
                        </div>
                        <button id="rest-custom" type="button" style="width: 100%; background: rgba(255,255,255,0.15); color: white; border: none; padding: 8px; border-radius: 8px; cursor: pointer; font-size: 13px;">⏰ 自定义时间</button>
                        <div id="custom-time-input" style="display: none; margin-top: 10px; align-items: center; gap: 8px;">
                            <input id="custom-minutes" type="number" min="1" max="60" value="20" style="flex: 1; padding: 8px; border-radius: 6px; border: none; font-size: 14px; text-align: center;">
                            <span style="font-size: 14px;">分钟</span>
                            <button id="start-custom-rest" type="button" style="background: white; color: #059669; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-weight: 500;">开始</button>
                        </div>
                    </div>
                    
                    <!-- 倒计时显示 -->
                    <div id="rest-countdown" style="display: none; text-align: center;">
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">剩余休息时间</p>
                        <p id="countdown-display" style="margin: 0 0 15px 0; font-size: 48px; font-weight: bold; font-family: monospace;">00:00</p>
                        <button id="stop-rest-btn" type="button" style="background: white; color: #059669; border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">🚀 结束休息，继续学习</button>
                    </div>
                </div>
                
                <!-- 休息一下按钮 -->
                <button id="rest-mode-btn" type="button" class="rest-btn">
                    ☕ 休息一下
                </button>
                
                <!-- 签到日历 -->
                <div class="checkin-panel" style="background:#ffffff;border:2px solid #10b981;border-radius:12px;padding:15px;margin-bottom:15px;">
                    <h4 style="margin:0 0 12px 0;font-size:15px;color:#000000;font-weight:700;">📅 签到日历</h4>
                    <div id="checkin-calendar"></div>
                </div>
                
                <!-- 成就面板 -->
                <div class="achievements-panel" style="background:#ffffff;border:2px solid #f59e0b;border-radius:12px;padding:15px;margin-bottom:15px;">
                    <h4 style="margin:0 0 12px 0;font-size:15px;color:#000000;font-weight:700;">🏆 我的成就</h4>
                    <div id="achievements-container"></div>
                </div>
                
                <!-- 快捷操作面板 -->
                <div class="quick-actions-panel" style="background:#ffffff;border:2px solid #8b5cf6;border-radius:12px;padding:15px;margin-bottom:15px;">
                    <h4 style="margin:0 0 12px 0;font-size:15px;color:#000000;font-weight:700;">⚡ 快捷操作</h4>
                    <div class="quick-actions-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                        <button id="advice-btn" type="button" style="background:#f3f4f6;border:2px solid #8b5cf6;border-radius:10px;padding:12px 10px;font-size:13px;font-weight:700;color:#000000;cursor:pointer;">💡 学习建议</button>
                        <button id="plan-btn" type="button" style="background:#f3f4f6;border:2px solid #8b5cf6;border-radius:10px;padding:12px 10px;font-size:13px;font-weight:700;color:#000000;cursor:pointer;">📋 制定计划</button>
                        <button id="encourage-btn" type="button" style="background:#f3f4f6;border:2px solid #8b5cf6;border-radius:10px;padding:12px 10px;font-size:13px;font-weight:700;color:#000000;cursor:pointer;">💪 鼓励我</button>
                        <button id="clear-btn" type="button" style="background:#fef2f2;border:2px solid #ef4444;border-radius:10px;padding:12px 10px;font-size:13px;font-weight:700;color:#991b1b;cursor:pointer;">🗑️ 清空对话</button>
                    </div>
                </div>
            """)
        
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                value=INITIAL_MESSAGES,
                elem_id="chatbot",
                show_label=False,
                height=480
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="输入你的问题或想说的话... (支持流式响应)",
                    show_label=False,
                    scale=4,
                    container=False
                )
                send_btn = gr.Button("发送", elem_id="send-btn", scale=1)
    
    # 事件绑定 - 使用流式响应
    send_btn.click(chat, [msg, chatbot], [chatbot, msg])
    msg.submit(chat, [msg, chatbot], [chatbot, msg])
    
    # 页面加载时执行JavaScript
    demo.load(fn=None, inputs=None, outputs=None, js=LOAD_JS)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)