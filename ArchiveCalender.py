import streamlit as st
import calendar
from datetime import datetime, timedelta
import requests

# === 設定 ===
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]   # ←自分のAPIキーに置き換えてください
REACTIONS = ["🔥", "😢", "❤", "😂", "👏", "👍"]  # 利用可能なリアクション一覧

# --- YouTube API 呼び出し関数 ---
def fetch_channels(query, max_results=5):
    #st.write(f"DEBUG: fetch_channels called with query: {query}") # デバッグ用
    params = {
        'key': YOUTUBE_API_KEY,
        'q': query,
        'type': 'channel',
        'part': 'snippet',
        'maxResults': max_results
    }
    #st.write(f"DEBUG: API params: {params}") # デバッグ用
    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params
        )
        response.raise_for_status() # HTTPエラーがあれば例外を発生
        res_json = response.json()
        #st.write(f"DEBUG: API response: {res_json}") # デバッグ用
    except requests.exceptions.RequestException as e:
        st.error(f"APIリクエストエラー: {e}")
        return []
    except ValueError as e: # JSONデコードエラー
        st.error(f"APIレスポンスのJSONデコードエラー: {e}")
        st.error(f"API raw response: {response.text}") # 生のレスポンスを表示
        return []

    return [
        {
            'id': item['snippet']['channelId'],
            'title': item['snippet']['title']
        }
        for item in res_json.get('items', [])
    ]

def fetch_videos(channel_id, year, month, max_results=50):
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

def fetch_earliest_date(channel_id):
    res = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            'key': YOUTUBE_API_KEY,
            'channelId': channel_id,
            'part': 'snippet',
            'order': 'date',
            'maxResults': 1
        }
    ).json()
    items = res.get('items', [])
    if not items:
        return datetime.now()
    return datetime.fromisoformat(items[0]['snippet']['publishedAt'].replace("Z", "+00:00"))

# --- Streamlit UI ---
st.set_page_config(page_title="Vtuber アーカイブカレンダー", layout="wide")
st.title("📅 Vtuber アーカイブカレンダー")

# チャンネル検索
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

# カレンダー表示
if channel_id:
    if 'year' not in st.session_state:
        st.session_state.year = datetime.now().year
    if 'month' not in st.session_state:
        st.session_state.month = datetime.now().month

    earliest_date = fetch_earliest_date(channel_id)
    current_date = datetime.now()
    year_options = list(range(2006, current_date.year + 1))
    if st.session_state.year not in year_options:
        st.session_state.year = year_options[-1]

    if st.session_state.year == current_date.year:
        month_options = list(range(1, current_date.month + 1))
    else:
        month_options = list(range(1, 13))

    if st.session_state.month not in month_options:
        st.session_state.month = month_options[0]

    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 8])
    with nav_col2:
        if st.button("◀ 前の月"):
            if st.session_state.month == 1:
                st.session_state.month = 12
                st.session_state.year -= 1
            else:
                st.session_state.month -= 1
    with nav_col1:
        selected_year = st.selectbox("年", year_options, index=year_options.index(st.session_state.year), key="year_select", format_func=str)
        st.session_state.year = selected_year

        selected_month = st.selectbox("月", month_options, index=month_options.index(st.session_state.month), key="month_select", format_func=str)
        st.session_state.month = selected_month

    with nav_col3:
        if st.button("次の月 ▶"):
            if st.session_state.month == 12:
                st.session_state.month = 1
                st.session_state.year += 1
            else:
                st.session_state.month += 1

    year = st.session_state.year
    month = st.session_state.month
    videos = fetch_videos(channel_id, year, month)

    day_map = {}
    for v in videos:
        dt = datetime.fromisoformat(v['snippet']['publishedAt'].replace("Z", "+00:00"))
        day_map.setdefault(dt.day, []).append(v)

    st.subheader(f"{year}年{month}月の配信カレンダー")
    cal = calendar.Calendar()
    for week in cal.monthdayscalendar(year, month):
        cols_week = st.columns(7)  # 週の各日を表示するためのカラム
        for i, day in enumerate(week):
            with cols_week[i]:
                if day == 0:
                    st.write(" ")
                else:
                    # 日付ボタン (クリックでその日の配信一覧へ)
                    if st.button(f"{day}日", key=f"cal_day_btn-{year}-{month}-{day}", use_container_width=True):
                        st.session_state['selected_day'] = day
                    
                    if day in day_map:
                        for video_idx, v_data in enumerate(day_map[day]):
                            video_id = v_data['id'].get('videoId', f"{year}-{month}-{day}-{video_idx}") # 動画ごとのユニークID (videoIdがない場合も考慮)
                            thumbnail_url = v_data['snippet']['thumbnails'].get('default', {}).get('url', None)
                            
                            if thumbnail_url:
                                st.image(thumbnail_url, use_container_width=True)

                            # リアクション機能のUI変更
                            # 各動画のリアクション展開状態を管理するセッションステートキー
                            reaction_toggle_key = f"reaction_toggle_{video_id}"

                            # セッションステートの初期化
                            if reaction_toggle_key not in st.session_state:
                                st.session_state[reaction_toggle_key] = False

                            # 「リアクション」トグルボタン
                            if st.button("リアクション", key=f"toggle_btn_{video_id}", use_container_width=True):
                                st.session_state[reaction_toggle_key] = not st.session_state[reaction_toggle_key]

                            # リアクション絵文字の表示 (トグルがONの場合)
                            if st.session_state[reaction_toggle_key]:
                                reaction_cols = st.columns(len(REACTIONS))
                                for r_idx, emoji in enumerate(REACTIONS):
                                    with reaction_cols[r_idx]:
                                        if st.button(emoji, key=f"react_emoji_{video_id}_{emoji}", use_container_width=True):
                                            st.success(f"{v_data['snippet']['title']} に {emoji} でリアクションしました！")
                                            # TODO: ここにリアクションを保存・集計する処理を追加
                                            # st.session_state[reaction_toggle_key] = False # リアクション後は閉じる場合
                            
                            # 動画タイトルなどを表示する場合はここに追加
                            # st.caption(v_data['snippet']['title'][:30] + "...") # 短縮タイトルなど

                    else: # day in day_map
                        st.write("配信なし")

    if 'selected_day' in st.session_state:
        sd = st.session_state.selected_day
        st.subheader(f"{year}年{month}月{sd}日の配信一覧")
        for v in day_map.get(sd, []):
            cols = st.columns([1,3])
            with cols[0]:
                thumb = v['snippet']['thumbnails'].get('medium', {}).get('url', None)
                if thumb:
                    st.image(thumb, use_container_width=True)
            with cols[1]:
                title = v['snippet']['title']
                desc = v['snippet']['description'][:200] + '...'
                st.markdown(f"**{title}**")
                st.caption(desc)
                vid = v['id'].get('videoId')
                if vid:
                    url = f"https://www.youtube.com/watch?v={vid}"
                    st.markdown(f"[▶️ YouTubeで観る]({url})")
                # リアクションの集計（仮想カウント表示）
                st.caption("リアクション: " + " ".join([f"{emoji} 0" for emoji in REACTIONS]))
