import os
import sqlite3
from pathlib import Path
from config.logger import setup_logging

TAG = __name__

class NFCCardManager:
    def __init__(self, data_dir="data"):
        self.logger = setup_logging()
        self.db_path = os.path.join(data_dir, "nfc_cards.db")
        self._init_database()
    
    def _init_database(self):
        """初始化数据库，创建表结构并添加示例数据"""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建卡片表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS nfc_cards (
            card_id TEXT PRIMARY KEY,
            card_name TEXT NOT NULL,
            topic TEXT NOT NULL,
            prompt TEXT NOT NULL,
            difficulty_level INTEGER DEFAULT 1,
            age_range TEXT DEFAULT '2-3'
        )
        ''')
        
        # 检查是否需要添加示例数据
        cursor.execute("SELECT COUNT(*) FROM nfc_cards")
        if cursor.fetchone()[0] == 0:
            # 添加示例数据
            sample_cards = [
                ("ABCD1234EFGH5678", "小猫卡片", "猫咪", "猫是一种可爱的宠物，有很多有趣的习性", 1, "2-3"),
                ("1234ABCD5678EFGH", "小狗卡片", "狗狗", "狗是人类最忠实的朋友，有很多品种", 1, "2-3"),
                ("AAAA1111BBBB2222", "恐龙卡片", "恐龙", "恐龙是已经灭绝的庞大动物，生活在很久以前", 2, "3-4"),
                ("2222BBBB3333CCCC", "数字卡片", "数字", "数字是我们日常生活中不可或缺的基础知识", 1, "2-3"),
                ("3333CCCC4444DDDD", "颜色卡片", "颜色", "世界上有许多美丽的颜色，红黄蓝是三原色", 1, "2-3")
            ]
            cursor.executemany("INSERT INTO nfc_cards VALUES (?, ?, ?, ?, ?, ?)", sample_cards)
            self.logger.bind(tag=TAG).info(f"已初始化NFC卡片示例数据，共{len(sample_cards)}条")
        
        conn.commit()
        conn.close()
    
    def get_card_info(self, card_id):
        """根据卡片ID查询卡片信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT card_id, card_name, topic, prompt, difficulty_level, age_range FROM nfc_cards WHERE card_id = ?", 
                (card_id,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    "card_id": result[0],
                    "card_name": result[1],
                    "topic": result[2],
                    "prompt": result[3],
                    "difficulty_level": result[4],
                    "age_range": result[5]
                }
            return None
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取卡片信息出错: {str(e)}")
            return None