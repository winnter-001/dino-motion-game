# ===============================================
# 跑步小恐龍動作偵測遊戲
# 製作人：沈敬諺
# ===============================================

import cv2
import mediapipe as mp
import numpy as np
import streamlit as st
import time
import random
import pygame
import os

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
# ✅ Streamlit UI 設定有沒有甚麼
st.set_page_config(page_title="跑步小恐龍", layout="wide")
st.title("🏃‍♂️ 跑步小恐龍遊戲")
st.write("選擇動作控制跳躍，舉右手無敵，舉左手攻擊Boss，撐過第二階段Boss即可通關！")

# 初始化 session_state
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "coins" not in st.session_state:
    st.session_state.coins = 0
if "lives" not in st.session_state:
    st.session_state.lives = 5
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False  # 管理員模式
if "start_bpm" not in st.session_state:
    st.session_state.start_bpm = 0
if "end_bpm" not in st.session_state:
    st.session_state.end_bpm = 0
if "age" not in st.session_state:
    st.session_state.age = 0

lives = st.session_state.lives
coins = st.session_state.coins

# Sidebar 設定
st.sidebar.subheader("🎯 選擇難度")
available_difficulties = ["簡單"]
if coins >= 10 or st.session_state.admin_mode:
    available_difficulties.append("中等")
if coins >= 30 or st.session_state.admin_mode:
    available_difficulties.append("困難")
difficulty = st.sidebar.radio("難度", available_difficulties)

# 🔐 管理員模式
st.sidebar.subheader("🔐 管理員模式")
if not st.session_state.admin_mode:
    if st.sidebar.button("👑 啟用管理員模式"):
        st.session_state.admin_mode = True
        st.sidebar.success("👑 管理員模式已啟動！")
else:
    st.sidebar.info("👑 管理員模式已啟動")

# 年齡輸入
st.sidebar.subheader("🧑 請輸入年齡")
age_input = st.sidebar.number_input("請輸入年齡", min_value=5, max_value=100, step=1, key="age_input")
if age_input != 0:
    st.session_state.age = age_input

# Sidebar 作者浮水印
st.sidebar.markdown("**👑 製作者：沈敬諺**")

# 心率輸入
st.sidebar.subheader("❤️ 遊戲開始前請測量心率")
st.session_state.start_bpm = st.sidebar.number_input("請輸入起始心率 BPM", min_value=30, max_value=200, step=1)

# 跳躍動作選擇
st.sidebar.subheader("🕹️ 跳躍動作選擇")
jump_option = st.sidebar.radio(
    "選擇要使用的跳躍動作：",
    ["雙手舉高", "站起動作", "抬腿"]
)

# 開始按鈕
if not st.session_state.game_started:
    if st.button("🚀 開始遊戲"):
        st.session_state.game_started = True
        st.session_state.game_over = False
    st.stop()
# MediaPipe 初始化
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Pygame 初始化
pygame.init()
width, height = 800, 400
screen = pygame.Surface((width, height))
clock = pygame.time.Clock()

# 音效
try:
    pygame.mixer.init()
    pygame.mixer.music.load(os.path.join(BASE_PATH, "0317.mp3"))
    coin_sound = pygame.mixer.Sound(os.path.join(BASE_PATH, "coin.mp3"))
    heart_sound = pygame.mixer.Sound(os.path.join(BASE_PATH, "heart.mp3"))
    hurt_sound = pygame.mixer.Sound(os.path.join(BASE_PATH, "hurt.mp3"))
    sound_available = True
except pygame.error:
    # 雲端環境，音效初始化失敗，禁用音效
    coin_sound = None
    heart_sound = None
    hurt_sound = None
    sound_available = False
    
# 顏色設定
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GROUND_HEIGHT = 300
FPS = 30

# 讀取圖片
player_img = pygame.image.load(os.path.join(BASE_PATH, 'player.jpg'))
player_img = pygame.transform.scale(player_img, (40, 40))
cactus_img = pygame.image.load(os.path.join(BASE_PATH, 'cactus.jpg'))
cactus_img = pygame.transform.scale(cactus_img, (30, 50))
rock_img = pygame.image.load(os.path.join(BASE_PATH, 'rock.jpg'))
rock_img = pygame.transform.scale(rock_img, (40, 30))
crow_img = pygame.image.load(os.path.join(BASE_PATH, 'crow.jpg'))
crow_img = pygame.transform.scale(crow_img, (40, 30))
coin_img = pygame.image.load(os.path.join(BASE_PATH, 'coin.jpg'))
coin_img = pygame.transform.scale(coin_img, (20, 20))
heart_img = pygame.image.load(os.path.join(BASE_PATH, 'heart.jpg'))
heart_img = pygame.transform.scale(heart_img, (20, 20))
boss1_img = pygame.image.load(os.path.join(BASE_PATH, 'boss1.jpg'))
boss1_img = pygame.transform.scale(boss1_img, (100, 100))
boss2_img = pygame.image.load(os.path.join(BASE_PATH, 'boss2.jpg'))
boss2_img = pygame.transform.scale(boss2_img, (100, 100))

# 小恐龍參數
player_x, player_y = 100, GROUND_HEIGHT - 40
player_width, player_height = 40, 40
player_jump = False
jump_strength = 14
jump_velocity = 0
gravity = 1
max_lives = 5
max_player_x = 400
return_speed = 2

# 無敵技能
invincible = False
invincible_timer = 0
invincible_duration = 5 * 30
invincible_cooldown = 30 * 30
cooldown_timer = 0
skill_timer = 0

# 障礙物 & 金幣 & 血量
obstacle_types = [
    {"name": "cactus", "img": cactus_img, "width": 30, "height": 50, "y_offset": 50},
    {"name": "rock", "img": rock_img, "width": 40, "height": 30, "y_offset": 30},
    {"name": "crow", "img": crow_img, "width": 40, "height": 30, "y_offset": 150},
]
obstacles = []
coins_list = []
hearts_list = []
obstacle_speed = 5
coin_spawn_interval = 60
frame_counter = 0
heart_count = 5

# Boss
boss_active = False
boss_spawned = False
boss = None
boss_attacks = []
boss_phase = 1
boss_auto_damage_timer = 0
boss_health = 10
second_phase_health = 15

# 攝影機選擇
st.sidebar.subheader("📷 攝影機選擇")
camera_source = st.sidebar.radio("選擇攝影機", ["電腦攝影機", "手機攝影機"])
MOBILE_CAM_URL = "http://192.168.x.x:8080/video"
cap = cv2.VideoCapture(MOBILE_CAM_URL if camera_source == "手機攝影機" else 0)
if not cap.isOpened():
    st.error("❌ 無法開啟攝影機，請檢查設備！")
    st.stop()

# Streamlit 顯示元件
game_display = st.image([])
camera_display = st.image([])
life_display = st.sidebar.empty()
coin_display = st.sidebar.empty()
score_display = st.sidebar.empty()
boss_display = st.sidebar.empty()
invincible_display = st.sidebar.empty()
time_remaining_display = st.sidebar.empty()

# 動作偵測變數
jump_counter = 0
hip_history = []

# 動作偵測 function
def detect_motions(landmarks):
    global jump_counter, hip_history
    if not landmarks:
        return False, False, False, False
    left_hand = landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST].y
    right_hand = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].y
    left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER].y
    right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER].y
    left_knee = landmarks.landmark[mp_pose.PoseLandmark.LEFT_KNEE].y
    right_knee = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_KNEE].y
    left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP].y
    right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP].y
    hip_avg = (left_hip + right_hip) / 2

    knee_diff = abs(left_knee - right_knee)
    is_running = knee_diff > 0.07

    is_jump = False
    if jump_option == "雙手舉高":
        if (left_hand < left_shoulder - 0.08) and (right_hand < right_shoulder - 0.08):
            jump_counter += 1
        else:
            jump_counter = 0
        if jump_counter >= 2:
            is_jump = True
            jump_counter = 0

    elif jump_option == "站起動作":
        hip_history.append(hip_avg)
        if len(hip_history) > 10:
            hip_history.pop(0)
        if len(hip_history) == 10:
            smooth_hips = np.convolve(hip_history, np.ones(3)/3, mode='valid')
            max_hip = max(hip_history)
            min_hip = min(hip_history)
            rising = [smooth_hips[i+1] - smooth_hips[i] < -0.02 for i in range(len(smooth_hips)-1)]
            if rising.count(True) >= 3 and (max_hip - min_hip) > 0.15:
                is_jump = True
                hip_history = []

    elif jump_option == "抬腿":
        if (left_knee < left_hip - 0.07) or (right_knee < right_hip - 0.07):
            jump_counter += 1
        else:
            jump_counter = 0
        if jump_counter >= 2:
            is_jump = True
            jump_counter = 0

    is_right_up = (right_hand < right_shoulder - 0.08) and (left_hand > left_shoulder)
    is_left_up = (left_hand < left_shoulder - 0.08) and (right_hand > right_shoulder)

    return is_running, is_jump, is_right_up, is_left_up
# 主迴圈變數
running = True
frame_counter = 0
boss_attack_cooldown = 0
total_time = 90 if difficulty == "簡單" else 120 if difficulty == "中等" else 150
time_left = total_time

while running:
    screen.fill(WHITE)
    pygame.draw.line(screen, BLACK, (0, GROUND_HEIGHT), (width, GROUND_HEIGHT), 3)

    # 攝影機
    ret, frame = cap.read()
    if not ret:
        st.error("❌ 攝影機讀取錯誤")
        break
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(frame_rgb)
    is_running, is_jumping, is_right_up, is_left_up = detect_motions(results.pose_landmarks) if results.pose_landmarks else (False, False, False, False)

    # 小恐龍跑步
    if is_running:
        if player_x < max_player_x:
            player_x += 8 if invincible else 5
    else:
        if player_x > 100:
            player_x -= return_speed

    # 跳躍
    if is_jumping and not player_jump:
        player_jump = True
        jump_velocity = jump_strength
    if player_jump:
        player_y -= jump_velocity
        jump_velocity -= gravity
        if player_y >= GROUND_HEIGHT - 40:
            player_y = GROUND_HEIGHT - 40
            player_jump = False

    # 無敵技能
    if is_right_up and cooldown_timer == 0 and not invincible:
        skill_timer += 1
        if skill_timer >= 1 * FPS:
            invincible = True
            invincible_timer = invincible_duration
            cooldown_timer = invincible_cooldown
            st.sidebar.success("⚡ 無敵衝刺啟動！")
            skill_timer = 0
    elif skill_timer > 0:
        skill_timer -= 1

    if invincible:
        invincible_timer -= 1
        if invincible_timer <= 0:
            invincible = False
            st.sidebar.info("🕒 無敵結束")
    if cooldown_timer > 0:
        cooldown_timer -= 1

    # 無敵狀態提示
    if invincible:
        invincible_display.write("🟡 無敵中！")
    elif cooldown_timer > 0:
        invincible_display.write(f"❄️ 技能冷卻中：{cooldown_timer // FPS}秒")
    else:
        invincible_display.write("✨ 技能可用")

    # 畫小恐龍
    screen.blit(player_img, (player_x, player_y))

    frame_counter += 1

    # 時間倒數
    if frame_counter % FPS == 0:
        time_left -= 1
        time_remaining_display.write(f"⏰ 剩餘時間: {time_left} 秒")
        if time_left <= 0:
            running = False
            st.session_state.game_over = True
            st.warning("⏰ 時間到！遊戲結束")
    # 產生障礙物
    obstacle_spawn_interval = 80 if difficulty == "簡單" else 60 if difficulty == "中等" else 40
    if frame_counter % obstacle_spawn_interval == 0 and boss_phase != 2:
        obstacle_type = random.choice(obstacle_types)
        obstacles.append({
            "x": width,
            "y": GROUND_HEIGHT - obstacle_type["y_offset"],
            "type": obstacle_type
        })

    # 生成金幣
    if frame_counter % coin_spawn_interval == 0 and boss_phase != 2:
        coins_list.append([random.randint(200, width), GROUND_HEIGHT - 30])

    # 生成回血
    if heart_count > 0 and frame_counter % 300 == 0 and boss_phase != 2:
        hearts_list.append([random.randint(200, width), GROUND_HEIGHT - 30])
        heart_count -= 1

    # 更新障礙物
    for obstacle in obstacles[:]:
        obstacle["x"] -= obstacle_speed
        screen.blit(obstacle["type"]["img"], (obstacle["x"], obstacle["y"]))
        if obstacle["x"] < -obstacle["type"]["width"]:
            obstacles.remove(obstacle)
        player_rect = pygame.Rect(player_x + 5, player_y, player_width - 10, player_height)
        obstacle_rect = pygame.Rect(obstacle["x"], obstacle["y"], obstacle["type"]["width"], obstacle["type"]["height"])
        if player_rect.colliderect(obstacle_rect):
            if not invincible:
                lives = max(0, lives - 1)
                st.session_state.lives = lives
                if hurt_sound:
                    hurt_sound.play()
            obstacles.remove(obstacle)
            if lives == 0:
                running = False
                st.session_state.game_over = True

    # 更新金幣
    for coin in coins_list[:]:
        coin[0] -= obstacle_speed
        screen.blit(coin_img, (coin[0], coin[1]))
        if player_x + player_width > coin[0] and player_x < coin[0] + 20 and player_y + player_height > coin[1]:
            coins += 1
            st.session_state.coins = coins
            coins_list.remove(coin)
            if coin_sound:
                coin_sound.play()


    # 回回血
    for heart in hearts_list[:]:
        heart[0] -= obstacle_speed
        screen.blit(heart_img, (heart[0], heart[1]))
        if player_x + player_width > heart[0] and player_x < heart[0] + 20 and player_y + player_height > heart[1]:
            if lives < max_lives:
                lives += 1
                st.session_state.lives = lives
                if hurt_sound:
                    hurt_sound.play()
            hearts_list.remove(heart)

    # === Boss 第一階段 ===
    if difficulty == "困難" and (coins >= 30 or st.session_state.admin_mode) and not boss_spawned:
        boss = {"health": 10, "max_health": 10, "x": 600, "y": GROUND_HEIGHT - 100,
                "attack_interval": 150, "attack_timer": 0, "heal_interval": 200, "heal_timer": 0}
        boss_attacks = []
        boss_active = True
        boss_spawned = True
        boss_attack_cooldown = FPS
        st.sidebar.warning("⚠️ Boss 出現！左手攻擊，右手無敵，雙手跳躍！")
    # === Boss 第一階段邏輯 ===
    if boss_active and boss_phase == 1:
        # 畫 Boss
        screen.blit(boss1_img, (boss["x"] - 50, boss["y"] - 50))
        health_ratio = boss["health"] / boss["max_health"]
        pygame.draw.rect(screen, (255,0,0), (boss["x"] - 50, boss["y"] - 70, 100 * health_ratio, 10))
        boss_display.empty()
        boss_display.write(f"👹 Boss 血量: {boss['health']} / {boss['max_health']}")

        # Boss 攻擊
        boss["attack_timer"] += 1
        if boss["attack_timer"] >= boss["attack_interval"]:
            boss["attack_timer"] = 0
            boss_attacks.append({"x": boss["x"], "y": boss["y"]})

        # Boss回血
        boss["heal_timer"] += 1
        if boss["heal_timer"] >= boss["heal_interval"]:
            if boss["health"] < boss["max_health"]:
                boss["health"] += 1
                st.sidebar.info("👹 Boss 回血 +1！")
            boss["heal_timer"] = 0

        for attack in boss_attacks[:]:
            attack["x"] -= 7
            pygame.draw.circle(screen, (255, 100, 0), (attack["x"], attack["y"]), 10)
            attack_rect = pygame.Rect(attack["x"], attack["y"], 10, 10)
            player_rect = pygame.Rect(player_x + 5, player_y, player_width - 10, player_height)
            if player_rect.colliderect(attack_rect):
                if not invincible:
                    lives = max(0, lives - 1)
                    st.session_state.lives = lives
                    if hurt_sound:
                        hurt_sound.play()
                boss_attacks.remove(attack)
                if lives == 0:
                    running = False
                    st.session_state.game_over = True
            if attack["x"] < 0:
                boss_attacks.remove(attack)

        # 玩家攻擊 Boss
        if results.pose_landmarks and boss_attack_cooldown == 0:
            if is_left_up:
                boss["health"] -= 1
                boss_attack_cooldown = FPS // 2
                st.sidebar.info("👊 攻擊 Boss！")
                if boss["health"] <= 0:
                    st.sidebar.warning("⚠️ Boss 進入第二階段！雙邊瘋狂攻擊！")
                    boss_phase = 2
                    boss_health = second_phase_health
                    boss_auto_damage_timer = 0
                    boss_attacks = []
                    player_x = width // 2 - player_width // 2
                    frame_counter = 0

        if boss_attack_cooldown > 0:
            boss_attack_cooldown -= 1

    # === Boss 第二階段 ===
    if boss_active and boss_phase == 2:
        player_x = width // 2 - player_width // 2
        left_boss_x = 100
        right_boss_x = 700
        # 畫左右 Boss
        screen.blit(boss2_img, (left_boss_x - 50, GROUND_HEIGHT - 150))
        screen.blit(boss2_img, (right_boss_x - 50, GROUND_HEIGHT - 150))

        # 血量條
        health_ratio = boss_health / second_phase_health
        pygame.draw.rect(screen, (255,0,0), (width // 2 - 50, 50, 100 * health_ratio, 10))
        boss_display.empty()
        boss_display.write(f"👹 Boss 第二階段 血量: {boss_health} / {second_phase_health}")

        # 瘋狂攻擊
        if frame_counter % 20 == 0:
          for side in ["left", "right"]:
            attack_height_choice = random.choice(["high", "middle", "low"])
            if attack_height_choice == "high":
                attack_y = GROUND_HEIGHT - 90
            elif attack_height_choice == "middle":
                attack_y = GROUND_HEIGHT - 60
            else:
                attack_y = GROUND_HEIGHT - 30
            attack_x = left_boss_x + 30 if side == "left" else right_boss_x - 30
            attack_dir = 1 if side == "left" else -1
            boss_attacks.append({"x": attack_x, "y": attack_y, "dir": attack_dir})

        # 子彈移動 & 碰撞
        for attack in boss_attacks[:]:
            attack["x"] += attack["dir"] * 10
            pygame.draw.circle(screen, (255, 50, 50), (attack["x"], attack["y"]), 10)
            attack_rect = pygame.Rect(attack["x"], attack["y"], 10, 10)
            player_rect = pygame.Rect(player_x + 5, player_y, player_width - 10, player_height)
            if player_rect.colliderect(attack_rect):
                if not invincible:
                    lives = max(0, lives - 1)
                    st.session_state.lives = lives
                boss_attacks.remove(attack)
                if lives == 0:
                    running = False
                    st.session_state.game_over = True
            if attack["x"] < 0 or attack["x"] > width:
                boss_attacks.remove(attack)

        # Boss 每3秒自損
        boss_auto_damage_timer += 1
        if boss_auto_damage_timer >= 3 * FPS:
            boss_health -= 1
            boss_auto_damage_timer = 0
            st.sidebar.info("👹 Boss 承受痛苦 -1 HP！")
            if boss_health <= 0:
                pygame.mixer.music.play()
                for i in range(10):
                    screen.fill((255,0,0))
                    game_array = pygame.surfarray.array3d(screen)
                    game_array = np.fliplr(np.rot90(game_array, k=3))
                    game_display.image(game_array, channels="RGB")
                    time.sleep(0.1)
                running = False
                st.session_state.game_over = True

    # Sidebar 更新
    life_display.write(f"💖 剩餘生命: {lives}")
    coin_display.write(f"🪙 獲得金幣: {coins}")
    score_display.write(f"🎯 當前分數: {coins*10}")

    # 浮水印
    font = pygame.font.SysFont('Arial', 18)
    watermark_text = font.render("沈敬諺製作", True, (100, 100, 100))
    screen.blit(watermark_text, (width - 140, height - 30))

    # 畫面更新
    game_array = pygame.surfarray.array3d(screen)
    game_array = np.fliplr(np.rot90(game_array, k=3))
    game_display.image(game_array, channels="RGB")
    camera_display.image(frame_rgb, channels="RGB")
    clock.tick(FPS)

# === 遊戲結束 ===
if cap.isOpened():
    cap.release()
pygame.quit()

st.success("🎉 遊戲結束！")
st.write("💖 剩餘生命:", lives)
st.write("🪙 獲得金幣:", coins)
st.write("**本遊戲由沈敬諺開發製作**")

st.success("🎉 遊戲結束！")
st.write("💖 剩餘生命:", lives)
st.write("🪙 獲得金幣:", coins)

# ===== 遊戲結束後：年齡 & BPM 總結 =====
st.sidebar.subheader("❤️ 遊戲結束後請再測量心率")
end_bpm_input = st.sidebar.number_input("請輸入結束心率 BPM", min_value=30, max_value=200, step=1, key="end_bpm_input")

# 紀錄結束 bpm
if end_bpm_input != 0:
    st.session_state.end_bpm = end_bpm_input

# 健康分析顯示
if st.session_state.age > 0 and st.session_state.start_bpm > 30 and st.session_state.end_bpm > 30:
    age = st.session_state.age
    bpm_diff = st.session_state.end_bpm - st.session_state.start_bpm
    final_score = coins * 10
    st.write(f"📊 年齡：{age} 歲")
    st.write(f"📊 心率上升值：**{bpm_diff} BPM**")

    # 心率建議
    if bpm_diff < 10:
        st.warning("心率上升太少，建議下次增加動作強度！💪")
    elif 10 <= bpm_diff <= 30:
        st.success("心率變化正常！請繼續保持 👍")
    else:
        st.error("心率上升過高，請注意不要過度負荷 🚨")

    # 年齡 + 分數健康建議
    if age < 18:
        if final_score < 150:
            st.info("建議多多參加運動增強體力！🏃‍♂️")
        else:
            st.success("年輕又有活力！👍")
    elif 18 <= age < 40:
        if final_score < 200:
            st.warning("體能普通，建議持續訓練💪")
        else:
            st.success("體力不錯，保持運動習慣！✨")
    else:
        if final_score < 100:
            st.info("建議適當運動維持健康 🌿")
        else:
            st.success("年紀輕輕不服老，繼續加油！🔥")
else:
    st.info("請在左側完整填入年齡與 BPM 才會顯示健康分析")

# 解鎖提示
if coins >= 30:
    st.success("🔥 恭喜解鎖【困難模式】！")
elif coins >= 10:
    st.info("✨ 恭喜解鎖【中等模式】！")

# 再玩一次
if st.button("🔄 再玩一次"):
    st.session_state.game_started = False
    st.session_state.lives = 5
    st.session_state.coins = 0
    st.session_state.start_bpm = 0
    st.session_state.end_bpm = 0
    st.session_state.age = 0
    st.session_state.end_bpm_input = 0
    st.rerun()
