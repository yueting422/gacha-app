import streamlit as st
import random
import os
from pathlib import Path

# --- 網頁基礎設定 ---
st.set_page_config(page_title="TNT抽卡模擬器", page_icon="🍿")
st.title("💣 時代少年團 - 抽卡模擬器")

# --- 通用函式 ---
def get_image_files(path):
    """安全地獲取指定路徑下的所有圖片檔案"""
    image_path = Path(path)
    if not image_path.is_dir():
        return []
    return [str(p) for p in image_path.glob('*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg')]

# --- 「夏日記憶」模式的函式 (無變動) ---
def draw_summer_memories():
    st.subheader("☀️ 夏日記憶")
    st.write("規則：從所有卡片中隨機抽取 3 張雙人卡。")
    
    deck_path = Path("image/夏日記憶")
    deck = get_image_files(deck_path)
    
    if not deck:
        st.error(f"找不到「夏日記憶」的卡片，請檢查路徑：{deck_path}")
        return

    if st.button("抽取三張夏日記憶！", key="summer_draw"):
        if len(deck) < 3:
            st.warning("卡池數量不足3張，無法抽取！")
        else:
            drawn_cards = random.sample(deck, 3)
            st.success("恭喜！您抽到了：")
            cols = st.columns(3)
            for i, card in enumerate(drawn_cards):
                with cols[i]:
                    st.image(card, use_container_width=True)

# --- 「三專」模式的相關函式 (已更新) ---
def draw_duo_cards():
    """處理「雙人卡」的抽卡邏輯"""
    base_path = Path("image/三專/雙人卡")
    r_cards = get_image_files(base_path / "R")
    sr_cards = get_image_files(base_path / "SR")

    if not r_cards and not sr_cards:
        st.error("找不到任何「雙人卡」的卡片，請檢查R, SR資料夾。")
        return None

    # 更新加權卡池：R:60%, SR:40%
    weighted_deck = (r_cards * 60) + (sr_cards * 40)
    
    if len(weighted_deck) < 3:
        st.warning("「雙人卡」卡池總數不足3張，無法抽取！")
        return None
        
    return random.sample(weighted_deck, 3)

def draw_group_card():
    """處理「團體卡」的抽卡邏輯"""
    base_path = Path("image/三專/團體卡")
    
    # 更新加權列表：R:57%, SR:38%, SSR:5%
    weighted_options = {
        "R": 57,
        "SR": 38,
        "SSR": 5
    }
    
    weighted_deck = []
    for rarity, weight in weighted_options.items():
        found_files = list(base_path.glob(f'{rarity}.*'))
        if found_files:
            weighted_deck.extend([str(found_files[0])] * weight)

    if not weighted_deck:
        st.error("找不到任何「團體卡」的卡片，請確認圖片檔名是否為 R, SR, SSR。")
        return None
        
    return random.choice(weighted_deck)

def draw_solo_set():
    """處理「單人固卡」的抽卡邏輯"""
    base_path = Path("image/三專/單人固卡")
    
    # 更新稀有度選擇：R:57%, SR:38%, SSR:5%
    rarity_choices = (["R"] * 57) + (["SR"] * 38) + (["SSR"] * 5)
    chosen_rarity = random.choice(rarity_choices)
    
    chosen_folder_path = base_path / chosen_rarity
    card_set = get_image_files(chosen_folder_path)
    
    if not card_set:
        st.error(f"在「單人固卡」中找不到 {chosen_rarity} 的卡片，請檢查資料夾。")
        return None, None
        
    return chosen_rarity, card_set

def draw_special_ur():
    """處理1%機率掉落的UR卡"""
    # 進行1%的機率檢定
    if random.randint(1, 100) == 1:
        ur_path = Path("image/三專/UR")
        ur_cards = get_image_files(ur_path)
        if ur_cards:
            return random.choice(ur_cards)
    return None

def draw_third_album():
    st.subheader("💿 第三張專輯")
    st.write("規則：點擊按鈕，將會同時抽取「雙人卡」3張、「團體卡」1張、「單人固卡」1套，並有1%機率額外獲得一張UR卡！")

    if st.button("開始抽取三專！", key="album_draw"):
        st.success("抽卡結果如下：")

        # 1. 抽取雙人卡
        st.markdown("---")
        st.markdown("### 💖 雙人卡 (3張)")
        duo_results = draw_duo_cards()
        if duo_results:
            cols = st.columns(3)
            for i, card in enumerate(duo_results):
                with cols[i]:
                    st.image(card, use_container_width=True)
        
        # 2. 抽取團體卡
        st.markdown("---")
        st.markdown("### 👨‍👨‍👦‍👦 團體卡 (1張)")
        group_result = draw_group_card()
        if group_result:
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                st.image(group_result, use_container_width=True)

        # 3. 抽取單人固卡
        st.markdown("---")
        st.markdown("### ✨ 單人固卡 (1套)")
        rarity, solo_results = draw_solo_set()
        if solo_results:
            st.info(f"您抽中了 **{rarity}** 套組！")
            num_columns = min(len(solo_results), 7)
            cols = st.columns(num_columns)
            for i, card in enumerate(solo_results):
                with cols[i % num_columns]:
                    st.image(card, use_container_width=True)
        
        # 4. 進行特別UR卡抽獎
        st.markdown("---")
        ur_card = draw_special_ur()
        if ur_card:
            st.balloons() # 顯示慶祝氣球
            st.markdown("### 🎉 奇蹟降臨！🎉")
            st.warning("您額外獲得了一張極其稀有的UR卡！")
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                st.image(ur_card, use_container_width=True)

# --- 主介面：使用選項卡(Tab)來切換模式 ---
tab1, tab2 = st.tabs(["☀️ 夏日記憶", "💿 第三張專輯"])

with tab1:
    draw_summer_memories()

with tab2:
    draw_third_album()