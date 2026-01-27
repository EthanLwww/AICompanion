from typing import List, Dict, Tuple
from .stats_tracker import StatsTracker
from config.constants import ACHIEVEMENT_CONFIG


class AchievementManager:
    """
    成就管理系统
    """
    
    def __init__(self, stats_tracker: StatsTracker):
        self.stats_tracker = stats_tracker
        self.achievement_config = ACHIEVEMENT_CONFIG
    
    def check_and_unlock_achievements(self) -> List[Dict]:
        """
        检查并解锁成就
        返回新解锁的成就列表
        """
        unlocked_achievements = []
        current_achievements = self.stats_tracker.user_data["achievements"]
        
        for achievement in self.achievement_config:
            achievement_id = achievement["id"]
            
            # 如果成就已经解锁，跳过
            if achievement_id in current_achievements:
                continue
            
            # 检查成就条件
            if self._check_achievement_condition(achievement):
                # 解锁成就
                current_achievements.append(achievement_id)
                
                # 添加积分奖励
                points_reward = achievement.get("points", 0)
                if points_reward > 0:
                    self.stats_tracker.add_points(points_reward, f"achievement_{achievement_id}")
                
                # 添加到解锁列表
                unlocked_achievements.append(achievement)
        
        # 保存数据
        self.stats_tracker.save_user_data()
        
        return unlocked_achievements
    
    def _check_achievement_condition(self, achievement: Dict) -> bool:
        """
        检查特定成就的解锁条件
        """
        user_data = self.stats_tracker.user_data
        achievement_id = achievement["id"]
        
        # 根据成就ID检查不同条件
        if achievement_id == "first_study":
            return user_data["totalStudyMinutes"] > 0
        elif achievement_id == "study_30min":
            return user_data["totalStudyMinutes"] >= 30
        elif achievement_id == "study_1hour":
            return user_data["totalStudyMinutes"] >= 60
        elif achievement_id == "study_5hours":
            return user_data["totalStudyMinutes"] >= 300
        elif achievement_id == "study_10hours":
            return user_data["totalStudyMinutes"] >= 600
        elif achievement_id == "study_24hours":
            return user_data["totalStudyMinutes"] >= 1440  # 24*60
        elif achievement_id == "checkin_3days":
            return user_data["consecutiveDays"] >= 3
        elif achievement_id == "checkin_7days":
            return user_data["consecutiveDays"] >= 7
        elif achievement_id == "checkin_14days":
            return user_data["consecutiveDays"] >= 14
        elif achievement_id == "checkin_30days":
            return user_data["consecutiveDays"] >= 30
        elif achievement_id == "early_rest_5":
            return user_data["earlyEndRestCount"] >= 5
        elif achievement_id == "early_rest_20":
            return user_data["earlyEndRestCount"] >= 20
        elif achievement_id == "level_5":
            return user_data["level"] >= 5
        elif achievement_id == "level_10":
            return user_data["level"] >= 10
        elif achievement_id == "points_1000":
            return user_data["points"] >= 1000
        elif achievement_id == "points_5000":
            return user_data["points"] >= 5000
        else:
            # 默认返回False，对于未定义的成就ID
            return False
    
    def get_achievement_progress(self, achievement_id: str) -> Tuple[bool, float]:
        """
        获取特定成就的进度
        返回: (是否已解锁, 进度百分比)
        """
        user_data = self.stats_tracker.user_data
        
        # 检查是否已解锁
        if achievement_id in user_data["achievements"]:
            return (True, 100.0)
        
        # 获取成就配置
        achievement = next((a for a in self.achievement_config if a["id"] == achievement_id), None)
        if not achievement:
            return (False, 0.0)
        
        # 计算进度
        progress = 0.0
        if achievement_id == "first_study":
            progress = 100.0 if user_data["totalStudyMinutes"] > 0 else 0.0
        elif achievement_id == "study_30min":
            progress = min(user_data["totalStudyMinutes"] / 30 * 100, 100.0)
        elif achievement_id == "study_1hour":
            progress = min(user_data["totalStudyMinutes"] / 60 * 100, 100.0)
        elif achievement_id == "study_5hours":
            progress = min(user_data["totalStudyMinutes"] / 300 * 100, 100.0)
        elif achievement_id == "study_10hours":
            progress = min(user_data["totalStudyMinutes"] / 600 * 100, 100.0)
        elif achievement_id == "study_24hours":
            progress = min(user_data["totalStudyMinutes"] / 1440 * 100, 100.0)
        elif achievement_id == "checkin_3days":
            progress = min(user_data["consecutiveDays"] / 3 * 100, 100.0)
        elif achievement_id == "checkin_7days":
            progress = min(user_data["consecutiveDays"] / 7 * 100, 100.0)
        elif achievement_id == "checkin_14days":
            progress = min(user_data["consecutiveDays"] / 14 * 100, 100.0)
        elif achievement_id == "checkin_30days":
            progress = min(user_data["consecutiveDays"] / 30 * 100, 100.0)
        elif achievement_id == "early_rest_5":
            progress = min(user_data["earlyEndRestCount"] / 5 * 100, 100.0)
        elif achievement_id == "early_rest_20":
            progress = min(user_data["earlyEndRestCount"] / 20 * 100, 100.0)
        elif achievement_id == "level_5":
            progress = min(user_data["level"] / 5 * 100, 100.0)
        elif achievement_id == "level_10":
            progress = min(user_data["level"] / 10 * 100, 100.0)
        elif achievement_id == "points_1000":
            progress = min(user_data["points"] / 1000 * 100, 100.0)
        elif achievement_id == "points_5000":
            progress = min(user_data["points"] / 5000 * 100, 100.0)
        
        return (False, progress)
    
    def get_all_achievements_status(self) -> List[Dict]:
        """
        获取所有成就的状态
        """
        user_data = self.stats_tracker.user_data
        statuses = []
        
        for achievement in self.achievement_config:
            achievement_id = achievement["id"]
            unlocked = achievement_id in user_data["achievements"]
            _, progress = self.get_achievement_progress(achievement_id)
            
            statuses.append({
                **achievement,
                "unlocked": unlocked,
                "progress": progress
            })
        
        return statuses
    
    def get_unlocked_achievements(self) -> List[Dict]:
        """
        获取已解锁的成就
        """
        user_data = self.stats_tracker.user_data
        unlocked_ids = set(user_data["achievements"])
        
        return [
            ach for ach in self.achievement_config
            if ach["id"] in unlocked_ids
        ]
    
    def get_recent_achievements(self, count: int = 5) -> List[Dict]:
        """
        获取最近解锁的成就
        """
        user_data = self.stats_tracker.user_data
        recent_ids = user_data["achievements"][-count:]  # 获取最近的几个ID
        
        return [
            next((ach for ach in self.achievement_config if ach["id"] == aid), None)
            for aid in recent_ids
        ]