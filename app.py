import streamlit as st
import random
import os
import re
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

def natural_sort_key(s):
    """提供給 sort() 使用的鍵，實現自然排序"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))]

def draw_random_cards(path, num_to_draw, title):
    """通用抽卡函式：從指定路徑隨機抽取N張卡"""
    st.markdown(f"### {title}")
    deck = get_image_files(path)
    if not deck:
        st.error(f"在「{path}」中找不到卡片。")
        return
    
    if len(deck) < num_to_draw:
        st.warning(f"「{path}」卡池數量不足 {num_to_draw} 張，無法抽取！")
        return

    drawn_cards = random.sample(deck, num_to_draw)
    
    # 根據抽取數量決定欄位數
    num_columns = min(len(drawn_cards), 7)
    cols = st.columns(num_columns)
    for i, card in enumerate(drawn_cards):
        with cols[i % num_columns]:
            st.image(card, use_container_width=True)

def draw_fixed_solo_set(path, title):
    """通用函式：抽取一套完整的單人固卡"""
    st.markdown(f"### {title}")
    base_path = Path(path)
    # 隨機選擇 "白底" 或 "黃底"
    themes = [d.name for d in base_path.glob('*') if d.is_dir()]
    if not themes:
        st.error(f"在「{path}」中找不到主題資料夾（如 '白底' 或 '黃底'）。")
        return

    chosen_theme = random.choice(themes)
    chosen_folder_path = base_path / chosen_theme
    card_set = get_image_files(chosen_folder_path)
    
    if card_set:
        card_set.sort(key=natural_sort_key)
        st.info(f"您抽中了 **{chosen_theme}** 套組！")
        num_columns = min(len(card_set), 7)
        cols = st.columns(num_columns)
        for i, card in enumerate(card_set):
            with cols[i % num_columns]:
                st.image(card, use_container_width=True)
    else:
        st.error(f"在「{chosen_folder_path}」中找不到卡片。")

# --- 各個抽卡模式的主函式 ---

def draw_summer_memories():
    st.subheader("☀️ 夏日記憶")
    st.write("規則：從所有卡片中隨機抽取 3 張雙人卡。")
    if st.button("抽取三張夏日記憶！", key="summer_draw"):
        draw_random_cards(Path("image/夏日記憶"), 3, "恭喜！您抽到了：")

def draw_second_album(album_name):
    """處理二專兩種版本的通用函式"""
    st.subheader(f"🎶 {album_name}")
    st.write("規則：點擊按鈕，將會一次性抽取所有配置的卡片。")
    
    base_path = Path(f"image/{album_name}")

    if st.button(f"開始抽取 {album_name}！", key=album_name.replace("-", "_")):
        st.success("抽卡結果如下：")
        st.markdown("---")
        draw_random_cards(base_path / "團體卡", 1, "👨‍👨‍👦‍👦 團體卡 (1張)")
        st.markdown("---")
        draw_random_cards(base_path / "分隊卡", 1, "👯 分隊卡 (1張)")
        st.markdown("---")
        draw_random_cards(base_path / "雙人卡", 7, "❣️ 雙人卡 (7張)")
        st.markdown("---")
        draw_random_cards(base_path / "ID卡", 1, "🆔 ID卡 (1張)")
        st.markdown("---")
        draw_fixed_solo_set(base_path / "單人固卡", "✨ 單人固卡 (1套)")
        
        # 【本次更新重點】新增高級會員贈品抽卡
        st.markdown("---")
        draw_random_cards(base_path / "高級會員專屬贈品", 1, "💎 高級會員專屬贈品 (1張)")
        
        # 處理獨特的預售禮邏輯
        st.markdown("---")
        st.markdown("### 特典 - 預售禮")
        presale_path = base_path / "預售禮"
        if album_name == "二專-三時有聲款":
            # 固定印出團卡 + 隨機抽1張單人卡
            draw_random_cards(presale_path / "團卡", 1, "預售禮 - 團卡 (固定)")
            draw_random_cards(presale_path / "單人卡", 1, "預售禮 - 單人卡 (隨機)")
        elif album_name == "二專-烏托邦樂園款":
            # 隨機抽1張分隊卡 + 隨機抽1張單人卡
            draw_random_cards(presale_path / "分隊卡", 1, "預售禮 - 分隊卡 (隨機)")
            draw_random_cards(presale_path / "單人卡", 1, "預售禮 - 單人卡 (隨機)")

def draw_third_album():
    st.subheader("💿 第三張專輯")
    st.write("規則：點擊按鈕，將會同時抽取「雙人卡」3張、「團體卡」1張、「單人固卡」1套，並有1%機率額外獲得一張UR卡！")

    if st.button("開始抽取三專！", key="album_draw"):
        st.success("抽卡結果如下：")
        
        # 雙人卡
        st.markdown("---")
        st.markdown("### ❣️ 雙人卡 (3張)")
        base_path = Path("image/三專/雙人卡")
        r_cards = get_image_files(base_path / "R")
        sr_cards = get_image_files(base_path / "SR")
        if r_cards or sr_cards:
            weighted_deck = (r_cards * 60) + (sr_cards * 40)
            if len(weighted_deck) >= 3:
                drawn = random.sample(weighted_deck, 3)
                cols = st.columns(3)
                for i, card in enumerate(drawn):
                    with cols[i]: st.image(card, use_container_width=True)
        
        # 團體卡
        st.markdown("---")
        st.markdown("### 👨‍👨‍👦‍👦 團體卡 (1張)")
        group_base_path = Path("image/三專/團體卡")
        options = {"R": 57, "SR": 38, "SSR": 5}
        deck = []
        for r, w in options.items():
            files = list(group_base_path.glob(f'{r}.*'))
            if files: deck.extend([str(files[0])] * w)
        if deck:
            drawn = random.choice(deck)
            c1, c2, c3 = st.columns([1,2,1]); c2.image(drawn, use_container_width=True)

        # 單人固卡
        st.markdown("---")
        solo_base_path = Path("image/三專/單人固卡")
        rarity_choices = (["R"] * 57) + (["SR"] * 38) + (["SSR"] * 5)
        chosen_rarity = random.choice(rarity_choices)
        draw_fixed_solo_set(solo_base_path, f"✨ 單人固卡 ({chosen_rarity}套)")

        # UR卡
        st.markdown("---")
        if random.randint(1, 100) == 1:
            ur_path = Path("image/三專/UR")
            ur_cards = get_image_files(ur_path)
            if ur_cards:
                st.balloons()
                st.markdown("### 🎉 奇蹟降臨！🎉")
                st.warning("您額外獲得了一張極其稀有的UR卡！")
                c1, c2, c3 = st.columns([1,2,1]); c2.image(random.choice(ur_cards), use_container_width=True)

# --- 主介面 ---
modes = ["☀️ 夏日記憶", "🎤 二專-三時有聲款", "🎡 二專-烏托邦樂園款", "💿 第三張專輯"]
selected_mode = st.selectbox("請選擇您想玩的抽卡模式：", modes)
st.markdown("---")

# 根據選擇執行對應函式
if selected_mode == "☀️ 夏日記憶":
    draw_summer_memories()
elif selected_mode == "🎤 二專-三時有聲款":
    draw_second_album("二專-三時有聲款")
elif selected_mode == "🎡 二專-烏托邦樂園款":
    draw_second_album("二專-烏托邦樂園款")
elif selected_mode == "💿 第三張專輯":
    draw_third_album()

# --- 頁尾資訊 ---
st.markdown("---")
st.caption("此網頁的圖檔皆來自於微博 : 小姚宋敏")