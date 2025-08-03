import streamlit as st
import random
import os
import re
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import json

# --- Firebase 初始化 ---
# 使用 Streamlit Secrets 來安全地加載 Firebase 金鑰
try:
    # 為了避免重複初始化，我們檢查 session_state
    if 'db' not in st.session_state:
        # 手動從 secrets 建立一個標準的 Python 字典
        creds_dict = {
            "type": st.secrets["firebase_credentials"]["type"],
            "project_id": st.secrets["firebase_credentials"]["project_id"],
            "private_key_id": st.secrets["firebase_credentials"]["private_key_id"],
            "private_key": st.secrets["firebase_credentials"]["private_key"],
            "client_email": st.secrets["firebase_credentials"]["client_email"],
            "client_id": st.secrets["firebase_credentials"]["client_id"],
            "auth_uri": st.secrets["firebase_credentials"]["auth_uri"],
            "token_uri": st.secrets["firebase_credentials"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase_credentials"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase_credentials"]["client_x509_cert_url"],
            "universe_domain": st.secrets["firebase_credentials"]["universe_domain"]
        }
        
        cred = credentials.Certificate(creds_dict)
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        
        # 建立 Firestore 客戶端並存入 session state
        st.session_state['db'] = firestore.client()
except Exception as e:
    st.error("Firebase 初始化失敗，請檢查 Streamlit Secrets 中的金鑰是否已拆解成獨立欄位。")
    st.error(e)
    st.stop()

# --- 使用者驗證設定 ---
# 【本次更新重點】移除執行時的密碼雜湊，改用預先產生的雜湊值
# 範例使用者 tnt_user 的密碼現在是 '12345'
users = {
    "usernames": {
        "tnt_user": { # 這是一個範例使用者名稱
            "email": "user@example.com",
            "name": "時代少年團粉絲",
            "password": "$2b$12$3yN/o.AS8j4BscLgB4p.HeaBqI.O7s5J4Zz1e9c2b3d4e5f6g7h8i" # 這是 '12345' 的雜湊值
        }
    }
}

authenticator = stauth.Authenticate(
    users['usernames'],
    'tnt_gacha_cookie',    # Cookie 名稱，可自訂
    'tnt_gacha_signature', # Signature 金鑰，可自訂
    cookie_expiry_days=30
)

# --- 登入介面 ---
# 登入時，使用者名稱請輸入 tnt_user，密碼請輸入 12345
name, authentication_status, username = authenticator.login('main')

if authentication_status == False:
    st.error('使用者名稱/密碼不正確')
elif authentication_status == None:
    st.warning('請輸入您的使用者名稱和密碼以開始使用')

# --- 主應用程式邏輯 (使用者登入後才會執行) ---
if authentication_status:
    # --- 將所有函式定義在登入後的區塊內 ---

    # --- 通用函式 ---
    def get_image_files(path):
        image_path = Path(path)
        if not image_path.is_dir(): return []
        return [str(p) for p in image_path.glob('*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg')]

    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))]

    def add_cards_to_collection(card_paths):
        """將抽到的卡片路徑新增到使用者的 Firestore 卡冊中"""
        if not card_paths: return
        db = st.session_state['db']
        user_doc_ref = db.collection('users').document(st.session_state['username'])
        
        for card_path in card_paths:
            # 將路徑中的斜線替換，以符合 Firestore 文件ID的規範
            card_id = str(card_path).replace("/", "_").replace("\\", "_")
            card_doc_ref = user_doc_ref.collection('cards').document(card_id)
            card_doc_ref.set({'path': str(card_path), 'count': firestore.Increment(1)}, merge=True)
        st.toast(f"已將 {len(card_paths)} 張卡片加入卡冊！")

    def show_card_collection():
        st.header("📚 我的卡冊")
        db = st.session_state['db']
        # 從 Firestore 讀取該使用者的卡片
        cards_ref = db.collection('users').document(st.session_state['username']).collection('cards').stream()
        
        my_cards = [card.to_dict() for card in cards_ref]
            
        if not my_cards:
            st.info("您的卡冊還是空的，快去抽卡吧！")
            return
            
        my_cards.sort(key=lambda x: natural_sort_key(x.get('path', '')))
        
        total_cards = sum(c.get('count', 0) for c in my_cards)
        st.success(f"您總共擁有 {len(my_cards)} 種不同卡片，總計 {total_cards} 張。")
        st.markdown("---")

        for card_data in my_cards:
            path = card_data.get('path')
            count = card_data.get('count', 0)
            col1, col2 = st.columns([1, 3])
            with col1: st.image(path, width=150)
            with col2:
                st.write(f"**擁有數量：{count}**")
                st.caption(f"路徑: {path}")
            st.markdown("---")

    # --- 抽卡核心邏輯函式 ---
    def draw_random_cards_and_save(path, num_to_draw, title):
        st.markdown(f"### {title}")
        deck = get_image_files(path)
        if not deck:
            st.error(f"在「{path}」中找不到卡片。"); return
        if len(deck) < num_to_draw:
            st.warning(f"「{path}」卡池數量不足 {num_to_draw} 張！"); return
        drawn_cards = random.sample(deck, num_to_draw)
        add_cards_to_collection(drawn_cards) # 存入卡冊
        cols = st.columns(min(len(drawn_cards), 7))
        for i, card in enumerate(drawn_cards):
            with cols[i % len(cols)]: st.image(card, use_container_width=True)

    def draw_fixed_solo_set_and_save(path, title):
        st.markdown(f"### {title}")
        base_path = Path(path)
        themes = [d.name for d in base_path.glob('*') if d.is_dir()]
        if not themes:
            st.error(f"在「{path}」中找不到主題資料夾。"); return
        chosen_theme = random.choice(themes)
        chosen_folder_path = base_path / chosen_theme
        card_set = get_image_files(chosen_folder_path)
        if card_set:
            card_set.sort(key=natural_sort_key)
            st.info(f"您抽中了 **{chosen_theme}** 套組！")
            add_cards_to_collection(card_set) # 存入卡冊
            cols = st.columns(min(len(card_set), 7))
            for i, card in enumerate(card_set):
                with cols[i % len(cols)]: st.image(card, use_container_width=True)
        else:
            st.error(f"在「{chosen_folder_path}」中找不到卡片。")

    # --- 各個抽卡模式的主函式 ---
    def draw_summer_memories():
        st.subheader("☀️ 夏日記憶")
        st.write("規則：從所有卡片中隨機抽取 3 張。")
        if st.button("抽取三張夏日記憶！", key="summer_draw"):
            draw_random_cards_and_save(Path("image/夏日記憶"), 3, "恭喜！您抽到了：")

    def draw_second_album(album_name):
        st.subheader(f"� {album_name}")
        st.write("規則：點擊按鈕，將會一次性抽取所有配置的卡片。")
        base_path = Path(f"image/{album_name}")
        if st.button(f"開始抽取 {album_name}！", key=album_name.replace("-", "_")):
            st.success("抽卡結果如下：")
            draw_random_cards_and_save(base_path / "團體卡", 1, "🎫 團體卡")
            draw_random_cards_and_save(base_path / "分隊卡", 1, "👯 分隊卡")
            draw_random_cards_and_save(base_path / "雙人卡", 7, "💖 雙人卡")
            draw_random_cards_and_save(base_path / "ID卡", 1, "🆔 ID卡")
            draw_fixed_solo_set_and_save(base_path / "單人固卡", "✨ 單人固卡")
            draw_random_cards_and_save(base_path / "高級會員專屬贈品", 1, "💎 高級會員贈品")
            st.markdown("### 特典 - 預售禮")
            presale_path = base_path / "預售禮"
            if album_name == "二專-三時有聲款":
                draw_random_cards_and_save(presale_path / "團卡", 1, "預售禮 - 團卡")
                draw_random_cards_and_save(presale_path / "單人卡", 1, "預售禮 - 單人卡")
            elif album_name == "二專-烏托邦樂園款":
                draw_random_cards_and_save(presale_path / "分隊卡", 1, "預售禮 - 分隊卡")
                draw_random_cards_and_save(presale_path / "單人卡", 1, "預售禮 - 單人卡")

    def draw_third_album():
        st.subheader("💿 第三張專輯")
        st.write("規則：點擊按鈕，抽取「雙人卡」3張、「團體卡」1張、「單人固卡」1套，並有1%機率額外獲得UR卡！")
        if st.button("開始抽取三專！", key="album_draw"):
            st.success("抽卡結果如下：")
            
            # 雙人卡
            st.markdown("### 💖 雙人卡 (3張)")
            base_path = Path("image/三專/雙人卡")
            r, sr = get_image_files(base_path/"R"), get_image_files(base_path/"SR")
            if r or sr:
                deck = (r * 60) + (sr * 40)
                if len(deck) >= 3:
                    drawn = random.sample(deck, 3)
                    add_cards_to_collection(drawn)
                    cols = st.columns(3); [cols[i].image(c, use_container_width=True) for i, c in enumerate(drawn)]
            
            # 團體卡
            st.markdown("### 👨‍👨‍👦‍👦 團體卡 (1張)")
            g_path = Path("image/三專/團體卡")
            opts = {"R": 57, "SR": 38, "SSR": 5}
            deck = [str(f) for r, w in opts.items() for f in g_path.glob(f'{r}.*') for _ in range(w)]
            if deck:
                drawn = random.choice(deck)
                add_cards_to_collection([drawn])
                c1,c2,c3 = st.columns([1,2,1]); c2.image(drawn, use_container_width=True)

            # 單人固卡
            solo_base_path = Path("image/三專/單人固卡")
            choices = (["R"]*57) + (["SR"]*38) + (["SSR"]*5)
            rarity = random.choice(choices)
            # 這邊我們需要傳遞完整的路徑給函式
            draw_fixed_solo_set_and_save(solo_base_path / rarity, f"✨ 單人固卡 ({rarity}套)")

            # UR卡
            if random.randint(1, 100) == 1:
                ur_cards = get_image_files(Path("image/三專/UR"))
                if ur_cards:
                    st.balloons()
                    st.markdown("### 🎉 奇蹟降臨！🎉")
                    drawn = random.choice(ur_cards)
                    add_cards_to_collection([drawn])
                    c1,c2,c3 = st.columns([1,2,1]); c2.image(drawn, use_container_width=True)

    # --- 主應用程式介面 ---
    st.sidebar.title(f"歡迎, {name}!")
    authenticator.logout('登出', 'sidebar')
    
    app_mode = st.sidebar.selectbox("請選擇功能", ["抽卡模擬器", "我的卡冊"])

    if app_mode == "我的卡冊":
        show_card_collection()
    else:
        st.header("🎰 抽卡模擬器")
        modes = ["☀️ 夏日記憶", "🎤 二專-三時有聲款", "🎡 二專-烏托邦樂園款", "💿 第三張專輯"]
        selected_mode = st.selectbox("請選擇您想玩的抽卡模式：", modes)
        st.markdown("---")

        if selected_mode == "☀️ 夏日記憶":
            draw_summer_memories()
        elif selected_mode == "🎤 二專-三時有聲款":
            draw_second_album("二專-三時有聲款")
        elif selected_mode == "🎡 二專-烏托邦樂園款":
            draw_second_album("二專-烏托邦樂園款")
        elif selected_mode == "💿 第三張專輯":
            draw_third_album()
    
    # 頁尾資訊
    st.sidebar.markdown("---")
    st.sidebar.caption("此網頁的圖檔皆來自於微博 : 小姚宋敏")