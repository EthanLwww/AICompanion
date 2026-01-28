import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config.constants import LEVEL_CONFIG, ACHIEVEMENT_CONFIG, STORAGE_KEY
from utils.logger import logger


class StatsTracker:
    """
    学习统计数据追踪器
    """
    
    def __init__(self):
        # 默认用户数据
        self.default_data = {
            "points": 0,                    # 总积分（升级积分，只增不减）
            "level": 1,                     # 当前等级
            "totalStudyMinutes": 0,         # 总学习分钟数
            "todayStudyMinutes": 0,         # 今日学习分钟数
            "consecutiveDays": 0,           # 连续签到天数
            "lastCheckInDate": None,        # 上次签到日期
            "checkInHistory": [],           # 签到历史（最近 30 天）
            "achievements": [],             # 已解锁成就 ID 列表
            "positiveEmotionMinutes": 0,    # 积极情绪累计分钟
            "earlyEndRestCount": 0,         # 主动结束休息次数
            "firstStudyDate": None,         # 首次学习日期
            "lastStudyDate": None,          # 最后学习日期
            # 数据可视化扩展字段
            "dailyRecords": [],             # 每日学习记录 [{date, studyMinutes, emotions:{}, bestHour}]
            "weeklyReports": [],            # 周报记录
            # ========== 抽卡系统字段 ==========
            "spendablePoints": 0,           # 可消耗积分（用于抽卡）
            "inventory": [],                # 背包 [{itemId, count, obtainedAt}]
            "equipped": {                   # 当前装备
                "avatarFrame": None,        # 头像框ID
                "chatBubble": None,         # 聊天气泡ID
                "theme": None                # 主题皮肤ID
            },
            "gachaHistory": [],             # 抽卡历史（最近50条）
            "totalGachaCount": 0,           # 累计抽卡次数
            "activeBuffs": {                # 激活的增益效果
                "doublePoints": None,       # 双倍积分到期时间
                "focusBoost": None          # 专注加成到期时间
            }
        }
        
        # 初始化用户数据
        self.user_data = self.load_user_data()
    
    def load_user_data(self) -> Dict:
        """从本地存储加载用户数据"""
        try:
            # 这里模拟从localStorage加载数据，实际应用中需要通过Gradio接口实现
            # 目前返回默认数据
            return self.default_data.copy()
        except Exception as e:
            print(f"加载用户数据失败: {e}")
            return self.default_data.copy()
    
    def save_user_data(self):
        """保存用户数据到本地存储"""
        try:
            # 这里模拟保存到localStorage，实际应用中需要通过Gradio接口实现
            pass
        except Exception as e:
            print(f"保存用户数据失败: {e}")
    
    def get_today_str(self) -> str:
        """获取今日日期字符串"""
        return datetime.now().strftime('%Y-%m-%d')
    
    def calculate_level(self, points: int) -> Dict:
        """根据积分计算等级"""
        for level_info in reversed(LEVEL_CONFIG):
            if points >= level_info["minPoints"]:
                return level_info
        return LEVEL_CONFIG[0]  # 默认返回第一级
    
    def get_next_level_points(self, current_level: int) -> Optional[int]:
        """获取下一级所需积分"""
        next_level = next((l for l in LEVEL_CONFIG if l["level"] == current_level + 1), None)
        return next_level["minPoints"] if next_level else None
    
    def add_points(self, amount: int, reason: str = "") -> Dict[str, any]:
        """添加积分（同时增加升级积分与可消耗积分）"""
        old_level = self.user_data["level"]
        self.user_data["points"] += amount  # 升级积分（只增不减）
        
        # 同步增加可消耗积分（用于抽卡）
        if "spendablePoints" not in self.user_data:
            self.user_data["spendablePoints"] = 0
        self.user_data["spendablePoints"] += amount
        
        logger.info(f"Points added: +{amount} (Reason: {reason}). Total Points: {self.user_data['points']}, Spendable: {self.user_data['spendablePoints']}")
        
        # 重新计算等级
        new_level_info = self.calculate_level(self.user_data["points"])
        self.user_data["level"] = new_level_info["level"]
        
        # 检查是否升级
        leveled_up = new_level_info["level"] > old_level
        
        return {
            "leveled_up": leveled_up,
            "old_level": old_level,
            "new_level": new_level_info,
            "total_points": self.user_data["points"]
        }
    
    def handle_check_in(self) -> Dict[str, any]:
        """处理每日签到"""
        today = self.get_today_str()
        
        # 如果是新的一天，重置今日学习分钟数
        if self.user_data["lastCheckInDate"] != today:
            self.user_data["todayStudyMinutes"] = 0
        
        # 检查是否是新签到
        is_new_checkin = self.user_data["lastCheckInDate"] != today
        
        if is_new_checkin:
            # 检查是否连续签到
            if self.user_data["lastCheckInDate"]:
                last_date = datetime.strptime(self.user_data["lastCheckInDate"], '%Y-%m-%d')
                today_date = datetime.strptime(today, '%Y-%m-%d')
                diff_days = (today_date - last_date).days
                
                if diff_days == 1:
                    self.user_data["consecutiveDays"] += 1
                else:
                    self.user_data["consecutiveDays"] = 1
            else:
                self.user_data["consecutiveDays"] = 1
            
            # 更新签到日期
            self.user_data["lastCheckInDate"] = today
            
            # 更新签到历史
            if today not in self.user_data["checkInHistory"]:
                self.user_data["checkInHistory"].append(today)
                # 只保留最近 30 天
                if len(self.user_data["checkInHistory"]) > 30:
                    self.user_data["checkInHistory"] = self.user_data["checkInHistory"][-30:]
            
            # 签到奖励积分（连续天数越多奖励越高）
            bonus = min(10 + self.user_data["consecutiveDays"] * 2, 50)
            self.user_data["points"] += bonus  # 升级积分
            
            # 同步增加可消耗积分
            if "spendablePoints" not in self.user_data:
                self.user_data["spendablePoints"] = 0
            self.user_data["spendablePoints"] += bonus
            
            # 保存数据
            self.save_user_data()
            
            return {
                "is_new": True,
                "bonus": bonus,
                "consecutive_days": self.user_data["consecutiveDays"]
            }
        
        # 不是新签到
        return {
            "is_new": False,
            "bonus": 0,
            "consecutive_days": self.user_data["consecutiveDays"]
        }
    
    def record_study_minute(self):
        """记录一分钟学习时间"""
        # 增加总学习时间和今日学习时间
        self.user_data["totalStudyMinutes"] += 1
        self.user_data["todayStudyMinutes"] += 1
        
        # 记录到每日记录
        today_record = self.get_today_record()
        today_record["studyMinutes"] += 1
        
        # 记录到小时分布
        hour = datetime.now().hour
        if str(hour) not in today_record["hourlyMinutes"]:
            today_record["hourlyMinutes"][str(hour)] = 0
        today_record["hourlyMinutes"][str(hour)] += 1
        
        # 添加基础积分
        self.add_points(1, "study_minute")
        
        # 检查连续学习奖励
        if self.user_data["todayStudyMinutes"] % 30 == 0:
            self.add_points(10, "continuous_learning_bonus")
        
        # 保存数据
        self.save_user_data()
    
    def get_today_record(self):
        """获取或创建今日记录"""
        today = self.get_today_str()
        
        # 查找今天的记录
        today_record = next((r for r in self.user_data["dailyRecords"] if r["date"] == today), None)
        
        if not today_record:
            today_record = {
                "date": today,
                "studyMinutes": 0,
                "emotions": {"happy": 0, "neutral": 0, "sad": 0, "angry": 0, "fearful": 0, "disgusted": 0, "surprised": 0},
                "hourlyMinutes": {},  # {hour: minutes}
                "focusScore": 0,      # 专注度得分
                "emotionSamples": 0,  # 情绪采样次数
                "noFaceCount": 0,     # 走神次数（无人脸检测）
                "totalSamples": 0,    # 总采样次数（包括走神）
                "maxConsecutiveFocus": 0,  # 最长连续专注时长（分钟）
                "currentConsecutiveFocus": 0  # 当前连续专注时长
            }
            self.user_data["dailyRecords"].append(today_record)
            
            # 只保留最近 60 天
            if len(self.user_data["dailyRecords"]) > 60:
                self.user_data["dailyRecords"] = self.user_data["dailyRecords"][-60:]
        
        return today_record
    
    def record_emotion(self, emotion: str, confidence: float = 0.0):
        """记录情绪数据"""
        today_record = self.get_today_record()
        today_record["totalSamples"] += 1
        
        # 更新情绪计数
        if emotion in today_record["emotions"]:
            today_record["emotions"][emotion] += 1
            today_record["emotionSamples"] += 1
        
        # 判断是否为专注状态（开心/平静，且置信度 > 40%）
        is_focused = (emotion in ['happy', 'neutral']) and confidence > 0.4
        
        if is_focused:
            today_record["currentConsecutiveFocus"] += 1
            if today_record["currentConsecutiveFocus"] > today_record["maxConsecutiveFocus"]:
                today_record["maxConsecutiveFocus"] = today_record["currentConsecutiveFocus"]
        else:
            today_record["currentConsecutiveFocus"] = 0
        
        # 计算综合专注度得分
        self._calculate_focus_score(today_record)
    
    def record_no_face(self):
        """记录走神（无人脸检测）"""
        today_record = self.get_today_record()
        today_record["noFaceCount"] += 1
        today_record["totalSamples"] += 1
        today_record["currentConsecutiveFocus"] = 0  # 走神打断连续专注
        
        # 重新计算专注度
        self._calculate_focus_score(today_record)
    
    def _calculate_focus_score(self, record: Dict):
        """计算综合专注度得分"""
        if record["totalSamples"] == 0:
            record["focusScore"] = 0
            return
        
        # 1. 积极情绪得分（满分 60 分）
        positive_count = record["emotions"]["happy"] + record["emotions"]["neutral"]
        positive_ratio = record["emotionSamples"] > 0 and positive_count / record["emotionSamples"] or 0
        emotion_score = positive_ratio * 60
        
        # 2. 出勤得分（满分 30 分）- 检测到人脸的比例
        attendance_ratio = record["emotionSamples"] / record["totalSamples"] if record["totalSamples"] > 0 else 0
        attendance_score = attendance_ratio * 30
        
        # 3. 连续专注加分（满分 10 分）
        # 每 10 次连续专注（约 3 秒）加 1 分，上限 10 分
        consecutive_bonus = min(record["maxConsecutiveFocus"] / 10, 10)
        
        # 综合得分
        score = emotion_score + attendance_score + consecutive_bonus
        record["focusScore"] = round(min(max(score, 0), 100))  # 确保在 0-100 范围内
    
    def increment_early_end_rest(self):
        """增加主动结束休息次数"""
        self.user_data["earlyEndRestCount"] += 1
        self.save_user_data()
    
    def get_weekly_data(self) -> List[Dict]:
        """获取本周学习数据"""
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())  # 周一开始
        
        week_data = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            record = next((r for r in self.user_data["dailyRecords"] if r["date"] == date_str), None)
            day_name = ['一', '二', '三', '四', '五', '六', '日'][i]
            
            week_data.append({
                "date": date_str,
                "day": day_name,
                "studyMinutes": record["studyMinutes"] if record else 0,
                "focusScore": record["focusScore"] if record else 0
            })
        
        return week_data
    
    def get_monthly_data(self) -> int:
        """获取本月学习数据"""
        today = datetime.now()
        year, month = today.year, today.month
        
        # 获取当月的天数
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        month_start = datetime(year, month, 1)
        month_end = next_month - timedelta(days=1)
        
        total_minutes = 0
        for day_offset in range(month_end.day):
            day = datetime(year, month, day_offset + 1).strftime('%Y-%m-%d')
            record = next((r for r in self.user_data["dailyRecords"] if r["date"] == day), None)
            if record:
                total_minutes += record["studyMinutes"]
        
        return total_minutes
    
    def get_best_study_hours(self) -> List[Dict]:
        """获取最佳学习时段"""
        hourly_total = {}
        for record in self.user_data["dailyRecords"]:
            if "hourlyMinutes" in record:
                for hour, mins in record["hourlyMinutes"].items():
                    if hour not in hourly_total:
                        hourly_total[hour] = 0
                    hourly_total[hour] += mins
        
        # 找出前 3 个最佳时段
        sorted_hours = sorted(hourly_total.items(), key=lambda x: x[1], reverse=True)[:3]
        return [{
            "hour": int(hour),
            "minutes": mins,
            "label": f"{hour}:00 - {int(hour)+1}:00"
        } for hour, mins in sorted_hours]
    
    def get_stats_summary(self) -> Dict:
        """获取统计摘要"""
        return {
            "points": self.user_data["points"],
            "level": self.user_data["level"],
            "totalStudyMinutes": self.user_data["totalStudyMinutes"],
            "todayStudyMinutes": self.user_data["todayStudyMinutes"],
            "consecutiveDays": self.user_data["consecutiveDays"],
            "achievementsCount": len(self.user_data["achievements"]),
            "todayFocusScore": self.get_today_record()["focusScore"]
        }