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
            // 【子题师】详细记录每次检查的状态
            const checkResult = {
                startWebcam_type: typeof window.startWebcam,
                playAlertSound_type: typeof window.playAlertSound,
                stopWebcam_type: typeof window.stopWebcam,
                msgInput_exists: !!document.querySelector('#msg-input')
            };
            console.log('[RECOVERY-CHECK] 第 ' + Math.round(performance.now() / 1000) + ' 秒：检查全局函数状态', checkResult);
            
            if (!window.startWebcam || typeof window.startWebcam !== 'function') {
                console.warn('[RECOVERY-TRIGGER] 検测到全局函数丢失！window.startWebcam = ' + typeof window.startWebcam);
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
