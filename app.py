# app.py 的完整程式碼
import streamlit as st
import random
import os

# --- 網頁基礎設定 ---
# 設定網頁標題和圖示(Emoji)
st.set_page_config(page_title="時代少年團抽卡模擬器", page_icon="🍿")

# --- 網頁顯示內容 ---
# 顯示大標題
st.title("💣 時代少年團抽卡模擬器")
# 顯示說明文字
st.write("點擊按鈕，看看你今天的手氣如何！")

# --- 卡池設定 ---
# 圖片所在的資料夾名稱
IMAGE_DIR = "images"
# 檢查圖片資料夾是否存在，並讀取所有圖片檔名
try:
    # 組合出完整的圖片路徑列表
    DECK = [os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
except FileNotFoundError:
    st.error(f"錯誤：找不到 '{IMAGE_DIR}' 資料夾。請確認圖片已上傳到正確位置。")
    DECK = []


# --- 核心功能與互動 ---
# 只有當卡池 (DECK) 不是空的，才顯示按鈕
if DECK:
    # st.button() 會建立一個按鈕，如果使用者點擊，if 條件就會成立
    if st.button("✨ 點我抽三張！ ✨", use_container_width=True):
        if len(DECK) < 3:
            st.warning("卡池中的卡片數量不足三張，無法抽取！")
        else:
            st.subheader("恭喜！您抽到了：")
            
            # 從牌組中隨機抽出3個不重複的項目
            drawn_cards = random.sample(DECK, 3)
            
            # st.columns 可以讓我們將畫面分成三欄，用來並排顯示圖片
            cols = st.columns(3)
            for i, card_path in enumerate(drawn_cards):
                # 在每一欄中顯示一張圖片
                with cols[i]:
                    st.image(card_path, use_container_width=True)
else:
    # 如果找不到圖片，顯示提示訊息
    st.info("卡池目前是空的，請先上傳圖片並確認專案結構是否正確。")