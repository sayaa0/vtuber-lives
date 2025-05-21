import streamlit as st
import calendar
from datetime import datetime, timedelta, date
import requests

YOUTUBE_API_KEY = 'AIzaSyDiB9XuCww8uWmnafqh-ZZjLd0Zed0MAuI'  # ←自分のAPIキーに置き換えてください

def extract_channel_id(url):
    return url.strip().split("/")[-1]

def fetch_videos(channel_id, year, month):
    start = datetime(year, month, 1).isoformat("T") + "Z"
    end = (datetime(year, month, calendar.monthrange(year, month)[1]) + timedelta(days=1)).isoformat("T") + "Z"
    params = {
        'key': YOUTUBE_API_KEY,
        'channelId': channel_id,
        'part': 'snippet',
        'order': 'date',
        'maxResults': 50,
        'publishedAfter': start,
        'publishedBefore': end
    }
    res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params)
    return res.json().get("items", [])

# --- UI部分 ---
st.set_page_config(layout="wide")
st.title("📅 Vtuber アーカイブカレンダー")

channel_url = st.text_input("YouTubeチャンネルのURLを入力")

if channel_url:
    channel_id = extract_channel_id(channel_url)
    # --- 年月の状態保持 ---
    if 'calendar_year' not in st.session_state:
        st.session_state['calendar_year'] = datetime.now().year
    if 'calendar_month' not in st.session_state:
        st.session_state['calendar_month'] = datetime.now().month

    # --- 前月・次月ボタン + 年月セレクター ---
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        if st.button("◀ 前の月"):
            if st.session_state['calendar_month'] == 1:
                st.session_state['calendar_month'] = 12
                st.session_state['calendar_year'] -= 1
            else:
                st.session_state['calendar_month'] -= 1
    with col3:
        if st.button("▶ 次の月"):
            if st.session_state['calendar_month'] == 12:
                st.session_state['calendar_month'] = 1
                st.session_state['calendar_year'] += 1
            else:
                st.session_state['calendar_month'] += 1
    with col2:
        st.session_state['calendar_year'] = st.selectbox(
            "年", list(range(datetime.now().year, datetime.now().year - 5, -1)),
            index=list(range(datetime.now().year, datetime.now().year - 5, -1)).index(st.session_state['calendar_year'])
        )
        st.session_state['calendar_month'] = st.selectbox(
            "月", list(range(1, 13)),
            index=st.session_state['calendar_month'] - 1
    )

    # --- 選択された年月を反映 ---
    year = st.session_state['calendar_year']
    month = st.session_state['calendar_month']

    # --- YouTube API 呼び出し ---
    videos = fetch_videos(channel_id, year, month)


    # 日付ごとのマッピング
    day_map = {}
    for v in videos:
        dt = datetime.fromisoformat(v['snippet']['publishedAt'].replace("Z", "+00:00"))
        day = dt.day
        day_map.setdefault(day, []).append(v)

    st.subheader(f"{year}年{month}月の配信カレンダー")
    cal = calendar.Calendar()
    for week in cal.monthdayscalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.write(" ")
                elif day in day_map:
                    v = day_map[day][0]
                    if st.button(f"{day}日", key=f"day-{day}"):
                        st.session_state['selected_day'] = day
                    st.image(v['snippet']['thumbnails']['default']['url'], use_container_width=True)
                else:
                    st.write(f"{day}日")

    if 'selected_day' in st.session_state:
        st.subheader(f"{year}年{month}月{st.session_state['selected_day']}日の配信一覧")
        for v in day_map.get(st.session_state['selected_day'], []):
            cols = st.columns([1, 3])
            with cols[0]:
                st.image(v['snippet']['thumbnails']['medium']['url'], use_container_width=True)
            with cols[1]:
                st.markdown(f"**{v['snippet']['title']}**")
                st.caption(v['snippet']['description'][:200] + "...")

                if 'videoId' in v['id']:
                    video_id = v['id']['videoId']
                    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                    st.markdown(
                        f'<a href="{youtube_url}" target="_blank" style="color:#1E90FF; font-weight:bold;">▶️ YouTubeでこの配信を観る</a>',
                        unsafe_allow_html=True
                    )
