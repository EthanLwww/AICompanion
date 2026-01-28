// ===== Step 3: 全局函数和初始化代码 =====
// 【重要】移除 async 包装器，确保代码在同步环境中立即执行

console.log('[LOAD_JS] 脚本开始执行');

(function() {
    'use strict';
    
    console.log('[LOAD_JS] 初始化全局变量...');
    
    // 初始化全局变量（即使后续加载失败也要执行）
    window.isRunning = false;
    window.modelsLoaded = false;
    window.noFaceCount = 0;
    window.webcamStream = null;
    window.detectionInterval = null;
    window.emotionHistory = [];
    window.useSsdModel = false;
    window.distractedCount = 0;
    window.negativeEmotionCount = 0;
    window.lastAlertTime = 0;
    window.alertCooldown = 30000;
    
    console.log('[LOAD_JS] 全局变量初始化完成');
    
    // ===== 异步加载 face-api.js =====
    // 这部分在后台异步执行，不阻塞主线程
    const loadFaceAPI = async () => {
        console.log('[LOAD_JS] 开始异步加载 face-api.js...');
        
        if (typeof faceapi !== 'undefined') {
            console.log('[LOAD_JS] face-api.js 已存在');
            return true;
        }
        
        const cdnUrls = [
            'https://unpkg.com/face-api.js@0.22.2/dist/face-api.min.js',
            'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/face-api.js/0.22.2/face-api.min.js'
        ];
        
        let loaded = false;
        for (const url of cdnUrls) {
            if (loaded) break;
            try {
                console.log('[LOAD_JS] 尝试从以下地址加载:', url);
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = url;
                    script.onload = () => {
                        console.log('[LOAD_JS] ✅ face-api.js 加载成功');
                        resolve();
                    };
                    script.onerror = () => {
                        try { document.head.removeChild(script); } catch(e) {}
                        reject(new Error('加载失败'));
                    };
                    document.head.appendChild(script);
                    setTimeout(() => {
                        if (!loaded) {
                            try { document.head.removeChild(script); } catch(e) {}
                            reject(new Error('超时'));
                        }
                    }, 10000);
                });
                loaded = true;
            } catch (e) {
                console.warn('[LOAD_JS] ⚠️ 从', url, '加载失败:', e.message);
                continue;
            }
        }
        
        if (!loaded) {
            console.error('[LOAD_JS] ❌ 无法从任何 CDN 加载 face-api.js');
            return false;
        }
        
        // 等待 faceapi 对象可用
        let waitCount = 0;
        while (typeof faceapi === 'undefined' && waitCount < 50) {
            await new Promise(r => setTimeout(r, 100));
            waitCount++;
        }
        
        if (typeof faceapi === 'undefined') {
            console.error('[LOAD_JS] ❌ faceapi 对象不可用');
            return false;
        }
        
        console.log('[LOAD_JS] ✅ faceapi 对象已就纪');
        return true;
    };
    
    // 在后台异步加载（不阻塞）
    loadFaceAPI().catch(e => {
        console.error('[LOAD_JS] face-api 加载出错:', e);
    });
    
    console.log('[LOAD_JS] 异步加载已启动，继续执行主线程代码...');

    
    // ========== 游戏化系统 - localStorage数据管理 ==========
    const STORAGE_KEY = 'studyCompanionData';
    
    // 默认用户数据
    const defaultUserData = {
        points: 0,                    // 总积分
        level: 1,                     // 当前等级
        totalStudyMinutes: 0,         // 总学习分钟数
        todayStudyMinutes: 0,         // 今日学习分钟数
        consecutiveDays: 0,           // 连续签到天数
        lastCheckInDate: null,        // 上次签到日期
        checkInHistory: [],           // 签到历史（最近30天）
        achievements: [],             // 已解锁成就ID列表
        positiveEmotionMinutes: 0,    // 积极情绪累计分钟
        earlyEndRestCount: 0,         // 主动结束休息次数
        firstStudyDate: null,         // 首次学习日期
        lastStudyDate: null,          // 最后学习日期
        // ========== 数据可视化扩展字段 ==========
        dailyRecords: [],             // 每日学习记录 [{date, studyMinutes, emotions:{}, bestHour}]
        weeklyReports: []             // 周报记录
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
                // 合并默认值，确保新字段存在
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
        
        // 如果是新的一天，重置今日学习分钟数
        if (userData.lastCheckInDate !== today) {
            userData.todayStudyMinutes = 0;
        }
        
        if (userData.lastCheckInDate === today) {
            return { isNew: false, bonus: 0 };
        }
        
        // 检查是否连续签到
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
        
        // 更新签到历史
        if (!userData.checkInHistory.includes(today)) {
            userData.checkInHistory.push(today);
            // 只保留最近30天
            if (userData.checkInHistory.length > 30) {
                userData.checkInHistory.shift();
            }
        }
        
        // 签到奖励积分（连续天数越多奖励越高）
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
        
        // 检查是否升级
        const leveledUp = levelInfo.level > oldLevel;
        
        return { leveledUp, newLevel: levelInfo };
    }
    
    // ========== 数据可视化相关函数 ==========
    
    // 获取或创建今日记录
    function getTodayRecord() {
        const today = getTodayStr();
        if (!window.userData.dailyRecords) {
            window.userData.dailyRecords = [];
        }
        let record = window.userData.dailyRecords.find(r => r.date === today);
        if (!record) {
            record = {
                date: today,
                studyMinutes: 0,
                emotions: { happy: 0, neutral: 0, sad: 0, angry: 0, fearful: 0, disgusted: 0, surprised: 0 },
                hourlyMinutes: {}, // {hour: minutes}
                focusScore: 0,     // 专注度得分
                emotionSamples: 0, // 情绪采样次数
                noFaceCount: 0,    // 走神次数（无人脸检测）
                totalSamples: 0,   // 总采样次数（包括走神）
                maxConsecutiveFocus: 0, // 最长连续专注时长（分钟）
                currentConsecutiveFocus: 0 // 当前连续专注时长
            };
            window.userData.dailyRecords.push(record);
            // 只保留最近60天
            if (window.userData.dailyRecords.length > 60) {
                window.userData.dailyRecords = window.userData.dailyRecords.slice(-60);
            }
        }
        return record;
    }
    
    // 记录学习时间（按小时）
    function recordStudyMinute() {
        const record = getTodayRecord();
        const hour = new Date().getHours();
        record.studyMinutes++;
        if (!record.hourlyMinutes[hour]) {
            record.hourlyMinutes[hour] = 0;
        }
        record.hourlyMinutes[hour]++;
    }
    
    // 记录情绪数据
    function recordEmotion(emotion, confidence) {
        const record = getTodayRecord();
        record.totalSamples++;
        
        if (record.emotions[emotion] !== undefined) {
            record.emotions[emotion]++;
            record.emotionSamples++;
        }
        
        // 判断是否为专注状态（开心/平静，且置信度>50%）
        const isFocused = (emotion === 'happy' || emotion === 'neutral') && (confidence || 0.5) > 0.4;
        
        if (isFocused) {
            record.currentConsecutiveFocus++;
            if (record.currentConsecutiveFocus > record.maxConsecutiveFocus) {
                record.maxConsecutiveFocus = record.currentConsecutiveFocus;
            }
        } else {
            record.currentConsecutiveFocus = 0;
        }
        
        // 计算综合专注度得分
        calculateFocusScore(record);
    }
    
    // 记录走神（无人脸检测）
    function recordNoFace() {
        const record = getTodayRecord();
        record.noFaceCount++;
        record.totalSamples++;
        record.currentConsecutiveFocus = 0; // 走神打断连续专注
        
        // 重新计算专注度
        calculateFocusScore(record);
    }
    
    // 综合专注度计算
    function calculateFocusScore(record) {
        if (record.totalSamples === 0) {
            record.focusScore = 0;
            return;
        }
        
        // 1. 积极情绪得分（满分60分）
        const positiveCount = (record.emotions.happy || 0) + (record.emotions.neutral || 0);
        const positiveRatio = record.emotionSamples > 0 ? positiveCount / record.emotionSamples : 0;
        const emotionScore = positiveRatio * 60;
        
        // 2. 出勤得分（满分30分）- 检测到人脸的比例
        const attendanceRatio = record.emotionSamples / record.totalSamples;
        const attendanceScore = attendanceRatio * 30;
        
        // 3. 连续专注加分（满分10分）- 最长连续专注越长，加分越多
        // 每10次连续专注（约3秒）加1分，上限10分
        const consecutiveBonus = Math.min(record.maxConsecutiveFocus / 10, 10);
        
        // 综合得分
        record.focusScore = Math.round(emotionScore + attendanceScore + consecutiveBonus);
        
        // 确保在0-100范围内
        record.focusScore = Math.max(0, Math.min(100, record.focusScore));
    }
    
    // 获取本周学习数据
    function getWeeklyData() {
        const today = new Date();
        const weekStart = new Date(today);
        weekStart.setDate(today.getDate() - today.getDay()); // 周日开始
        
        const weekData = [];
        for (let i = 0; i < 7; i++) {
            const d = new Date(weekStart);
            d.setDate(weekStart.getDate() + i);
            const dateStr = d.toISOString().split('T')[0];
            const record = (window.userData.dailyRecords || []).find(r => r.date === dateStr);
            weekData.push({
                date: dateStr,
                day: ['日', '一', '二', '三', '四', '五', '六'][i],
                studyMinutes: record ? record.studyMinutes : 0,
                focusScore: record ? record.focusScore : 0
            });
        }
        return weekData;
    }
    
    // 获取本月学习数据
    function getMonthlyData() {
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        
        let totalMinutes = 0;
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
            const record = (window.userData.dailyRecords || []).find(r => r.date === dateStr);
            if (record) {
                totalMinutes += record.studyMinutes;
            }
        }
        return totalMinutes;
    }
    
    // 获取最佳学习时段
    function getBestStudyHours() {
        const hourlyTotal = {};
        (window.userData.dailyRecords || []).forEach(record => {
            if (record.hourlyMinutes) {
                Object.entries(record.hourlyMinutes).forEach(([hour, mins]) => {
                    hourlyTotal[hour] = (hourlyTotal[hour] || 0) + mins;
                });
            }
        });
        
        // 找出前3个最佳时段
        const sorted = Object.entries(hourlyTotal).sort((a, b) => b[1] - a[1]);
        return sorted.slice(0, 3).map(([hour, mins]) => ({
            hour: parseInt(hour),
            minutes: mins,
            label: hour + ':00 - ' + (parseInt(hour) + 1) + ':00'
        }));
    }
    
    // 获取情绪趋势（最近7天）
    function getEmotionTrend() {
        const records = (window.userData.dailyRecords || []).slice(-7);
        return records.map(r => ({
            date: r.date,
            focusScore: r.focusScore || 0,
            mainEmotion: getMainEmotion(r.emotions)
        }));
    }
    
    // 获取主要情绪
    function getMainEmotion(emotions) {
        if (!emotions) return 'neutral';
        let max = 0;
        let main = 'neutral';
        Object.entries(emotions).forEach(([emotion, count]) => {
            if (count > max) {
                max = count;
                main = emotion;
            }
        });
        return main;
    }
    
    // 生成周报
    function generateWeeklyReport() {
        const weekData = getWeeklyData();
        const totalMinutes = weekData.reduce((sum, d) => sum + d.studyMinutes, 0);
        const avgFocus = weekData.filter(d => d.focusScore > 0).reduce((sum, d) => sum + d.focusScore, 0) / (weekData.filter(d => d.focusScore > 0).length || 1);
        const bestHours = getBestStudyHours();
        
        // 获取上周数据对比
        const lastWeekRecords = (window.userData.dailyRecords || []).slice(-14, -7);
        const lastWeekMinutes = lastWeekRecords.reduce((sum, r) => sum + (r.studyMinutes || 0), 0);
        
        const change = lastWeekMinutes > 0 ? Math.round(((totalMinutes - lastWeekMinutes) / lastWeekMinutes) * 100) : 100;
        
        return {
            totalMinutes,
            avgFocus: Math.round(avgFocus),
            bestHours,
            weekData,
            change,
            suggestion: generateSuggestion(totalMinutes, avgFocus, change, bestHours)
        };
    }
    
    // 生成建议
    function generateSuggestion(minutes, focus, change, bestHours) {
        const suggestions = [];
        
        if (minutes < 60) {
            suggestions.push('本周学习时间较少，建议每天至少保持30分钟的学习。');
        } else if (minutes > 600) {
            suggestions.push('学习时间充足，注意劳逸结合，避免过度疲劳。');
        }
        
        if (focus < 60) {
            suggestions.push('专注度有待提高，可以尝试番茄工作法，25分钟专注+5分钟休息。');
        } else if (focus >= 80) {
            suggestions.push('专注度表现优秀，继续保持！');
        }
        
        if (change < -20) {
            suggestions.push('学习时间比上周减少较多，需要调整学习计划。');
        } else if (change > 20) {
            suggestions.push('进步明显！学习时间比上周增加' + change + '%，继续加油！');
        }
        
        if (bestHours.length > 0) {
            suggestions.push('你的最佳学习时段是 ' + bestHours[0].label + '，建议在这个时间段安排重要任务。');
        }
        
        return suggestions.length > 0 ? suggestions : ['保持良好的学习习惯，继续努力！'];
    }
    
    // 初始化用户数据
    window.userData = loadUserData();
    
    // 学习计时器（每分钟+1积分）
    window.studyPointsInterval = null;
    window.positiveEmotionTime = 0; // 本次学习中积极情绪累计时间（秒）
    
    function startStudyPointsTimer() {
        if (window.studyPointsInterval) return;
        
        window.studyPointsInterval = setInterval(() => {
            if (window.isRunning && !window.isResting) {
                window.userData.totalStudyMinutes++;
                window.userData.todayStudyMinutes++;
                
                // 记录学习数据（用于可视化）
                recordStudyMinute();
                
                // 基础积分：每分钟+1
                let pointsToAdd = 1;
                
                // 连续专注奖励：每30分钟额外+10
                if (window.userData.todayStudyMinutes % 30 === 0) {
                    pointsToAdd += 10;
                    showAlert('连续专注30分钟，额外获得10积分！', 'encourage');
                    playAlertSound('levelup');
                }
                
                const result = addPoints(window.userData, pointsToAdd, 'study');
                
                // 如果升级了
                if (result.leveledUp) {
                    showAlert('恭喜升级！你现在是 ' + result.newLevel.icon + ' ' + result.newLevel.name + ' 了！', 'encourage');
                    playAlertSound('levelup');
                }
                
                // 检查成就
                const newAchievements = checkAchievements(window.userData);
                newAchievements.forEach(achievement => {
                    setTimeout(() => {
                        showAchievementPopup(achievement);
                    }, 1000);
                });
                
                saveUserData(window.userData);
                updateStatsDisplay();
            }
        }, 60000); // 每分钟执行一次
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
        
        // 更新进度条
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
        
        // 【加固】确保用户数据已加载
        if (!window.userData || !window.userData.achievements) {
            window.userData = loadUserData() || window.userData;
        }
        
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
        
        // 【加固】确保用户数据已加载，防止渲染空白
        if (!window.userData || !window.userData.checkInHistory) {
            window.userData = loadUserData() || window.userData;
        }
        
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
        
        // 填充空白
        for (let i = 0; i < firstDay; i++) {
            html += '<span style="visibility:hidden;"></span>';
        }
        
        // 填充日期
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
    
    // 【优化】风格化分神提醒词 (与后端同步)
    const STYLE_DISTRACTION_REMINDERS = {
        "默认": "专注一下，你可以的！",
        "柔情猫娘": "主人，不可以分心喵~ 快回过神来！",
        "成熟妈妈系御姐": "亲爱的，稍微集中一下注意力，好吗？",
        "磁性霸道男总裁": "我不允许你在这种时候分心，听到了吗？"
    };
    
    // 【新增】风格化情绪鼓励提醒词 (与后端同步)
    const STYLE_ENCOURAGE_REMINDERS = {
        "默认": "看起来你有点累了，记得适当休息哦，你已经很棒了！",
        "柔情猫娘": "主人喵~ 是不是累坏了？喵喵给你一个隔空的抱抱喵，打起精神来喵~",
        "成熟妈妈系御姐": "我的好孩子，累了就歇会儿，不管遇到什么困难，我都会陪在你身边的。",
        "磁性霸道男总裁": "振作起来，我不允许我的陪伴者露出这种丧气的表情。休息五分钟，然后继续。"
    };
    
    // 多样化鼓励语句库 - 分神提醒
    const distractedMessages = [
        "嘿，注意力回来啦~专注一下，你可以的！",
        "学了么发现你走神了哦，深呼吸，继续加油！",
        "学习需要专注力，让我们重新集中注意力吧！",
        "休息一下眼睛，然后继续专注学习哦~",
        "走神了？没关系，现在开始重新专注！",
        "专注是成功的关键，让我们一起努力！",
        "学了么提醒你：回到学习状态啦~",
        "发现你有点分心，要不要休息一下再继续？",
        "注意力是学习的第一步，加油！",
        "集中精神，你离目标又近了一步！"
    ];
    
    // 多样化鼓励语句库 - 消极情绪鼓励
    const encourageMessages = [
        "看起来你有点累了，记得适当休息哦，你已经很棒了！",
        "学习路上难免有低谷，但每一步都算数，加油！",
        "学了么看到你在努力，无论结果如何，你都很了不起！",
        "感到沮丧是正常的，休息一下，我们再出发！",
        "每个人都会有疲惫的时候，给自己一个拥抱吧~",
        "困难只是暂时的，你的努力终将开花结果！",
        "累了就休息，明天又是元气满满的一天！",
        "学了么相信你，你比想象中更强大！",
        "坚持不一定成功，但放弃一定不会，继续加油！",
        "每一次挫折都是成长的机会，你在变得更好！",
        "学习是马拉松，不是短跑，慢慢来~",
        "感到压力？深呼吸，你已经做得很好了！",
        "今天的辛苦是明天的收获，继续努力！",
        "学了么一直在这里陪着你，你不是一个人在战斗！",
        "即使进步很小，也是进步，为自己鼓掌！"
    ];
    
    // 播放提示音函数
    window.playAlertSound = function(type) {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // 根据类型设置不同的音调
            if (type === 'distracted') {
                // 分神提醒 - 较高频率，提醒注意
                oscillator.frequency.setValueAtTime(880, audioContext.currentTime); // A5
                oscillator.frequency.setValueAtTime(660, audioContext.currentTime + 0.15); // E5
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
            } else if (type === 'encourage') {
                // 鼓励提示 - 温和的上升音调
                oscillator.frequency.setValueAtTime(523, audioContext.currentTime); // C5
                oscillator.frequency.setValueAtTime(659, audioContext.currentTime + 0.15); // E5
                oscillator.frequency.setValueAtTime(784, audioContext.currentTime + 0.3); // G5
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.5);
            } else if (type === 'levelup') {
                // 升级音效 - 欢快的上升音阶
                const notes = [523, 659, 784, 1047]; // C5, E5, G5, C6
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
                // 成就解锁音效 - 胜利音调
                const notes = [784, 988, 1175, 1568]; // G5, B5, D6, G6
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
                // 签到音效 - 清脆的叮咚
                oscillator.frequency.setValueAtTime(1047, audioContext.currentTime); // C6
                oscillator.frequency.setValueAtTime(1319, audioContext.currentTime + 0.1); // E6
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
    };  // window.playAlertSound 函数结束
    
    // 显示提醒消息的函数
    function showAlert(message, type) {
        const now = Date.now();
        if (now - window.lastAlertTime < window.alertCooldown) {
            return; // 冷却时间内不重复提醒
        }
        window.lastAlertTime = now;
        
        // 播放提示音
        playAlertSound(type);
        
        const alertBox = document.getElementById('alert-box');
        const alertText = document.getElementById('alert-text');
        
        if (alertBox && alertText) {
            alertText.textContent = message;
            
            // 获取语音开关状态和触发器组件
            const voiceToggle = document.querySelector('#voice-toggle-checkbox input');
            const trigger = document.querySelector('#alert-trigger textarea');
            
            // 根据类型设置样式并触发语音
            if (type === 'distracted') {
                alertBox.style.background = 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)';
                
                if (voiceToggle && voiceToggle.checked && trigger) {
                    const triggerValue = 'distracted_' + Date.now();
                    console.log("[DEBUG-JS] 触发分神语音:", triggerValue);
                    trigger.value = triggerValue;
                    trigger.dispatchEvent(new Event('input', { bubbles: true }));
                }
            } else if (type === 'encourage') {
                alertBox.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                
                if (voiceToggle && voiceToggle.checked && trigger) {
                    const triggerValue = 'encourage_' + Date.now();
                    console.log("[DEBUG-JS] 触发鼓励语音:", triggerValue);
                    trigger.value = triggerValue;
                    trigger.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
            
            alertBox.style.display = 'block';
            alertBox.style.animation = 'slideIn 0.5s ease-out';
            
            // 8秒后自动隐藏
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
    
    // 加载模型 - 尝试多个CDN源，加载更多模型以提高精准度
    async function loadModels() {
        if (typeof faceapi === 'undefined') {
            console.error('faceapi not loaded');
            return false;
        }
        
        const modelUrls = [
            'https://unpkg.com/@vladmandic/face-api@1.7.12/model',
            'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model',
            'https://justadudewhohacks.github.io/face-api.js/models'
        ];
        
        for (const MODEL_URL of modelUrls) {
            try {
                console.log('Trying to load models from:', MODEL_URL);
                
                // 先加载必需的模型
                await Promise.race([
                    Promise.all([
                        faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
                        faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL),
                        faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL) // 添加68点特征点模型提高精度
                    ]),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Model load timeout')), 30000))
                ]);
                
                // 尝试加载更精确的SSD模型（可选）
                try {
                    await Promise.race([
                        faceapi.nets.ssdMobilenetv1.loadFromUri(MODEL_URL),
                        new Promise((_, reject) => setTimeout(() => reject(new Error('SSD model timeout')), 15000))
                    ]);
                    window.useSsdModel = true;
                    console.log('SSD Mobilenet model loaded - using high accuracy mode');
                } catch (e) {
                    console.log('SSD model not loaded, using TinyFaceDetector');
                    window.useSsdModel = false;
                }
                
                window.modelsLoaded = true;
                console.log('Models loaded successfully from:', MODEL_URL);
                return true;
            } catch (e) {
                console.warn('Model loading failed from:', MODEL_URL, e.message);
                continue;
            }
        }
        console.error('Failed to load models from all sources');
        return false;
    }
    
    // 情绪平滑处理 - 使用滑动窗口减少抖动
    function smoothEmotion(newEmotion, confidence) {
        const historySize = 12; // 【优化】增加窗口大小以提高稳定性
        window.emotionHistory.push({ emotion: newEmotion, confidence: confidence, time: Date.now() });
        
        // 只保留最近的记录
        if (window.emotionHistory.length > historySize) {
            window.emotionHistory.shift();
        }
        
        // 如果历史记录不足，直接返回当前结果
        if (window.emotionHistory.length < 3) {
            return { emotion: newEmotion, confidence: confidence };
        }
        
        // 统计各情绪出现频率和平均置信度
        const emotionStats = {};
        window.emotionHistory.forEach(item => {
            if (!emotionStats[item.emotion]) {
                emotionStats[item.emotion] = { count: 0, totalConf: 0 };
            }
            emotionStats[item.emotion].count++;
            emotionStats[item.emotion].totalConf += item.confidence;
        });
        
        // 找出出现次数最多且置信度较高的情绪
        let bestEmotion = newEmotion;
        let bestScore = 0;
        
        for (const [emotion, stats] of Object.entries(emotionStats)) {
            const avgConf = stats.totalConf / stats.count;
            const score = stats.count * avgConf; // 综合考虑频率和置信度
            if (score > bestScore) {
                bestScore = score;
                bestEmotion = emotion;
            }
        }
        
        const avgConfidence = emotionStats[bestEmotion].totalConf / emotionStats[bestEmotion].count;
        return { emotion: bestEmotion, confidence: avgConfidence };
    }
    
    // 检测函数 - 优化精准度
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
            
            // 根据加载的模型选择检测方式
            if (window.useSsdModel) {
                // 使用更精确的SSD模型 + 68点特征点
                detections = await faceapi.detectAllFaces(video, new faceapi.SsdMobilenetv1Options({
                    minConfidence: 0.6 // 【优化】提高置信度阈值
                }))
                .withFaceLandmarks()
                .withFaceExpressions();
            } else {
                // 使用优化参数的TinyFaceDetector + 68点特征点
                detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions({
                    inputSize: 320, // 【优化】减小尺寸以降低卡顿 (原416)
                    scoreThreshold: 0.6 // 【优化】提高置信度阈值 (原0.5)
                }))
                .withFaceLandmarks()
                .withFaceExpressions();
            }
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            if (detections.length > 0) {
                window.noFaceCount = 0;
                const detection = detections[0];
                const box = detection.detection.box;
                
                // 绘制人脸框
                ctx.strokeStyle = '#6366f1';
                ctx.lineWidth = 3;
                ctx.strokeRect(box.x, box.y, box.width, box.height);
                
                // 绘制68个特征点（可选，帮助调试）
                if (detection.landmarks) {
                    const landmarks = detection.landmarks;
                    ctx.fillStyle = '#10b981';
                    landmarks.positions.forEach(point => {
                        ctx.beginPath();
                        ctx.arc(point.x, point.y, 2, 0, 2 * Math.PI);
                        ctx.fill();
                    });
                }
                
                // 获取所有情绪及置信度
                const expressions = detection.expressions;
                const sorted = Object.entries(expressions).sort((a, b) => b[1] - a[1]);
                
                // 获取前两个情绪用于更准确的判断
                const topEmotion = sorted[0][0];
                const topConfidence = sorted[0][1];
                const secondEmotion = sorted[1] ? sorted[1][0] : null;
                const secondConfidence = sorted[1] ? sorted[1][1] : 0;
                
                // 应用情绪平滑处理
                const smoothed = smoothEmotion(topEmotion, topConfidence);
                const emotionCN = emotionMap[smoothed.emotion] || '平静';
                const displayConfidence = Math.round(smoothed.confidence * 100);
                
                // 记录情绪数据（用于可视化）
                recordEmotion(smoothed.emotion, smoothed.confidence);
                
                // 绘制情绪标签（显示更多信息）
                const labelWidth = 120;
                ctx.fillStyle = '#6366f1';
                ctx.fillRect(box.x, box.y - 28, labelWidth, 25);
                ctx.fillStyle = 'white';
                ctx.font = 'bold 14px sans-serif';
                ctx.fillText(emotionCN + ' ' + displayConfidence + '%', box.x + 5, box.y - 10);
                
                // 如果第二情绪置信度也较高，显示混合情绪（简化显示）
                let displayText = emotionCN + ' ' + displayConfidence + '%';
                if (secondConfidence > 0.25 && secondEmotion !== topEmotion) {
                    const secondCN = emotionMap[secondEmotion] || '';
                    if (secondCN) {
                        displayText = emotionCN + '/' + secondCN;
                    }
                }
                
                if (emotionEl) {
                    emotionEl.textContent = displayText;
                    emotionEl.title = emotionCN + ' (' + displayConfidence + '%)'; // 悬停显示完整信息
                }
                
                // 根据情绪类型设置专注状态
                if (attentionEl) {
                    if (['happy', 'neutral'].includes(smoothed.emotion)) {
                        attentionEl.textContent = '专注中';
                        attentionEl.style.color = '#059669';
                        // 重置分神计数，减少消极情绪计数
                        window.distractedCount = 0;
                        if (window.negativeEmotionCount > 0) window.negativeEmotionCount--;
                    } else if (['sad', 'fearful'].includes(smoothed.emotion)) {
                        attentionEl.textContent = '情绪低落';
                        attentionEl.style.color = '#f59e0b';
                        // 增加消极情绪计数
                        window.negativeEmotionCount++;
                        window.distractedCount = 0;
                    } else if (['angry', 'disgusted'].includes(smoothed.emotion)) {
                        attentionEl.textContent = '有些烦躁';
                        attentionEl.style.color = '#ef4444';
                        // 增加消极情绪计数
                        window.negativeEmotionCount++;
                        window.distractedCount = 0;
                    } else if (smoothed.emotion === 'surprised') {
                        attentionEl.textContent = '注意力分散';
                        attentionEl.style.color = '#8b5cf6';
                        // 增加分神计数
                        window.distractedCount++;
                    } else {
                        attentionEl.textContent = '专注中';
                        attentionEl.style.color = '#059669';
                        window.distractedCount = 0;
                        if (window.negativeEmotionCount > 0) window.negativeEmotionCount--;
                    }
                }
                
                // 检查是否需要显示鼓励消息（消极情绪持续约7秒，即14次检测 * 500ms）
                if (window.negativeEmotionCount >= 14) {
                    // 获取当前风格
                    let currentStyle = "默认";
                    const selectedStyleEl = document.querySelector('#style-radio .selected span') || 
                                          document.querySelector('#style-radio input:checked');
                    if (selectedStyleEl) {
                        currentStyle = selectedStyleEl.textContent || selectedStyleEl.value || "默认";
                    }
                    
                    const styleMessage = STYLE_ENCOURAGE_REMINDERS[currentStyle] || getRandomMessage(encourageMessages);
                    console.log(`[DEBUG-JS] 触发情绪鼓励 | 风格: ${currentStyle} | 消息: ${styleMessage}`);
                    
                    showAlert(styleMessage, 'encourage');
                    window.negativeEmotionCount = 0; // 重置计数
                }
            } else {
                window.noFaceCount++;
                window.distractedCount++; // 没检测到人脸也算分神
                
                // 记录走神数据（用于可视化）
                recordNoFace();
                
                if (emotionEl) emotionEl.textContent = '---';
                if (attentionEl) {
                    if (window.noFaceCount >= 8) { 
                        attentionEl.textContent = '可能走神了'; 
                        attentionEl.style.color = '#f59e0b'; 
                    } else { 
                        attentionEl.textContent = '检测中...'; 
                        attentionEl.style.color = '#7c3aed'; 
                    }
                }
            }
            
            // 检查是否需要显示分神提醒（分神持续约7秒，即14次检测 * 500ms）
            if (window.distractedCount >= 14) {
                // 获取当前风格
                let currentStyle = "默认";
                const selectedStyleEl = document.querySelector('#style-radio .selected span') || 
                                      document.querySelector('#style-radio input:checked');
                if (selectedStyleEl) {
                    currentStyle = selectedStyleEl.textContent || selectedStyleEl.value || "默认";
                }
                
                const styleMessage = STYLE_DISTRACTION_REMINDERS[currentStyle] || getRandomMessage(distractedMessages);
                console.log(`[DEBUG-JS] 触发分神提醒 | 风格: ${currentStyle} | 消息: ${styleMessage}`);
                
                showAlert(styleMessage, 'distracted');
                window.distractedCount = 0; // 重置计数
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
            console.log('Loading models...');
            const loadingText = document.querySelector('#loading-indicator p');
            if (loadingText) loadingText.textContent = '正在加载人脸识别模型...';
            
            const loaded = await loadModels();
            if (!loaded) {
                alert('人脸识别模型加载失败\\n\\n可能的原因：\\n1. 网络连接不稳定\\n2. CDN资源暂时不可用\\n\\n请刷新页面后重试，或检查网络连接');
                if (loading) loading.style.display = 'none';
                if (placeholder) placeholder.style.display = 'flex';
                if (startBtn) startBtn.style.display = 'inline-block';
                return;
            }
        }
        
        try {
            console.log('Requesting camera access...');
            // 提高摄像头分辨率以获得更精确的检测
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    width: { ideal: 640 }, 
                    height: { ideal: 480 }, 
                    facingMode: 'user',
                    frameRate: { ideal: 30 } // 提高帧率
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
            window.emotionHistory = []; // 重置情绪历史
            window.distractedCount = 0; // 重置分神计数
            window.negativeEmotionCount = 0; // 重置消极情绪计数
            
            if (attentionEl) attentionEl.textContent = '监测中...';
            
            // 【优化】降低检测频率到500ms以减轻主线程压力
            window.detectionInterval = setInterval(detectFace, 500);
            console.log('Webcam started successfully with enhanced detection');
            
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
                
                // 检查签到相关成就
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
        window.emotionHistory = []; // 清除情绪历史
        window.distractedCount = 0; // 重置分神计数
        window.negativeEmotionCount = 0; // 重置消极情绪计数
        
        // 停止学习积分计时器
        stopStudyPointsTimer();
        
        // 隐藏提醒框
        const alertBox = document.getElementById('alert-box');
        if (alertBox) alertBox.style.display = 'none';
        
        if (window.detectionInterval) { clearInterval(window.detectionInterval); window.detectionInterval = null; }
        if (window.webcamStream) { window.webcamStream.getTracks().forEach(track => track.stop()); window.webcamStream = null; }
        
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const videoContainer = document.getElementById('video-container');
        const placeholder = document.getElementById('camera-placeholder');
        const emotionEl = document.getElementById('emotion-display');
        const attentionEl = document.getElementById('attention-display');
        
        if (videoContainer) { videoContainer.innerHTML = ''; videoContainer.style.display = 'none'; }
        if (placeholder) placeholder.style.display = 'flex';
        if (stopBtn) stopBtn.style.display = 'none';
        if (startBtn) startBtn.style.display = 'inline-block';
        if (emotionEl) emotionEl.textContent = '---';
        if (attentionEl) { attentionEl.textContent = '已关闭'; attentionEl.style.color = '#7c3aed'; }
        
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
        "你的积极态度让学了么很感动，一起加油吧！"
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
        
        // 先关闭摄像头
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
        
        // 更新倒计时显示
        function updateCountdown() {
            const remaining = Math.max(0, window.restEndTime - Date.now());
            const mins = Math.floor(remaining / 60000);
            const secs = Math.floor((remaining % 60000) / 1000);
            
            if (countdownDisplay) {
                countdownDisplay.textContent = String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
            }
            
            if (remaining <= 0) {
                window.endRest(false); // 时间到，自动结束
            }
        }
        
        updateCountdown();
        window.restCountdownInterval = setInterval(updateCountdown, 1000);
        
        // 设置休息结束定时器
        window.restTimer = setTimeout(() => {
            window.endRest(false);
        }, totalSeconds * 1000);
        
        console.log('Rest started for', minutes, 'minutes');
    };
    
    // 结束休息
    window.endRest = function(isEarly) {
        if (!window.isResting) return;
        
        window.isResting = false;
        
        // 清除定时器
        if (window.restTimer) {
            clearTimeout(window.restTimer);
            window.restTimer = null;
        }
        if (window.restCountdownInterval) {
            clearInterval(window.restCountdownInterval);
            window.restCountdownInterval = null;
        }
        
        // 隐藏休息面板
        window.hideRestPanel();
        
        // 显示提示
        if (isEarly) {
            // 主动结束休息，显示鼓励
            showAlert(getRandomMessage(earlyEndRestMessages), 'encourage');
            playAlertSound('encourage');
            
            // 增加主动结束休息次数，并奖励积分
            window.userData.earlyEndRestCount++;
            addPoints(window.userData, 5, 'early_rest'); // 主动结束休息+5积分
            
            // 检查成就
            const newAchievements = checkAchievements(window.userData);
            newAchievements.forEach(achievement => {
                setTimeout(() => {
                    showAchievementPopup(achievement);
                }, 1500);
            });
            
            saveUserData(window.userData);
            updateStatsDisplay();
        } else {
            // 时间到，显示继续学习提醒
            showAlert(getRandomMessage(restEndMessages), 'distracted');
            playAlertSound('distracted');
        }
        
        // 自动开启学习模式（摄像头）
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
                window.endRest(true); // 主动结束
            };
        }
        
        if (rest5Btn) rest5Btn.onclick = () => window.startRest(5);
        if (rest10Btn) rest10Btn.onclick = () => window.startRest(10);
        if (rest15Btn) rest15Btn.onclick = () => window.startRest(15);
        if (customBtn) customBtn.onclick = () => window.showCustomTimeInput();
        if (startCustomBtn) startCustomBtn.onclick = () => window.startCustomRest();
        
        console.log('Rest buttons bound');
    }
    
    // 延迟绑定，确保DOM已加载
    setTimeout(bindButtons, 1000);
    setTimeout(bindRestButtons, 1200);
    setTimeout(bindReportButtons, 1400);
    
    // ========== 数据仪表盘更新函数 ==========
    function updateDashboard() {
        const today = getTodayStr();
        const todayRecord = getTodayRecord();
        const weekData = getWeeklyData();
        const monthMinutes = getMonthlyData();
        const bestHours = getBestStudyHours();
        
        // 更新日期显示
        const dateEl = document.getElementById('dashboard-date');
        if (dateEl) {
            const d = new Date();
            dateEl.textContent = (d.getMonth() + 1) + '月' + d.getDate() + '日';
        }
        
        // 更新时长统计
        const todayEl = document.getElementById('today-minutes');
        const weekEl = document.getElementById('week-minutes');
        const monthEl = document.getElementById('month-minutes');
        
        if (todayEl) todayEl.textContent = todayRecord.studyMinutes || 0;
        if (weekEl) weekEl.textContent = weekData.reduce((sum, d) => sum + d.studyMinutes, 0);
        if (monthEl) monthEl.textContent = monthMinutes;
        
        // 更新本周趋势图
        const chartEl = document.getElementById('week-chart');
        if (chartEl) {
            // 【修复】确保包含今日时长在内的最大值计算，防止除以极小值导致高度溢出
            const maxMinutes = Math.max(...weekData.map(d => d.studyMinutes), todayRecord.studyMinutes || 0, 1);
            let chartHtml = '';
            weekData.forEach(d => {
                // 【修复】高度计算增加 Math.min 封顶，防止柱条溢出遮挡文字
                const height = Math.min(Math.max((d.studyMinutes / maxMinutes) * 60, 2), 60);
                const isToday = d.date === today;
                chartHtml += '<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;">' +
                    '<div style="width:70%;background:' + (isToday ? 'linear-gradient(180deg,#3b82f6,#1d4ed8)' : '#93c5fd') + ';height:' + height + 'px;border-radius:4px;transition:height 0.3s;"></div>' +
                    '<span style="font-size:10px;color:' + (isToday ? '#1d4ed8' : '#6b7280') + ';font-weight:' + (isToday ? '700' : '500') + ';">' + d.day + '</span>' +
                    '<span style="font-size:9px;color:#9ca3af;">' + d.studyMinutes + '</span>' +
                    '</div>';
            });
            chartEl.innerHTML = chartHtml;
        }
        
        // 更新最佳学习时段
        const hoursEl = document.getElementById('best-hours');
        if (hoursEl) {
            if (bestHours.length > 0) {
                hoursEl.innerHTML = bestHours.map((h, i) => 
                    '<span style="background:' + ['#dbeafe', '#dcfce7', '#fef3c7'][i] + ';color:' + ['#1e40af', '#166534', '#b45309'][i] + ';padding:4px 10px;border-radius:15px;font-size:11px;font-weight:600;">' + h.label + '</span>'
                ).join('');
            } else {
                hoursEl.innerHTML = '<span style="background:#f3f4f6;color:#6b7280;padding:4px 10px;border-radius:15px;font-size:11px;">暂无数据</span>';
            }
        }
        
        // 更新专注度
        const focusBar = document.getElementById('focus-bar');
        const focusText = document.getElementById('focus-text');
        const focusScore = todayRecord.focusScore || 0;
        
        if (focusBar) focusBar.style.width = focusScore + '%';
        if (focusText) focusText.textContent = focusScore + '%';
    }
    
    // 显示周报弹窗
    function showWeeklyReport() {
        const modal = document.getElementById('weekly-report-modal');
        const content = document.getElementById('report-content');
        
        if (!modal || !content) return;
        
        modal.style.display = 'flex';
        
        const report = generateWeeklyReport();
        const hours = Math.floor(report.totalMinutes / 60);
        const mins = report.totalMinutes % 60;
        
        let changeHtml = '';
        if (report.change > 0) {
            changeHtml = '<span style="color:#16a34a;">↑ +' + report.change + '%</span>';
        } else if (report.change < 0) {
            changeHtml = '<span style="color:#dc2626;">↓ ' + report.change + '%</span>';
        } else {
            changeHtml = '<span style="color:#6b7280;">→ 持平</span>';
        }
        
        content.innerHTML = 
            '<div style="background:linear-gradient(135deg,#eff6ff,#dbeafe);border-radius:12px;padding:20px;margin-bottom:15px;text-align:center;">' +
                '<p style="margin:0 0 5px 0;font-size:13px;color:#3b82f6;font-weight:600;">本周累计学习</p>' +
                '<p style="margin:0;font-size:32px;font-weight:700;color:#1e40af;">' + hours + '<span style="font-size:16px;">时</span> ' + mins + '<span style="font-size:16px;">分</span></p>' +
                '<p style="margin:10px 0 0 0;font-size:12px;">相比上周 ' + changeHtml + '</p>' +
            '</div>' +
            
            '<div style="margin-bottom:15px;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#374151;font-weight:600;">📊 每日学习时长</p>' +
                '<div style="display:flex;justify-content:space-between;">' +
                    report.weekData.map(d => 
                        '<div style="text-align:center;">' +
                            '<div style="width:30px;height:30px;border-radius:50%;background:' + (d.studyMinutes > 0 ? '#3b82f6' : '#e5e7eb') + ';color:white;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;margin-bottom:4px;">' + d.studyMinutes + '</div>' +
                            '<span style="font-size:10px;color:#6b7280;">' + d.day + '</span>' +
                        '</div>'
                    ).join('') +
                '</div>' +
            '</div>' +
            
            '<div style="margin-bottom:15px;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#374151;font-weight:600;">🎯 平均专注度</p>' +
                '<div style="display:flex;align-items:center;gap:10px;">' +
                    '<div style="flex:1;background:#e5e7eb;border-radius:10px;height:12px;overflow:hidden;">' +
                        '<div style="background:linear-gradient(90deg,#10b981,#059669);height:100%;width:' + report.avgFocus + '%;border-radius:10px;"></div>' +
                    '</div>' +
                    '<span style="font-size:14px;font-weight:700;color:#059669;">' + report.avgFocus + '%</span>' +
                '</div>' +
            '</div>' +
            
            '<div style="background:#fef9e7;border-radius:12px;padding:15px;">' +
                '<p style="margin:0 0 10px 0;font-size:13px;color:#b45309;font-weight:600;">💡 本周建议</p>' +
                '<ul style="margin:0;padding-left:20px;">' +
                    report.suggestion.map(s => '<li style="font-size:12px;color:#78350f;margin-bottom:5px;">' + s + '</li>').join('') +
                '</ul>' +
            '</div>';
    }
    
    // 绑定报告按钮事件
    function bindReportButtons() {
        const showBtn = document.getElementById('show-report-btn');
        const closeBtn = document.getElementById('close-report-btn');
        const modal = document.getElementById('weekly-report-modal');
        
        if (showBtn) {
            showBtn.onclick = () => showWeeklyReport();
        }
        
        if (closeBtn) {
            closeBtn.onclick = () => {
                if (modal) modal.style.display = 'none';
            };
        }
        
        // 点击背景关闭
        if (modal) {
            modal.onclick = (e) => {
                if (e.target === modal) modal.style.display = 'none';
            };
        }
        
        console.log('Report buttons bound');
    }
    
    // 初始化游戏化系统显示
    setTimeout(() => {
        updateStatsDisplay();
        generateCheckInCalendar();
        updateAchievementsPanel();
        updateDashboard();
    }, 1500);
    
    // 每分钟更新一次仪表盘
    setInterval(() => {
        if (window.isRunning) {
            updateDashboard();
        }
    }, 60000);
    
    console.log('[LOAD_JS] 控制中心已初始化');
})();

console.log('[LOAD_JS] 脚本增载完成');

// 【修复】验证所有全局函数是否正常初始化
console.log('[LOAD_JS-VERIFY] 每个全局函数初始化成止：', {
    startWebcam: typeof window.startWebcam,
    playAlertSound: typeof window.playAlertSound,
    stopWebcam: typeof window.stopWebcam,
    showAlert: typeof window.showAlert,
    timestamp: new Date().toISOString()
});
