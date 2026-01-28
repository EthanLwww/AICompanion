/**
 * Step 4: 事件处理和交互绑定
 * 将前端UI事件与后端回调函数连接
 */

(function() {
    'use strict';
    
    console.log('[EVENT_HANDLER] Step 4 Event Binding Module Loading...');
    
    // 等待 Gradio 加载完成
    function waitForGradio(callback, maxAttempts = 50) {
        let attempts = 0;
        const interval = setInterval(() => {
            if (typeof gr !== 'undefined' && gr && gr.Client) {
                clearInterval(interval);
                callback();
            } else if (attempts >= maxAttempts) {
                clearInterval(interval);
                console.warn('[EVENT_HANDLER] Gradio not found after max attempts');
            }
            attempts++;
        }, 200);
    }
    
    // 主事件处理初始化
    function initEventHandlers() {
        console.log('[EVENT_HANDLER] Initializing event handlers...');
        
        // 【超级重要】页面重载検测机制：配合 launch(js=...) 使用
        // Gradio 每次重载页面时，永不确保全局函数有效
        console.log('[RECOVERY-INIT] 页面重载検测机制已启动，每 5 秒检查一次全局函数...');
        
        const pageReloadDetector = setInterval(() => {
            // 【修复】检查所有关键函数，而不仅需startWebcam
            const requiredFunctions = ['startWebcam', 'playAlertSound', 'stopWebcam'];
            const missingFunctions = requiredFunctions.filter(fn => 
                !window[fn] || typeof window[fn] !== 'function'
            );
                    
            if (missingFunctions.length > 0) {
                console.warn('[RECOVERY-TRIGGER] 檢测到缺失关键函数！缺失：', missingFunctions);
                console.warn('[RECOVERY-TRIGGER] 正在执行页面刷新...');
                // 重新加载页面，使 Gradio 重新注入 JS 代码
                location.reload();
            }
        }, 5000);  // 每 5 秒检查一次
        
        // 不进行过度重新加载：当页面卫海时，清理检测器
        window.addEventListener('beforeunload', () => {
            console.log('[RECOVERY-CLEANUP] 页面卫海中，清理检测器');
            clearInterval(pageReloadDetector);
        });
        
        try {
                    
            // ===== 【新增】监控对话功能 =====
            // 监听发送按钮和文本框的提交事件
            const msgInput = document.querySelector('[id="msg-input"] input, textarea[id="msg-input"]');
            const sendBtn = document.getElementById('send-btn');
            const gradioTextbox = document.querySelector('#msg-input');
                    
            if (msgInput) {
                console.log('[CHAT_MONITOR] 找到消息输入框 (input/textarea)');
                msgInput.addEventListener('input', function() {
                    console.log(`[CHAT_MONITOR] 用户输入: "${this.value}"`);
                });
                msgInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        console.log('[CHAT_MONITOR] 用户按下 Enter 键, 准备发送');
                    }
                });
            } else if (gradioTextbox) {
                console.log('[CHAT_MONITOR] 找到 Gradio 文本框元素 (#msg-input)');
            } else {
                console.warn('[CHAT_MONITOR] ⚠️ 消息输入框未找到!');
            }
                    
            if (sendBtn) {
                console.log('[CHAT_MONITOR] 找到发送按钮');
                // 原始的 click 事件监听
                sendBtn.addEventListener('click', function() {
                    console.log('[CHAT_MONITOR] 发送按钮被点击');
                    const inputText = msgInput ? msgInput.value : '(未找到输入框)';
                    console.log(`[CHAT_MONITOR] 发送内容: "${inputText}"`);
                });
            } else {
                console.warn('[CHAT_MONITOR] ⚠️ 发送按钮未找到!');
            }


            // ===== 摄像头控制事件 =====
            const startBtn = document.getElementById('start-btn');
            const stopBtn = document.getElementById('stop-btn');
            
            if (startBtn) {
                startBtn.addEventListener('click', async function() {
                    console.log('[EVENT_HANDLER] Camera Start button clicked');
                    console.log('[DEBUG-CAMERA] 检查 window.startWebcam 是否存在:', typeof window.startWebcam);
                    
                    // 【修复】旧带模式: 轮询等待最多鄍秒
                    let attempts = 0;
                    const maxAttempts = 50; // 最多等5秒
                    
                    while (typeof window.startWebcam !== 'function' && attempts < maxAttempts) {
                        console.log(`[DEBUG-CAMERA] 正在等待 window.startWebcam 加载... (${attempts + 1}/${maxAttempts})`);
                        await new Promise(r => setTimeout(r, 100));
                        attempts++;
                    }
                    
                    if (typeof window.startWebcam === 'function') {
                        console.log('[DEBUG-CAMERA] ✅ 终于找到了 window.startWebcam, 正在调用...');
                        try {
                            window.startWebcam();
                            console.log('[DEBUG-CAMERA] ✅ window.startWebcam() 调用成功');
                        } catch (error) {
                            console.error('[DEBUG-CAMERA] ❌ window.startWebcam() 执行出错:', error.message, error.stack);
                        }
                    } else {
                        console.error('[DEBUG-CAMERA] ❌ 超时! window.startWebcam 仍然不存在或不是函数!');
                        console.log('[DEBUG-CAMERA] 当前 window 对象中的函数列表:', Object.keys(window).filter(k => typeof window[k] === 'function').slice(0, 20));
                    }
                    
                    window.isRunning = true;
                    startBtn.style.display = 'none';
                    const stopBtn = document.getElementById('stop-btn');
                    if (stopBtn) stopBtn.style.display = 'inline-block';
                    
                    const loadingIndicator = document.getElementById('loading-indicator');
                    const cameraPlaceholder = document.getElementById('camera-placeholder');
                    if (loadingIndicator) loadingIndicator.style.display = 'block';
                    if (cameraPlaceholder) cameraPlaceholder.style.display = 'none';
                    
                    console.log('[DEBUG-CAMERA] 摄像头按钮状态已更新');
                });
            } else {
                console.warn('[DEBUG-CAMERA] ⚠️ start-btn 元素未找到!');
            }
            
            if (stopBtn) {
                stopBtn.addEventListener('click', function() {
                    console.log('[EVENT_HANDLER] Camera Stop button clicked');
                    window.isRunning = false;
                    stopBtn.style.display = 'none';
                    startBtn.style.display = 'inline-block';
                    
                    // 隐藏加载指示器
                    const loadingIndicator = document.getElementById('loading-indicator');
                    const cameraPlaceholder = document.getElementById('camera-placeholder');
                    if (loadingIndicator) loadingIndicator.style.display = 'none';
                    if (cameraPlaceholder) cameraPlaceholder.style.display = 'flex';
                    
                    console.log('[EVENT_HANDLER] Camera stream stopped');
                    showAlert('✓ 摄像头已关闭', 'info');
                });
            }
            
            // ===== 休息模式事件 =====
            const restModeBtn = document.getElementById('rest-mode-btn');
            const restPanel = document.getElementById('rest-panel');
            const cancelRestBtn = document.getElementById('cancel-rest-btn');
            
            if (restModeBtn) {
                restModeBtn.addEventListener('click', function() {
                    console.log('[EVENT_HANDLER] Rest Mode button clicked');
                    window.isRunning = false;
                    if (stopBtn) stopBtn.click(); // 关闭摄像头
                    if (restPanel) restPanel.style.display = 'block';
                    if (restModeBtn) restModeBtn.style.display = 'none';
                    playAlertSound('checkin');
                    showAlert('☕ 进入休息模式...', 'rest');
                });
            }
            
            if (cancelRestBtn) {
                cancelRestBtn.addEventListener('click', function() {
                    console.log('[EVENT_HANDLER] Cancel Rest button clicked');
                    if (restPanel) restPanel.style.display = 'none';
                    if (restModeBtn) restModeBtn.style.display = 'block';
                    showAlert('✓ 已返回学习模式', 'info');
                });
            }
            
            // ===== 快捷工具按钮事件 =====
            const adviceBtn = document.querySelector('button[innerText*="学习建议"]') || 
                             Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('💡'));
            const planBtn = document.querySelector('button[innerText*="制定计划"]') || 
                           Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('📋'));
            const encourageBtn = document.querySelector('button[innerText*="鼓励我"]') || 
                                Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('💪'));
            const clearBtn = document.querySelector('button[innerText*="清空对话"]') || 
                            Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('🗑️'));
            
            if (adviceBtn) {
                adviceBtn.addEventListener('click', function() {
                    console.log('[EVENT_HANDLER] Learning Advice button clicked');
                    showAlert('💡 正在生成学习建议...', 'info');
                    // 后端回调处理
                });
            }
            
            if (planBtn) {
                planBtn.addEventListener('click', function() {
                    console.log('[EVENT_HANDLER] Make Plan button clicked');
                    showAlert('📋 正在为你制定学习计划...', 'info');
                    // 后端回调处理
                });
            }
            
            if (encourageBtn) {
                encourageBtn.addEventListener('click', function() {
                    console.log('[EVENT_HANDLER] Encourage button clicked');
                    showAlert('💪 你已经很努力了，继续加油！', 'encourage');
                    playAlertSound('encourage');
                    // 后端回调处理
                });
            }
            
            if (clearBtn) {
                clearBtn.addEventListener('click', function() {
                    console.log('[EVENT_HANDLER] Clear History button clicked');
                    if (confirm('确定要清空所有对话吗？')) {
                        showAlert('🗑️ 已清空对话历史', 'info');
                        // 后端回调处理
                    }
                });
            }
            
            // ===== 报告按钮事件 =====
            const showReportBtn = document.getElementById('show-report-btn');
            if (showReportBtn) {
                showReportBtn.addEventListener('click', function() {
                    console.log('[EVENT_HANDLER] Show Report button clicked');
                    const modal = document.getElementById('weekly-report-modal');
                    if (modal) {
                        modal.style.display = 'flex';
                        playAlertSound('checkin');
                        showAlert('📊 正在生成学习报告...', 'info');
                    }
                });
            }
            
            // ===== 语音开关事件 =====
            const voiceToggle = document.querySelector('#voice-toggle-checkbox input');
            if (voiceToggle) {
                voiceToggle.addEventListener('change', function() {
                    const status = this.checked ? '已开启' : '已关闭';
                    console.log(`[EVENT_HANDLER] Voice toggle: ${status}`);
                    showAlert(`🔊 语音播报${status}`, 'info');
                });
            }
            
            // ===== 【新增】风格选择调试 =====
            console.log('[DEBUG-STYLE] ========== 开始扫描风格选择器 ==========');
            
            // 方式1: 查找 #style-radio
            let styleRadioContainer = document.querySelector('#style-radio');
            if (styleRadioContainer) {
                console.log('[DEBUG-STYLE] ✅ 找到 #style-radio 容器');
            } else {
                console.warn('[DEBUG-STYLE] ⚠️ #style-radio 容器未找到!');
                // 尝试其他选择器
                styleRadioContainer = document.querySelector('[id*="style"]');
                if (styleRadioContainer) {
                    console.log('[DEBUG-STYLE] 🔍 找到包含"style"的元素:', styleRadioContainer.id);
                }
            }
            
            // 方式2: 扫描所有 input[type="radio"]
            const allRadios = document.querySelectorAll('input[type="radio"]');
            console.log('[DEBUG-STYLE] 页面中总共有', allRadios.length, '个 radio 输入框');
            
            // 方式3: 尝试通过 label 查找（Gradio 可能用 label 包装）
            const allLabels = document.querySelectorAll('label');
            console.log('[DEBUG-STYLE] 页面中总共有', allLabels.length, '个 label 元素');
            
            let styleRelatedRadios = [];
            allRadios.forEach((radio, idx) => {
                const label = radio.closest('label');
                const labelText = label ? label.textContent : '';
                if (labelText.includes('默认') || labelText.includes('猫娘') || labelText.includes('御姐') || labelText.includes('总裁')) {
                    console.log(`[DEBUG-STYLE] 🎯 找到风格相关 radio: value="${radio.value}", label="${labelText.substring(0, 20)}"`);
                    styleRelatedRadios.push(radio);
                    // 添加变更监听
                    radio.addEventListener('change', function() {
                        console.log(`[DEBUG-STYLE] 风格已切换为: ${this.value}`);
                    });
                }
            });
            
            if (styleRelatedRadios.length === 0) {
                console.warn('[DEBUG-STYLE] ⚠️ 未找到任何风格相关的 radio 元素!');
                // 尝试查找 button（Gradio 可能用 button 实现 Radio）
                const allButtons = document.querySelectorAll('button');
                console.log('[DEBUG-STYLE] 页面中总共有', allButtons.length, '个 button 元素');
                allButtons.forEach((btn, idx) => {
                    const text = btn.textContent;
                    if (text.includes('默认') || text.includes('猫娘') || text.includes('御姐') || text.includes('总裁')) {
                        console.log(`[DEBUG-STYLE] 🔘 找到可能的风格按钮: "${text.substring(0, 20)}"`);
                    }
                });
            } else {
                console.log(`[DEBUG-STYLE] ✅ 找到 ${styleRelatedRadios.length} 个风格 radio 元素`);
            }
            
            console.log('[DEBUG-STYLE] ========== 风格选择器扫描完成 ==========');
            
            console.log('[EVENT_HANDLER] All event handlers initialized successfully');
            
        } catch (error) {
            console.error('[EVENT_HANDLER] Error initializing event handlers:', error);
        }
    }
    
    // 便捷函数：显示提醒
    function showAlert(message, type = 'info') {
        const alertBox = document.getElementById('alert-box');
        const alertText = document.getElementById('alert-text');
        
        if (alertBox && alertText) {
            alertText.textContent = message;
            
            // 根据类型设置背景颜色
            if (type === 'error') {
                alertBox.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
            } else if (type === 'success') {
                alertBox.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
            } else if (type === 'encourage') {
                alertBox.style.background = 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)';
            } else if (type === 'rest') {
                alertBox.style.background = 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)';
            } else {
                alertBox.style.background = 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)';
            }
            
            alertBox.style.display = 'block';
            
            // 3秒后隐藏
            setTimeout(() => {
                alertBox.style.display = 'none';
            }, 3000);
        }
    }
    
    // 在页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            console.log('[EVENT_HANDLER] DOM loaded, initializing handlers');
            setTimeout(initEventHandlers, 500); // 延迟初始化，确保所有元素已加载
        });
    } else {
        console.log('[EVENT_HANDLER] Document already loaded, initializing handlers immediately');
        setTimeout(initEventHandlers, 500);
    }
    
    console.log('[EVENT_HANDLER] Step 4 Event Binding Module Loaded Successfully');
    
})();

// ========== 抽卡系统函数 (步骤3) ==========
// 注意：这些函数需要在全局作用域，不包裹在立即执行函数中

console.log('[GACHA] 开始加载抽卡核心逻辑...');

// 在抽卡面板附近显示临时提示
function showGachaToast(message, type = 'info') {
    // 查找抽卡按钮
    const gachaBtn = document.getElementById('gacha-btn');
    if (!gachaBtn) {
        console.warn('[GACHA_TOAST] 抽卡按钮未找到，使用默认提示');
        if (typeof window.showAlert === 'function') {
            window.showAlert(message, type);
        }
        return;
    }
    
    // 创建提示框
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        padding: 16px 24px;
        background: linear-gradient(135deg, #fbbf24, #f59e0b);
        color: white;
        border-radius: 12px;
        font-size: 16px;
        font-weight: 600;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        z-index: 10001;
        animation: toast-pop 0.3s ease-out;
    `;
    toast.textContent = message;
    
    // 添加动画样式
    const style = document.createElement('style');
    style.textContent = `
        @keyframes toast-pop {
            0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0; }
            100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(toast);
    
    // 2秒后移除
    setTimeout(() => {
        toast.style.animation = 'toast-pop 0.3s ease-in reverse';
        setTimeout(() => {
            document.body.removeChild(toast);
            document.head.removeChild(style);
        }, 300);
    }, 2000);
    
    console.log('[GACHA_TOAST] 显示提示:', message);
}

// 抽卡主函数
function doGacha() {
    console.log('[GACHA] 当前spendablePoints:', window.userData.spendablePoints, '需要:', window.GACHA_COST);
    
    if (window.userData.spendablePoints < window.GACHA_COST) {
        // 在抽卡按钮附近显示提示
        showGachaToast('⚠️ 积分不足！需要 ' + window.GACHA_COST + ' 积分', 'warning');
        window.playAlertSound('click');
        return null;
    }
    
    // 扣除消耗积分
    window.userData.spendablePoints -= window.GACHA_COST;
    window.userData.totalGachaCount++;
    
    // 检查是否有幸运金币效果
    const hasLuckyBoost = window.userData.inventory.some(inv => 
        inv.itemId === 'item_lucky_coin' && inv.count > 0 && inv.activeForNextGacha
    );
    
    // 随机决定稀有度
    let roll = Math.random() * 100;
    let selectedRarity = 'N';
    
    if (hasLuckyBoost) {
        // 幸运金币：必出R及以上
        roll = Math.random() * 50; // 只在R/SR/SSR中抽
        if (roll < 5) selectedRarity = 'SSR';
        else if (roll < 20) selectedRarity = 'SR';
        else selectedRarity = 'R';
        
        // 消耗幸运金币
        const luckyItem = window.userData.inventory.find(inv => inv.itemId === 'item_lucky_coin' && inv.activeForNextGacha);
        if (luckyItem) {
            luckyItem.count--;
            luckyItem.activeForNextGacha = false;
            if (luckyItem.count <= 0) {
                window.userData.inventory = window.userData.inventory.filter(inv => inv.itemId !== 'item_lucky_coin' || inv.count > 0);
            }
        }
    } else {
        // 正常概率
        if (roll < 5) selectedRarity = 'SSR';
        else if (roll < 20) selectedRarity = 'SR';
        else if (roll < 50) selectedRarity = 'R';
        else selectedRarity = 'N';
    }
    
    // 从对应稀有度的物品中随机选择
    const poolItems = gachaItems.filter(item => item.rarity === selectedRarity);
    const selectedItem = poolItems[Math.floor(Math.random() * poolItems.length)];
    
    // 添加到背包
    const addResult = addToInventory(selectedItem.id);
    
    // 记录抽卡历史
    window.userData.gachaHistory.unshift({
        itemId: selectedItem.id,
        time: new Date().toISOString()
    });
    if (window.userData.gachaHistory.length > 50) {
        window.userData.gachaHistory = window.userData.gachaHistory.slice(0, 50);
    }
    
    saveUserData(window.userData);
    if (typeof window.updateStatsDisplay === 'function') {
        window.updateStatsDisplay();
    }
    
    // 返回物品和转换信息
    return { item: selectedItem, converted: addResult.converted, convertedPoints: addResult.points || 0 };
}

// 添加物品到背包（非道具类已有物品转化为积分）
function addToInventory(itemId) {
    if (!window.userData.inventory) window.userData.inventory = [];
    
    const item = window.getItemById(itemId);
    const existing = window.userData.inventory.find(inv => inv.itemId === itemId);
    
    if (existing) {
        // 道具类可以叠加，其他类型转化为积分
        if (item && item.type === 'consumable') {
            existing.count++;
        } else {
            // 非道具类重复物品转化为5可用积分
            window.userData.spendablePoints += 5;
            return { converted: true, points: 5 };
        }
    } else {
        window.userData.inventory.push({
            itemId: itemId,
            count: 1,
            obtainedAt: new Date().toISOString()
        });
    }
    return { converted: false };
}

// 执行抽卡并显示动画
function performGacha() {
    console.log('[GACHA] performGacha 被调用');
    const result = doGacha();
    console.log('[GACHA] doGacha 返回结果:', result);
    
    if (result) {
        console.log('[GACHA] 开始显示动画, 物品:', result.item.name, '稀有度:', result.item.rarity);
        showGachaAnimation(result);
        updateGachaDisplay();
    } else {
        console.warn('[GACHA] doGacha 返回 null, 可能积分不足');
    }
}

// 更新抽卡面板显示
function updateGachaDisplay() {
    const pointsEl = document.getElementById('gacha-points-display');
    if (pointsEl) {
        const spendablePoints = window.userData.spendablePoints || 0;
        console.log('[GACHA_DISPLAY] 刷新抽卡积分显示:', spendablePoints);
        pointsEl.textContent = spendablePoints + ' 积分';
    }
}

// 显示抽卡动画
function showGachaAnimation(result) {
    console.log('[GACHA_ANIMATION] 开始渲染动画, result:', result);
    
    const item = result.item;
    const converted = result.converted;
    const convertedPoints = result.convertedPoints;
    const rarity = window.rarityConfig[item.rarity];
    
    console.log('[GACHA_ANIMATION] 物品信息 - name:', item.name, 'rarity:', item.rarity, 'icon:', item.icon);
    console.log('[GACHA_ANIMATION] 稀有度配置:', rarity);
    
    const modal = document.createElement('div');
    modal.id = 'gacha-result-modal';
    modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);display:flex;align-items:center;justify-content:center;z-index:10000;';
    
    let bgGlow = '';
    if (item.rarity === 'SSR') {
        bgGlow = 'box-shadow:0 0 100px 50px rgba(245,158,11,0.5);';
    } else if (item.rarity === 'SR') {
        bgGlow = 'box-shadow:0 0 80px 30px rgba(139,92,246,0.4);';
    }
    
    let content = '<div style="text-align:center;animation:gacha-pop 0.5s ease-out;">';
    content += '<div style="width:150px;height:150px;background:' + rarity.bgColor + ';border:4px solid ' + rarity.color + ';border-radius:20px;display:flex;align-items:center;justify-content:center;margin:0 auto 20px auto;' + bgGlow + '">';
    content += '<span style="font-size:64px;">' + item.icon + '</span>';
    content += '</div>';
    content += '<h2 style="margin:0 0 5px 0;color:white;font-size:24px;">' + item.name + '</h2>';
    content += '<div style="display:inline-block;padding:5px 15px;background:' + rarity.bgColor + ';color:' + rarity.color + ';border-radius:15px;font-weight:700;margin-bottom:10px;">' + rarity.name + '</div>';
    content += '<p style="color:#d1d5db;font-size:14px;margin:0 0 15px 0;">' + item.desc + '</p>';
    
    // 显示转换提示
    if (converted) {
        content += '<div style="background:linear-gradient(135deg,#fef3c7,#fde68a);color:#92400e;padding:8px 16px;border-radius:20px;font-size:13px;font-weight:600;margin-bottom:15px;display:inline-block;">🔄 已拥有！转化为 +' + convertedPoints + ' 积分</div>';
    }
    
    content += '<button id="close-gacha-modal" style="padding:12px 40px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);color:white;border:none;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer;">确定</button>';
    content += '</div>';
    
    // 添加动画样式
    const styleEl = document.createElement('style');
    styleEl.textContent = '@keyframes gacha-pop { from { transform: scale(0); opacity: 0; } to { transform: scale(1); opacity: 1; } }';
    document.head.appendChild(styleEl);
    
    modal.innerHTML = content;
    document.body.appendChild(modal);
    console.log('[GACHA_ANIMATION] ✅ 模态框已添加到 DOM, id:', modal.id);
    
    // 播放音效
    if (item.rarity === 'SSR') {
        if (typeof window.playAlertSound === 'function') window.playAlertSound('levelup');
    } else if (item.rarity === 'SR') {
        if (typeof window.playAlertSound === 'function') window.playAlertSound('achievement');
    } else {
        if (typeof window.playAlertSound === 'function') window.playAlertSound('click');
    }
    
    document.getElementById('close-gacha-modal').onclick = () => {
        document.body.removeChild(modal);
        document.head.removeChild(styleEl);
        renderInventory();
    };
    
    modal.onclick = (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
            document.head.removeChild(styleEl);
            renderInventory();
        }
    };
}

// 暴露抽卡函数到全局
window.performGacha = performGacha;
window.doGacha = doGacha;
window.updateGachaDisplay = updateGachaDisplay;

console.log('[GACHA] ✅ 抽卡核心逻辑加载完成');

// ========== 背包渲染功能 ==========

// 渲染背包面板
function renderInventory() {
    const container = document.getElementById('inventory-container');
    if (!container) return;
    
    const inventory = window.userData.inventory || [];
    
    if (inventory.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:30px;color:#9ca3af;"><p style="font-size:24px;margin:0 0 10px 0;">📦</p><p style="margin:0;">背包空空如也，快去抽卡吧！</p></div>';
        return;
    }
    
    // 按类型分组
    const groups = {
        avatarFrame: { name: '头像框', items: [] },
        chatBubble: { name: '聊天气泡', items: [] },
        theme: { name: '主题皮肤', items: [] },
        title: { name: '称号', items: [] },
        quoteCard: { name: '名言卡片', items: [] },
        consumable: { name: '道具', items: [] }
    };
    
    inventory.forEach(inv => {
        const item = window.getItemById(inv.itemId);
        if (item && groups[item.type]) {
            groups[item.type].items.push({ ...item, count: inv.count });
        }
    });
    
    let html = '';
    
    Object.entries(groups).forEach(([type, group]) => {
        if (group.items.length === 0) return;
        
        html += '<div style="margin-bottom:15px;">';
        html += '<h4 style="margin:0 0 10px 0;font-size:13px;color:#374151;font-weight:600;">' + group.name + '</h4>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:8px;">';
        
        group.items.forEach(item => {
            const rarity = window.rarityConfig[item.rarity];
            const isEquipped = (
                (type === 'avatarFrame' && window.userData.equipped.avatarFrame === item.id) ||
                (type === 'chatBubble' && window.userData.equipped.chatBubble === item.id) ||
                (type === 'theme' && window.userData.equipped.theme === item.id) ||
                (type === 'title' && window.userData.equipped.title === item.id)
            );
            
            html += '<div class="inventory-item" data-id="' + item.id + '" style="position:relative;width:70px;text-align:center;padding:10px 5px;background:' + rarity.bgColor + ';border:2px solid ' + (isEquipped ? '#10b981' : rarity.color) + ';border-radius:10px;cursor:pointer;transition:all 0.2s ease;">';
            html += '<div style="font-size:24px;margin-bottom:4px;">' + item.icon + '</div>';
            html += '<div style="font-size:10px;color:' + rarity.color + ';font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + item.name + '</div>';
            
            if (item.count > 1) {
                html += '<div style="position:absolute;top:3px;right:3px;background:#ef4444;color:white;font-size:10px;padding:1px 5px;border-radius:10px;">x' + item.count + '</div>';
            }
            
            if (isEquipped) {
                html += '<div style="position:absolute;top:3px;left:3px;background:#10b981;color:white;font-size:8px;padding:1px 4px;border-radius:4px;">使用中</div>';
            }
            
            html += '</div>';
        });
        
        html += '</div></div>';
    });
    
    container.innerHTML = html;
    
    // 绑定点击事件 - 道具类可使用，其他显示提示
    container.querySelectorAll('.inventory-item').forEach(el => {
        el.onclick = function() {
            const itemId = this.dataset.id;
            const item = window.getItemById(itemId);
            if (item) {
                if (item.type === 'consumable') {
                    // 消耗品直接使用
                    if (typeof window.useItem === 'function') {
                        window.useItem(itemId);
                    }
                } else {
                    // 其他物品显示提示
                    window.showAlert('🎉 ' + item.name + ' - ' + item.desc, 'success');
                }
            }
        };
    });
}

// 暴露背包函数到全局
window.renderInventory = renderInventory;

console.log('[INVENTORY] ✅ 背包渲染功能加载完成');

// ========== 道具使用功能 ==========

// 使用道具
function useItem(itemId) {
    const invItem = window.userData.inventory.find(inv => inv.itemId === itemId && inv.count > 0);
    if (!invItem) {
        window.showAlert('物品不足！', 'warning');
        return false;
    }
    
    const item = window.getItemById(itemId);
    if (!item) return false;
    
    // 根据物品类型处理
    switch (item.type) {
        case 'consumable':
            // 消耗品需要特殊处理
            if (item.points) {
                // 积分袋
                window.userData.points += item.points;
                window.userData.spendablePoints += item.points;
                invItem.count--;
                window.showAlert('获得 ' + item.points + ' 积分！', 'encourage');
                window.playAlertSound('achievement');
            } else if (item.id === 'item_double_points') {
                // 双倍积分卡
                window.userData.activeBuffs.doublePoints = Date.now() + (item.duration || 86400000);
                invItem.count--;
                window.showAlert('双倍积分效果已激活！持续24小时', 'encourage');
                window.playAlertSound('achievement');
            } else if (item.id === 'item_lucky_coin') {
                // 幸运金币 - 标记下次抽卡生效
                invItem.activeForNextGacha = true;
                window.showAlert('幸运金币已激活！下次抽卡必出R及以上', 'encourage');
                window.playAlertSound('achievement');
                // 不扣除数量，抽卡时扣除
                saveUserData(window.userData);
                if (typeof window.updateGachaDisplay === 'function') {
                    window.updateGachaDisplay();
                }
                renderInventory();
                return true;
            }
            
            if (invItem.count <= 0) {
                window.userData.inventory = window.userData.inventory.filter(inv => inv.count > 0);
            }
            break;
            
        default:
            window.showAlert('该物品暂不可用', 'warning');
            return false;
    }
    
    saveUserData(window.userData);
    if (typeof window.updateGachaDisplay === 'function') {
        window.updateGachaDisplay();
    }
    renderInventory();
    return true;
}

// 暴露useItem到全局
window.useItem = useItem;

console.log('[INVENTORY] ✅ 道具使用功能加载完成');

// ========== 步骤7: 抽卡系统事件绑定 ==========

// 绑定抽卡按钮点击事件
function bindGachaEvents() {
    console.log('[GACHA_EVENT] 开始绑定抽卡系统事件...');
    
    // 抽卡按钮点击
    const gachaBtn = document.getElementById('gacha-btn');
    if (gachaBtn) {
        gachaBtn.addEventListener('click', function() {
            console.log('[GACHA_EVENT] 抽卡按钮被点击');
            if (typeof window.performGacha === 'function') {
                window.performGacha();
            } else {
                console.error('[GACHA_EVENT] performGacha 函数未找到!');
            }
        });
        console.log('[GACHA_EVENT] ✅ 抽卡按钮事件绑定成功');
    } else {
        console.warn('[GACHA_EVENT] ⚠️ 抽卡按钮 #gacha-btn 未找到，稍后重试...');
    }

    // 调试按钮：增加1000积分
    const debugAddBtn = document.getElementById('debug-add-points');
    if (debugAddBtn) {
        debugAddBtn.addEventListener('click', function(e) {
            e.stopPropagation(); // 防止触发父容器事件
            console.log('[DEBUG_GACHA] 调试按钮被点击：增加1000积分');
            if (window.userData) {
                window.userData.spendablePoints += 1000;
                if (typeof window.saveUserData === 'function') {
                    window.saveUserData(window.userData);
                } else if (typeof saveUserData === 'function') {
                    saveUserData(window.userData);
                }
                
                if (typeof window.updateGachaDisplay === 'function') {
                    window.updateGachaDisplay();
                }
                
                if (typeof window.showGachaToast === 'function') {
                    window.showGachaToast('✅ 已成功注入 1000 积分！', 'success');
                } else {
                    alert('✅ 已成功注入 1000 积分！');
                }
            } else {
                console.error('[DEBUG_GACHA] window.userData 未初始化');
            }
        });
        console.log('[GACHA_EVENT] ✅ 调试加分按钮绑定成功');
    }
    
    // 初始化时主动刷新抽卡积分显示
    if (typeof window.updateGachaDisplay === 'function') {
        window.updateGachaDisplay();
        console.log('[GACHA_EVENT] ✅ 初始化抽卡积分显示');
    }
    
    // 抽卡面板展开时更新积分显示
    const gachaAccordion = document.getElementById('gacha-accordion');
    if (gachaAccordion) {
        const accordionHeader = gachaAccordion.querySelector('.label-wrap');
        if (accordionHeader) {
            accordionHeader.addEventListener('click', function() {
                console.log('[GACHA_EVENT] 抽卡面板被展开');
                setTimeout(() => {
                    if (typeof window.updateGachaDisplay === 'function') {
                        window.updateGachaDisplay();
                    }
                }, 100);
            });
            console.log('[GACHA_EVENT] ✅ 抽卡面板展开事件绑定成功');
        }
    } else {
        console.warn('[GACHA_EVENT] ⚠️ 抽卡面板 #gacha-accordion 未找到');
    }
    
    // 背包面板展开时刷新显示
    const inventoryAccordion = document.getElementById('inventory-accordion');
    if (inventoryAccordion) {
        const accordionHeader = inventoryAccordion.querySelector('.label-wrap');
        if (accordionHeader) {
            accordionHeader.addEventListener('click', function() {
                console.log('[GACHA_EVENT] 背包面板被展开');
                setTimeout(() => {
                    if (typeof window.renderInventory === 'function') {
                        window.renderInventory();
                    }
                }, 100);
            });
            console.log('[GACHA_EVENT] ✅ 背包面板展开事件绑定成功');
        }
    } else {
        console.warn('[GACHA_EVENT] ⚠️ 背包面板 #inventory-accordion 未找到');
    }
    
    // 成就面板展开时刷新显示
    const achievementsAccordion = document.getElementById('medal-accordion');
    if (achievementsAccordion) {
        const accordionHeader = achievementsAccordion.querySelector('.label-wrap');
        if (accordionHeader) {
            accordionHeader.addEventListener('click', function() {
                console.log('[ACCORDION_REFRESH] 成就面板被展开');
                setTimeout(() => {
                    const trigger = document.getElementById('achievements-refresh-trigger');
                    if (trigger && trigger.__gradio__) {
                        // 触发Gradio组件更新
                        const currentValue = trigger.value || '';
                        trigger.value = currentValue + ' ';
                        if (trigger.__gradio__.dispatch_event) {
                            trigger.__gradio__.dispatch_event('change');
                        }
                        console.log('[ACCORDION_REFRESH] ✅ 成就面板刷新触发器已触发');
                    }
                }, 100);
            });
            console.log('[ACCORDION_REFRESH] ✅ 成就面板展开事件绑定成功');
        }
    } else {
        console.warn('[ACCORDION_REFRESH] ⚠️ 成就面板 #medal-accordion 未找到');
    }
    
    // 统计数据面板展开时刷新显示
    const statsAccordion = document.querySelector('[id*="学习数据概览"]');
    if (!statsAccordion) {
        // 如果没找到中文ID,尝试查找包含统计关键词的Accordion
        const allAccordions = document.querySelectorAll('.accordion');
        allAccordions.forEach(acc => {
            const label = acc.querySelector('.label-wrap');
            if (label && label.textContent.includes('学习数据')) {
                label.addEventListener('click', function() {
                    console.log('[ACCORDION_REFRESH] 统计面板被展开');
                    setTimeout(() => {
                        const trigger = document.getElementById('stats-refresh-trigger');
                        if (trigger && trigger.__gradio__) {
                            const currentValue = trigger.value || '';
                            trigger.value = currentValue + ' ';
                            if (trigger.__gradio__.dispatch_event) {
                                trigger.__gradio__.dispatch_event('change');
                            }
                            console.log('[ACCORDION_REFRESH] ✅ 统计面板刷新触发器已触发');
                        }
                    }, 100);
                });
                console.log('[ACCORDION_REFRESH] ✅ 统计面板展开事件绑定成功');
            }
        });
    }
}

// 延迟绑定事件(等待DOM加载)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindGachaEvents);
} else {
    // DOM已加载完成,直接绑定
    setTimeout(bindGachaEvents, 500);
}

// Gradio页面刷新后重新绑定
setInterval(() => {
    const gachaBtn = document.getElementById('gacha-btn');
    if (gachaBtn && !gachaBtn.hasAttribute('data-gacha-bound')) {
        console.log('[GACHA_EVENT] 检测到未绑定的抽卡按钮,重新绑定...');
        gachaBtn.setAttribute('data-gacha-bound', 'true');
        bindGachaEvents();
    }
}, 2000);

console.log('[GACHA_EVENT] ✅ 抽卡事件绑定模块加载完成');

// ========== 全局调试函数防护声明 ==========
// 确保 resetGachaPoints 在所有模块加载后仍然可用
if (typeof window.resetGachaPoints !== 'function') {
    console.warn('[EVENT_HANDLER] ⚠️ resetGachaPoints 未找到，重新声明...');
    window.resetGachaPoints = function(points = 1000) {
        if (window.userData) {
            window.userData.spendablePoints = points;
            if (typeof window.saveUserData === 'function') {
                window.saveUserData(window.userData);
            } else {
                // 备用方案：直接保存到localStorage
                try {
                    localStorage.setItem('ai_companion_user_data', JSON.stringify(window.userData));
                } catch (e) {
                    console.error('[resetGachaPoints] 保存失败:', e);
                }
            }
            console.log('[DEBUG] 抽卡积分已重置为:', points);
            if (typeof window.updateGachaDisplay === 'function') {
                window.updateGachaDisplay();
            }
            return '✅ 抽卡积分已设置为 ' + points;
        }
        return '❌ userData 未初始化，请等待页面加载完成';
    };
    console.log('[EVENT_HANDLER] ✅ resetGachaPoints 已重新声明');
} else {
    console.log('[EVENT_HANDLER] ✅ resetGachaPoints 已存在，类型:', typeof window.resetGachaPoints);
}
