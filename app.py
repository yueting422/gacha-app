import streamlit as st
import random
import os
import re
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
from passlib.hash import pbkdf2_sha256 # 用於密碼雜湊與驗證
import json
from collections import defaultdict

# --- 網頁基礎設定 ---
st.set_page_config(page_title="TNT抽卡模擬器", page_icon="🎁", layout="wide")

# --- 載入卡片資料 ---
@st.cache_data
def load_card_data():
    """從 card_data.json 載入卡片名稱對照表"""
    try:
        with open('card_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.sidebar.warning("找不到 card_data.json 檔案，卡片將無法顯示名稱。")
        return {}
    except json.JSONDecodeError:
        st.sidebar.error("card_data.json 格式錯誤，請檢查檔案內容。")
        return {}

CARD_DATA = load_card_data()

# --- Firebase 初始化 ---
try:
    if 'db' not in st.session_state:
        creds_dict = {
            "type": st.secrets["firebase_credentials"]["type"],
            "project_id": st.secrets["firebase_credentials"]["project_id"],
            "private_key_id": st.secrets["firebase_credentials"]["private_key_id"],
            "private_key": st.secrets["firebase_credentials"]["private_key"].replace('\\n', '\n'),
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
        st.session_state['db'] = firestore.client()
except Exception as e:
    st.error("Firebase 初始化失敗，請檢查 Streamlit Secrets 中的金鑰。")
    st.error(e)
    st.stop()

db = st.session_state['db']

# --- 通用函式 ---
def get_image_files(path):
    image_path = Path(path)
    if not image_path.is_dir(): return []
    return [str(p) for p in image_path.glob('*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg')]

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))]

# --- 登入與註冊邏輯 ---
def show_login_register_page():
    st.title("歡迎來到 TNT 抽卡模擬器")
    login_tab, register_tab = st.tabs(["登入 (Login)", "註冊 (Register)"])
    with login_tab:
        st.subheader("會員登入")
        with st.form("login_form"):
            username = st.text_input("使用者名稱", key="login_user").lower()
            password = st.text_input("密碼", type="password", key="login_pass")
            login_submitted = st.form_submit_button("登入")
            if login_submitted:
                if not username or not password:
                    st.error("使用者名稱和密碼不可為空！")
                else:
                    user_ref = db.collection('users').document(username).get()
                    if not user_ref.exists:
                        st.error("使用者不存在！")
                    else:
                        user_data = user_ref.to_dict()
                        if pbkdf2_sha256.verify(password, user_data.get('password_hash', '')):
                            st.session_state['authentication_status'] = True
                            st.session_state['username'] = username
                            st.session_state['name'] = user_data.get('name', username)
                            st.rerun()
                        else:
                            st.error("密碼不正確！")
    with register_tab:
        st.subheader("建立新帳號")
        with st.form("register_form"):
            new_name = st.text_input("您的暱稱", key="reg_name")
            new_username = st.text_input("設定使用者名稱 (僅限英文和數字)", key="reg_user").lower()
            new_password = st.text_input("設定密碼", type="password", key="reg_pass")
            confirm_password = st.text_input("確認密碼", type="password", key="reg_confirm")
            register_submitted = st.form_submit_button("註冊")
            if register_submitted:
                if not all([new_name, new_username, new_password, confirm_password]):
                    st.error("所有欄位都必須填寫！")
                elif new_password != confirm_password:
                    st.error("兩次輸入的密碼不一致！")
                elif not new_username.isalnum():
                    st.error("使用者名稱只能包含英文和數字！")
                else:
                    user_ref = db.collection('users').document(new_username)
                    if user_ref.get().exists:
                        st.error("此使用者名稱已被註冊！")
                    else:
                        password_hash = pbkdf2_sha256.hash(new_password)
                        user_data = {"name": new_name, "password_hash": password_hash}
                        user_ref.set(user_data)
                        st.success("註冊成功！請前往登入分頁進行登入。")

# --- 主應用程式邏輯 ---
def main_app():
    st.sidebar.title(f"歡迎, {st.session_state['name']}!")
    if st.sidebar.button("登出"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    app_mode = st.sidebar.selectbox("請選擇功能", ["抽卡模擬器", "我的卡冊"])
    
    with st.sidebar.expander("帳號管理"):
        st.warning("注意：刪除帳號將會永久移除您的所有卡冊資料，此操作無法復原。")
        password = st.text_input("請輸入您的密碼以進行驗證", type="password", key="delete_password")
        confirmation = st.text_input("請輸入 'DELETE' 以確認刪除", key="delete_confirm")
        if st.button("永久刪除我的帳號"):
            delete_user_account(password, confirmation)

    st.sidebar.markdown("---")
    st.sidebar.caption("此網頁的圖檔皆來自於微博 : 小姚宋敏")
    if app_mode == "我的卡冊":
        show_card_collection()
    else:
        show_gacha_simulator()

def delete_user_account(password, confirmation):
    """處理刪除帳號的邏輯"""
    username = st.session_state['username']
    user_ref = db.collection('users').document(username).get()
    user_data = user_ref.to_dict()

    if not pbkdf2_sha256.verify(password, user_data.get('password_hash', '')):
        st.sidebar.error("密碼不正確！")
        return
    
    if confirmation.strip().upper() != 'DELETE':
        st.sidebar.error("確認文字不符，請輸入 'DELETE'。")
        return

    with st.spinner("正在刪除您的所有資料..."):
        cards_ref = db.collection('users').document(username).collection('cards')
        for doc in cards_ref.stream():
            doc.reference.delete()
        db.collection('users').document(username).delete()

    st.success("您的帳號與所有資料已成功刪除。")
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def show_card_collection():
    st.header("📚 我的卡冊")
    cards_ref = db.collection('users').document(st.session_state['username']).collection('cards').stream()
    my_cards = [card.to_dict() for card in cards_ref]
    if not my_cards:
        st.info("您的卡冊還是空的，快去抽卡吧！")
        return

    grouped_cards = defaultdict(list)
    for card in my_cards:
        path = card.get('path')
        if path:
            pool_name = Path(path).parts[1]
            if pool_name.startswith("二專"):
                grouped_cards["二專"].append(card)
            else:
                grouped_cards[pool_name].append(card)

    total_cards = sum(c.get('count', 0) for c in my_cards)
    st.success(f"您總共擁有 {len(my_cards)} 種不同卡片，總計 {total_cards} 張。")
    st.markdown("---")

    for pool_name in sorted(grouped_cards.keys()):
        with st.expander(f"**{pool_name}** ({len(grouped_cards[pool_name])} 種)"):
            pool_cards = grouped_cards[pool_name]
            pool_cards.sort(key=lambda x: natural_sort_key(x.get('path', '')))
            
            for card_data in pool_cards:
                path = card_data.get('path')
                count = card_data.get('count', 0)
                card_name = card_data.get('name', Path(path).stem)
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.image(path, width=150)
                with col2:
                    st.markdown(f"**{card_name}**")
                    st.write(f"擁有數量：{count}")
                st.markdown("---")


def show_gacha_simulator():
    st.header("🎰 抽卡模擬器")
    modes = ["☀️ 夏日記憶", "🎤 二專-三時有聲款", "🎡 二專-烏托邦樂園款", "💿 第三張專輯"]
    selected_mode = st.selectbox("請選擇您想玩的抽卡模式：", modes)
    st.markdown("---")
    if selected_mode == "☀️ 夏日記憶": draw_summer_memories()
    elif selected_mode == "🎤 二專-三時有聲款": draw_second_album("二專-三時有聲款")
    elif selected_mode == "🎡 二專-烏托邦樂園款": draw_second_album("二專-烏托邦樂園款")
    elif selected_mode == "💿 第三張專輯": draw_third_album()

def add_cards_to_collection(card_paths):
    if not card_paths: return
    user_doc_ref = db.collection('users').document(st.session_state['username'])
    for card_path_str in card_paths:
        card_path = Path(card_path_str)
        card_info = CARD_DATA.get(card_path.as_posix(), {})
        card_name = card_info.get('name', card_path.stem)
        
        card_id = str(card_path).replace("/", "_").replace("\\", "_")
        card_doc_ref = user_doc_ref.collection('cards').document(card_id)
        card_doc_ref.set({'path': str(card_path), 'name': card_name, 'count': firestore.Increment(1)}, merge=True)
    # 【本次更新重點】移除通知訊息
    # st.toast(f"已將 {len(card_paths)} 張卡片加入卡冊！")

def draw_random_cards_and_save(path, num_to_draw, title):
    st.markdown(f"### {title}")
    deck = get_image_files(path)
    if not deck: st.error(f"在「{path}」中找不到卡片。"); return
    if len(deck) < num_to_draw: st.warning(f"「{path}」卡池數量不足 {num_to_draw} 張！"); return
    drawn_cards = random.sample(deck, num_to_draw)
    add_cards_to_collection(drawn_cards)
    cols = st.columns(min(len(drawn_cards), 7))
    for i, card in enumerate(drawn_cards):
        with cols[i % len(cols)]: st.image(card, use_container_width=True)

def draw_fixed_solo_set_and_save(path, title):
    st.markdown(f"### {title}")
    base_path = Path(path)
    themes = [d.name for d in base_path.glob('*') if d.is_dir()]
    if not themes: st.error(f"在「{path}」中找不到主題資料夾。"); return
    chosen_theme = random.choice(themes)
    chosen_folder_path = base_path / chosen_theme
    card_set = get_image_files(chosen_folder_path)
    if card_set:
        card_set.sort(key=natural_sort_key)
        st.info(f"您抽中了 **{chosen_theme}** 套組！")
        add_cards_to_collection(card_set)
        cols = st.columns(min(len(card_set), 7))
        for i, card in enumerate(card_set):
            with cols[i % len(cols)]: st.image(card, use_container_width=True)
    else:
        st.error(f"在「{chosen_folder_path}」中找不到卡片。")

def draw_summer_memories():
    st.subheader("☀️ 夏日記憶")
    st.write("規則：從所有卡片中隨機抽取 3 張。")
    if st.button("抽取三張夏日記憶！", key="summer_draw"):
        draw_random_cards_and_save(Path("image/夏日記憶"), 3, "恭喜！您抽到了：")

def draw_second_album(album_name):
    st.subheader(f"🎶 {album_name}")
    st.write("規則：點擊按鈕，將會一次性抽取所有配置的卡片。")
    
    if album_name == "二專-烏托邦樂園款":
        data_source_path = Path("image/二專-三時有聲款")
    else:
        data_source_path = Path(f"image/{album_name}")
    
    presale_path = Path(f"image/{album_name}/預售禮")

    if st.button(f"開始抽取 {album_name}！", key=album_name.replace("-", "_")):
        st.success("抽卡結果如下：")
        draw_random_cards_and_save(data_source_path / "團體卡", 1, "🎫 團體卡")
        draw_random_cards_and_save(data_source_path / "分隊卡", 1, "👯 分隊卡")
        draw_random_cards_and_save(data_source_path / "雙人卡", 7, "💖 雙人卡")
        draw_random_cards_and_save(data_source_path / "ID卡", 1, "🆔 ID卡")
        draw_fixed_solo_set_and_save(data_source_path / "單人固卡", "✨ 單人固卡")
        draw_random_cards_and_save(data_source_path / "高級會員專屬贈品", 1, "💎 高級會員贈品")
        
        st.markdown("### 特典 - 預售禮")
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
                cols = st.columns(3)
                for i, c in enumerate(drawn):
                    with cols[i]:
                        st.image(c, use_container_width=True)

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
        st.markdown("### ✨ 單人固卡 (1套)")
        solo_base_path = Path("image/三專/單人固卡")
        choices = (["R"]*57) + (["SR"]*38) + (["SSR"]*5)
        rarity = random.choice(choices)
        st.info(f"您抽中了 **{rarity}** 套組！")
        
        solo_path = solo_base_path / rarity
        card_set = get_image_files(solo_path)
        if card_set:
            card_set.sort(key=natural_sort_key)
            add_cards_to_collection(card_set)
            cols = st.columns(min(len(card_set), 7))
            for i, card in enumerate(card_set):
                with cols[i % len(cols)]:
                    st.image(card, use_container_width=True)
        else:
            st.error(f"在「{solo_path}」中找不到卡片。")

        # UR卡
        if random.randint(1, 100) == 1:
            ur_cards = get_image_files(Path("image/三專/UR"))
            if ur_cards:
                st.balloons()
                st.markdown("### 🎉 奇蹟降臨！🎉")
                drawn = random.choice(ur_cards)
                add_cards_to_collection([drawn])
                c1,c2,c3 = st.columns([1,2,1]); c2.image(drawn, use_container_width=True)

# --- 程式進入點 ---
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if st.session_state.get('authentication_status'):
    main_app()
else:
    show_login_register_page()