import streamlit as st
import calendar
from datetime import datetime, timedelta
import requests

# === 設定 ===
YOUTUBE_API_KEY = 'AIzaSyDiB9XuCww8uWmnafqh-ZZjLd0Zed0MAuI'  # ←自分のAPIキーに置き換えてください

# --- YouTube API 呼び出し関数 ---
def fetch_channels(query, max_results=5):
    """
    チャンネル名で検索し、チャンネルIDとタイトルを返す
    """
    res = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            'key': YOUTUBE_API_KEY,
            'q': query,
            'type': 'channel',
            'part': 'snippet',
            'maxResults': max_results
        }
    ).json()
    return [
        {
            'id': item['snippet']['channelId'],
            'title': item['snippet']['title']
        }
        for item in res.get('items', [])
    ]


def fetch_videos(channel_id, year, month, max_results=50):
    """
    指定チャンネルの指定年月の動画一覧を取得する
    """
    start = datetime(year, month, 1).isoformat("T") + "Z"
    end = (datetime(year, month, calendar.monthrange(year, month)[1]) + timedelta(days=1)).isoformat("T") + "Z"
    res = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            'key': YOUTUBE_API_KEY,
            'channelId': channel_id,
            'part': 'snippet',
            'order': 'date',
            'maxResults': max_results,
            'publishedAfter': start,
            'publishedBefore': end
        }
    ).json()
    return res.get('items', [])

# --- Streamlit UI ---
st.set_page_config(page_title="Vtuber アーカイブカレンダー", layout="wide")
st.title("📅 Vtuber アーカイブカレンダー")

# 1. チャンネル検索
st.header("🔍 Vtuberチャンネルを検索して選ぶ")
search_query = st.text_input("チャンネル名で検索", placeholder="例: 星街すいせい")
channel_id = None
if search_query:
    channels = fetch_channels(search_query)
    if not channels:
        st.warning("チャンネルが見つかりませんでした。別のキーワードを試してください。")
    else:
        options = [f"{c['title']} ({c['id']})" for c in channels]
        idx = st.selectbox("候補からチャンネルを選択", range(len(options)), format_func=lambda i: options[i])
        channel_id = channels[idx]['id']
        st.success(f"選択されたチャンネル: {channels[idx]['title']} (ID: {channel_id})")

# 2. カレンダー表示
if channel_id:
    # 年月の初期設定
    if 'year' not in st.session_state:
        st.session_state.year = datetime.now().year
    if 'month' not in st.session_state:
        st.session_state.month = datetime.now().month

    # 前月・次月操作
    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        if st.button("◀ 前の月"):
            if st.session_state.month == 1:
                st.session_state.month = 12
                st.session_state.year -= 1
            else:
                st.session_state.month -= 1
    with col3:
        if st.button("次の月 ▶"):
            if st.session_state.month == 12:
                st.session_state.month = 1
                st.session_state.year += 1
            else:
                st.session_state.month += 1
    with col2:
        st.session_state.year = st.selectbox("年", list(range(datetime.now().year, datetime.now().year-5, -1)), index=0)
        st.session_state.month = st.selectbox("月", list(range(1,13)), index=st.session_state.month-1)

    year = st.session_state.year
    month = st.session_state.month

    # 動画取得
    videos = fetch_videos(channel_id, year, month)

    # 日付ごとにマッピング
    day_map = {}
    for v in videos:
        dt = datetime.fromisoformat(v['snippet']['publishedAt'].replace("Z", "+00:00"))
        day_map.setdefault(dt.day, []).append(v)

    # カレンダー描画
    st.subheader(f"{year}年{month}月の配信カレンダー")
    cal = calendar.Calendar()
    for week in cal.monthdayscalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.write(" ")
                else:
                    if day in day_map:
                        if st.button(f"{day}日", key=f"day-{day}"):
                            st.session_state.selected_day = day
                        # サムネ表示
                        st.image(day_map[day][0]['snippet']['thumbnails']['default']['url'], use_container_width=True)
                    else:
                        st.write(f"{day}日")

    # 日クリック後の詳細表示
    if 'selected_day' in st.session_state:
        sd = st.session_state.selected_day
        st.subheader(f"{year}年{month}月{sd}日の配信一覧")
        for v in day_map.get(sd, []):
            cols = st.columns([1,3])
            with cols[0]:
                st.image(v['snippet']['thumbnails']['medium']['url'], use_container_width=True)
            with cols[1]:
                title = v['snippet']['title']
                desc = v['snippet']['description'][:200] + '...'
                st.markdown(f"**{title}**")
                st.caption(desc)
                vid = v['id'].get('videoId')
                if vid:
                    url = f"https://www.youtube.com/watch?v={vid}"
                    st.markdown(f"[▶️ YouTubeで観る]({url})")
